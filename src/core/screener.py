import logging

from src.strategies.base import BaseStrategy
from src.strategies.breakout_30 import Breakout30Strategy

logger = logging.getLogger(__name__)


class Screener:
    """策略协调器——将具体策略的筛选逻辑委托给传入的 BaseStrategy"""

    def __init__(self, stock_names_dict: dict, strategy: BaseStrategy = None):
        self.stock_names = stock_names_dict
        self.strategy = strategy or Breakout30Strategy()

    def screen(self, df, target_date: str):
        if df is None or df.empty:
            return df
        return self.strategy.screen(df, target_date, self.stock_names)
