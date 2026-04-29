import os
import datetime
import time
import logging
from dotenv import load_dotenv
from main import run_job
from src.core.tushare_client import TushareClient
from src.utils.db_utils import Database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FullTestFix")

def run_latest_test():
    load_dotenv()
    token = os.getenv("TUSHARE_TOKEN")
    db_path = os.getenv("DB_PATH", "database/stock_data.db")
    
    ts_client = TushareClient(token)
    db = Database(db_path)
    
    # 获取从 2026-01-01 到今天的交易日
    start_date = "20260101"
    end_date = datetime.datetime.now().strftime("%Y%m%d")
    
    logger.info(f"Step 1: Fetching trade calendar from {start_date} to {end_date}...")
    cal = ts_client.get_trade_cal(start_date=start_date, end_date=end_date)
    # 确保正序排列
    cal = cal.sort_values('cal_date', ascending=True)
    open_days = cal[cal['is_open'] == 1]['cal_date'].tolist()
    
    target_day = open_days[-1]
    logger.info(f"Target latest trading day: {target_day}")
    
    # 检查缺失日期并补齐
    existing_dates = db.execute_query("SELECT DISTINCT trade_date FROM daily_raw")['trade_date'].tolist()
    # 我们至少需要最近 250 天的数据来支撑 MA200 计算，之前已经抓了一部分
    # 这里重点补齐 2026 年以来的
    dates_to_fetch = [d for d in open_days if d not in existing_dates]
    
    logger.info(f"Step 2: Fetching missing {len(dates_to_fetch)} days of data...")
    for day in dates_to_fetch:
        logger.info(f"Fetching {day}...")
        daily = ts_client.get_daily(trade_date=day)
        adj = ts_client.get_adj_factor(trade_date=day)
        basic = ts_client.get_daily_basic(trade_date=day)
        
        db.save_df('daily_raw', daily)
        db.save_df('adj_factor', adj)
        db.save_df('daily_basic', basic)
        time.sleep(0.2)

    logger.info(f"Step 3: Running main job for {target_day}...")
    run_job(target_day)

if __name__ == "__main__":
    run_latest_test()
