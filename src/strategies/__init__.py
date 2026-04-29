# 导入各策略文件，触发 __init_subclass__ 自动注册
import src.strategies.breakout_30  # noqa: F401
import src.strategies.breakout_60  # noqa: F401

from src.strategies.base import BaseStrategy
from src.strategies.registry import StrategyRegistry

__all__ = ["BaseStrategy", "StrategyRegistry"]
