import os
import datetime
import logging
from dotenv import load_dotenv
from main import TushareClient, Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InitData")

def init_history(days=400):
    load_dotenv()
    token = os.getenv("TUSHARE_TOKEN")
    db_path = os.getenv("DB_PATH", "database/stock_data.db")
    
    ts_client = TushareClient(token)
    db = Database(db_path)
    
    end_date = datetime.datetime.now().strftime("%Y%m%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y%m%d")
    
    logger.info(f"Initializing historical data from {start_date} to {end_date}...")
    
    # 1. 交易日历
    cal = ts_client.get_trade_cal(start_date=start_date, end_date=end_date)
    db.save_df('trade_calendar', cal, if_exists='replace')
    
    # 2. 股票基础信息
    basic = ts_client.get_stock_basic()
    db.save_df('stock_master', basic, if_exists='replace')
    
    # 3. 历史行情 (分批拉取，避免超时或限流)
    # Tushare 接口通常有每分钟调用次数限制，建议循环按日期或按股票拉取
    trade_days = cal[cal['is_open'] == 1]['cal_date'].tolist()
    
    for day in trade_days:
        logger.info(f"Fetching data for {day}...")
        daily = ts_client.get_daily(trade_date=day)
        adj = ts_client.get_adj_factor(trade_date=day)
        basic_daily = ts_client.get_daily_basic(trade_date=day)
        
        db.save_df('daily_raw', daily)
        db.save_df('adj_factor', adj)
        db.save_df('daily_basic', basic_daily)
        
        # 简单避免限流
        import time
        time.sleep(0.5)

    logger.info("Historical data initialization complete.")

if __name__ == "__main__":
    init_history()
