from abc import ABC, abstractmethod
from typing import ClassVar, Dict

import pandas as pd

from src.strategies.registry import StrategyRegistry


class BaseStrategy(ABC):
    """选股策略基类——新建策略只需继承此类并定义 name/description/csv_columns + screen()"""

    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    csv_columns: ClassVar[Dict[str, str]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.name:
            StrategyRegistry.register(cls)

    @abstractmethod
    def screen(self, df: pd.DataFrame, target_date: str, stock_names: dict) -> pd.DataFrame:
        ...
