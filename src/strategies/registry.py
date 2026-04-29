import logging
from typing import List, Type

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """策略注册表，按名称注册/查找策略类"""

    _strategies: dict = {}

    @classmethod
    def register(cls, strategy_cls: Type) -> None:
        name = strategy_cls.name
        if not name:
            raise ValueError(f"Strategy {strategy_cls.__name__} must define class var 'name'")
        cls._strategies[name] = strategy_cls
        logger.debug(f"Registered strategy: {name}")

    @classmethod
    def get(cls, name: str) -> Type:
        if name not in cls._strategies:
            raise KeyError(f"Unknown strategy '{name}'. Available: {list(cls._strategies.keys())}")
        return cls._strategies[name]

    @classmethod
    def list(cls) -> List[str]:
        return list(cls._strategies.keys())

    @classmethod
    def resolve(cls, names: List[str]) -> list:
        """解析策略名称列表，返回实例化后的策略对象列表"""
        instances = []
        for name in names:
            name = name.strip()
            if not name:
                continue
            try:
                instances.append(cls.get(name)())
            except KeyError as e:
                logger.warning(str(e))
        return instances
