import tushare as ts
import time
import logging
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

class TushareClient:
    def __init__(self, token: str):
        ts.set_token(token)
        self.pro = ts.pro_api()
        self.retry_limit = 3
        self.retry_delay = 2  # seconds

    def query(self, api_name: str, **kwargs) -> Optional[pd.DataFrame]:
        """封装 Tushare 查询，支持重试和基本异常处理"""
        for i in range(self.retry_limit):
            try:
                df = self.pro.query(api_name, **kwargs)
                return df
            except Exception as e:
                logger.warning(f"Tushare API {api_name} call failed (attempt {i+1}): {e}")
                if "抱歉，您每分钟最多访问" in str(e) or "接口限流" in str(e):
                    time.sleep(60) # 限流则等待较长时间
                else:
                    time.sleep(self.retry_delay * (i + 1))
        
        logger.error(f"Tushare API {api_name} failed after {self.retry_limit} attempts.")
        return None

    def get_stock_basic(self):
        return self.query('stock_basic', list_status='L', fields='ts_code,symbol,name,area,industry,market,list_date')

    def get_trade_cal(self, start_date: str, end_date: str):
        return self.query('trade_cal', start_date=start_date, end_date=end_date)

    def get_daily(self, trade_date: str = '', ts_code: str = '', start_date: str = '', end_date: str = ''):
        return self.query('daily', trade_date=trade_date, ts_code=ts_code, start_date=start_date, end_date=end_date)

    def get_adj_factor(self, trade_date: str = '', ts_code: str = '', start_date: str = '', end_date: str = ''):
        return self.query('adj_factor', trade_date=trade_date, ts_code=ts_code, start_date=start_date, end_date=end_date)

    def get_daily_basic(self, trade_date: str = '', ts_code: str = '', start_date: str = '', end_date: str = ''):
        return self.query('daily_basic', trade_date=trade_date, ts_code=ts_code, start_date=start_date, end_date=end_date)
