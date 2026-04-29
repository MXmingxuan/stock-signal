import pandas as pd

from src.strategies.base import BaseStrategy


class Breakout60Strategy(BaseStrategy):
    """收盘价突破60日新高（首次），且站上MA200"""

    name = "breakout_60"
    description = "收盘价突破60日新高（首次），且站上MA200"

    csv_columns = {
        'trade_date': '交易日期',
        'ts_code': '股票代码',
        'name': '股票名称',
        'qfq_close': '当日前复权收盘价',
        'turnover_rate': '当日换手率',
        'ma200': '当日前复权MA200',
        'high60': '过去60日最高前复权high',
        'is_first_break': '是否首次突破(60日)',
        'vol': '当日成交量',
        'vol_ma3': '过去3日平均成交量',
        'vol_ratio_3': '当日/3日均量',
        'vol_ma7': '过去7日平均成交量',
        'vol_ratio_7': '当日/7日均量',
    }

    def screen(self, df: pd.DataFrame, target_date: str, stock_names: dict) -> pd.DataFrame:
        df = df.sort_values(['ts_code', 'trade_date'])

        # 标记当日是否突破60日高点
        df['is_breakout'] = df['qfq_close'] > df['high60']

        # 判断是否首次突破（昨日未突破）
        df['prev_is_breakout'] = df.groupby('ts_code')['is_breakout'].shift(1)
        df['is_first_break'] = (df['is_breakout']) & (df['prev_is_breakout'] == False)

        # 筛选目标日期
        today_df = df[df['trade_date'] == target_date].copy()
        if today_df.empty:
            return pd.DataFrame()

        # 三条件：站上MA200 + 突破60日高 + 首次突破
        mask = (
            (today_df['qfq_close'] > today_df['ma200']) &
            (today_df['is_breakout']) &
            (today_df['is_first_break'])
        )
        results = today_df[mask].copy()

        # 补充字段
        results['name'] = results['ts_code'].map(stock_names)
        results['vol_ratio_3'] = results['vol'] / results['vol_ma3']
        results['vol_ratio_7'] = results['vol'] / results['vol_ma7']

        return results
