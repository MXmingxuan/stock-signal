import os
import sys
import logging
import datetime
from dotenv import load_dotenv
import pandas as pd

# 增加项目根目录到 path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.tushare_client import TushareClient
from src.core.processor import DataProcessor
from src.core.screener import Screener
from src.strategies import StrategyRegistry
from src.utils.db_utils import Database
from src.utils.notifier import Notifier

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Main")

def run_job(target_date: str = None):
    load_dotenv()
    
    # 1. 初始化
    token = os.getenv("TUSHARE_TOKEN")
    db_path = os.getenv("DB_PATH", "database/stock_data.db")
    
    if not token:
        logger.error("TUSHARE_TOKEN not found in .env")
        return

    ts_client = TushareClient(token)
    db = Database(db_path)
    
    # 如果没有指定日期，则默认为今天
    if not target_date:
        target_date = datetime.datetime.now().strftime("%Y%m%d")

    logger.info(f"Starting job for date: {target_date}")

    # 2. 检查是否为交易日
    trade_cal = ts_client.get_trade_cal(start_date=target_date, end_date=target_date)
    if trade_cal is None or trade_cal.empty or trade_cal.iloc[0]['is_open'] == 0:
        logger.info(f"{target_date} is not a trading day. Skipping.")
        return

    # 3. 记录任务开始
    job_id = db.execute_non_query(
        "INSERT INTO job_runs (job_date, start_time, status) VALUES (?, ?, ?)",
        (target_date, datetime.datetime.now().isoformat(), 'RUNNING')
    )

    try:
        # 4. 拉取数据 (基础数据、行情、复权因子、日指标)
        # 获取股票列表 (用于名称映射)
        stock_basic = ts_client.get_stock_basic()
        if stock_basic is None: raise Exception("Failed to fetch stock_basic")
        db.save_df('stock_master', stock_basic, if_exists='replace')
        stock_names = dict(zip(stock_basic['ts_code'], stock_basic['name']))

        # 拉取行情和复权因子 (至少需要过去 260 天的数据以计算 MA200 和 High60)
        start_date = (datetime.datetime.strptime(target_date, "%Y%m%d") - datetime.timedelta(days=400)).strftime("%Y%m%d")
        
        logger.info(f"Fetching daily data from {start_date} to {target_date}...")
        # 注意：全量拉取全市场 400 天数据非常大，且 Tushare 有流量限制。
        # v0.1 建议采用增量方式，或者仅针对 target_date 拉取。
        # 但计算 MA200 需要历史。这里演示直接拉取 target_date，并假设 DB 中已有历史。
        
        daily_today = ts_client.get_daily(trade_date=target_date)
        adj_today = ts_client.get_adj_factor(trade_date=target_date)
        basic_today = ts_client.get_daily_basic(trade_date=target_date)
        
        if daily_today is None or daily_today.empty:
            raise Exception(f"No daily data found for {target_date}")

        db.save_df('daily_raw', daily_today)
        db.save_df('adj_factor', adj_today)
        db.save_df('daily_basic', basic_today)

        # 5. 计算特征
        # 从 DB 读取历史 + 刚拉取的最新数据进行计算
        # 为了演示简化，这里假设我们能获取到足够的计算窗口
        all_daily = db.execute_query(
            "SELECT * FROM daily_raw WHERE trade_date >= ? AND trade_date <= ?", 
            (start_date, target_date)
        )
        all_adj = db.execute_query(
            "SELECT * FROM adj_factor WHERE trade_date >= ? AND trade_date <= ?",
            (start_date, target_date)
        )
        
        processor = DataProcessor()
        df_qfq = processor.calculate_qfq(all_daily, all_adj)
        df_features = processor.calculate_indicators(df_qfq)
        
        # 存入特征表 (仅存当日结果以节省空间，或按需存储)
        db.save_df('daily_features', df_features[df_features['trade_date'] == target_date])

        # 6. 执行选股（支持多策略）
        strategy_names = os.getenv("SCREEN_STRATEGIES", "breakout_30")
        selected = [s.strip() for s in strategy_names.split(",") if s.strip()]
        strategies = StrategyRegistry.resolve(selected)

        if not strategies:
            logger.warning("No valid strategies configured. Falling back to breakout_30.")
            strategies = [StrategyRegistry.get("breakout_30")()]

        # 合并 basic 字段 (换手率) 用于筛选输出
        df_full = pd.merge(df_features, basic_today[['ts_code', 'turnover_rate']], on='ts_code', how='left')

        notifier_config = {
            'server': os.getenv("SMTP_SERVER"),
            'port': int(os.getenv("SMTP_PORT", 465)),
            'user': os.getenv("SMTP_USER"),
            'password': os.getenv("SMTP_PASS"),
            'receiver': os.getenv("RECEIVER_EMAIL")
        }
        notifier = Notifier(notifier_config)

        all_results = {}
        all_attachments = []
        total_candidates = 0

        for strategy in strategies:
            logger.info(f"Running strategy: {strategy.name} - {strategy.description}")
            try:
                screener = Screener(stock_names, strategy=strategy)
                results = screener.screen(df_full, target_date)

                if not results.empty:
                    results['strategy'] = strategy.name
                    total_candidates += len(results)

                db.save_df('screen_results', results)
                logger.info(f"Strategy '{strategy.name}' found {len(results)} candidates.")

                # 每支策略独立的输出文件
                csv_path = f"data/stock_candidates_{strategy.name}_{target_date}.csv"
                txt_path = f"data/stock_codes_{strategy.name}_{target_date}.txt"

                notifier.export_csv(results, csv_path, columns_map=strategy.csv_columns)
                notifier.export_txt(results, txt_path)

                all_results[strategy.name] = results
                if not results.empty:
                    all_attachments.extend([csv_path, txt_path])

            except Exception as e:
                logger.error(f"Strategy '{strategy.name}' failed: {e}", exc_info=True)
                all_results[strategy.name] = pd.DataFrame()

        # 7. 推送结果
        strategy_list = ", ".join(all_results.keys())
        subject = f"【选股助手】{target_date} {strategy_list} - 命中 {total_candidates} 只"

        if total_candidates > 0:
            body_lines = [f"您好，\n\n{target_date} 的选股任务已完成。\n"]
            for name, res in all_results.items():
                body_lines.append(f"策略 [{name}]: {len(res)} 只")
            body_lines.append(f"\n共 {total_candidates} 只候选，详见附件。")
            body = "\n".join(body_lines)
            notifier.send_email(subject, body, all_attachments)
        else:
            body = f"您好，\n\n{target_date} 选股结束，当日无符合条件股票。"
            notifier.send_email(subject, body)

        # 8. 更新任务状态
        db.execute_non_query(
            "UPDATE job_runs SET end_time = ?, status = ? WHERE id = ?",
            (datetime.datetime.now().isoformat(), 'SUCCESS', job_id)
        )

    except Exception as e:
        logger.error(f"Job failed: {e}", exc_info=True)
        db.execute_non_query(
            "UPDATE job_runs SET end_time = ?, status = ?, error_msg = ? WHERE id = ?",
            (datetime.datetime.now().isoformat(), 'FAILED', str(e), job_id)
        )

if __name__ == "__main__":
    # 支持命令行参数指定日期
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_job(date_arg)
