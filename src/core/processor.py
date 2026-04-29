import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class DataProcessor:
    @staticmethod
    def calculate_qfq(daily_df: pd.DataFrame, adj_df: pd.DataFrame) -> pd.DataFrame:
        """
        计算前复权价格
        公式: qfq_price = price * (adj_factor / latest_adj_factor)
        """
        if daily_df.empty or adj_df.empty:
            return pd.DataFrame()

        # 合并行情和复权因子
        df = pd.merge(daily_df, adj_df[['ts_code', 'trade_date', 'adj_factor']], on=['ts_code', 'trade_date'], how='left')
        
        # 填充缺失的复权因子 (通常复权因子只在变动日更新，但 Tushare 每天都提供。如果缺失则向前填充)
        df = df.sort_values(['ts_code', 'trade_date'])
        df['adj_factor'] = df.groupby('ts_code')['adj_factor'].ffill()

        # 获取每只股票最新的复权因子
        latest_adj = df.groupby('ts_code')['adj_factor'].transform('last')

        # 计算前复权价格
        df['qfq_close'] = df['close'] * (df['adj_factor'] / latest_adj)
        df['qfq_high'] = df['high'] * (df['adj_factor'] / latest_adj)
        
        return df

    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 MA200, 60日高点, 成交量均值
        """
        if df.empty:
            return df

        df = df.sort_values(['ts_code', 'trade_date'])
        
        # MA200 (前复权收盘价)
        df['ma200'] = df.groupby('ts_code')['qfq_close'].transform(lambda x: x.rolling(window=200).mean())
        
        # 60日高点 (不包含当前日，所以用 shift(1))
        df['high60'] = df.groupby('ts_code')['qfq_high'].transform(lambda x: x.shift(1).rolling(window=60).max())

        # 30日高点
        df['high30'] = df.groupby('ts_code')['qfq_high'].transform(lambda x: x.shift(1).rolling(window=30).max())
        
        # 成交量均值 (不包含当前日)
        df['vol_ma3'] = df.groupby('ts_code')['vol'].transform(lambda x: x.shift(1).rolling(window=3).mean())
        df['vol_ma7'] = df.groupby('ts_code')['vol'].transform(lambda x: x.shift(1).rolling(window=7).mean())
        
        return df
