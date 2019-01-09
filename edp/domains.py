import dataclasses
from operator import attrgetter, methodcaller
from typing import Dict, Optional, Tuple

UNKNOWN = 'unknown'


class _BaseDomain:
    __sentinel__ = object()
    __changed__ = False

    def __setattr__(self, key, value):
        if value is self.__sentinel__:
            return
        if value != getattr(self, key, object()):
            super(_BaseDomain, self).__setattr__('__changed__', True)
        return super(_BaseDomain, self).__setattr__(key, value)

    def _dataclass_type_fields(self):
        for field_name, field in self.__dataclass_fields__.items():
            if dataclasses.is_dataclass(field.type):
                obj = getattr(self, field_name)
                if isinstance(obj, _BaseDomain):
                    yield obj

    @property
    def is_changed(self):
        return self.__changed__ or any(map(attrgetter('is_changed'), self._dataclass_type_fields()))

    def reset_changed(self):
        self.__changed__ = False
        list(map(methodcaller('reset_changed'), self._dataclass_type_fields()))


@dataclasses.dataclass
class Commander(_BaseDomain):
    name: str = UNKNOWN
    frontier_id: str = UNKNOWN


@dataclasses.dataclass
class Material(_BaseDomain):
    name: str
    count: int


@dataclasses.dataclass
class MaterialStorage(_BaseDomain):
    raw: Dict[str, Material] = dataclasses.field(default_factory=dict)
    encoded: Dict[str, Material] = dataclasses.field(default_factory=dict)
    manufactured: Dict[str, Material] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class Ship(_BaseDomain):
    model: str = UNKNOWN
    id: int = -1
    name: str = UNKNOWN
    ident: str = UNKNOWN


@dataclasses.dataclass
class Rank(_BaseDomain):
    combat: int = 0
    combat_progress: int = 0

    trade: int = 0
    trade_progress: int = 0

    explore: int = 0
    explore_progress: int = 0

    empire: int = 0
    empire_progress: int = 0

    federation: int = 0
    federation_progress: int = 0

    cqc: int = 0
    cqc_progress: int = 0


@dataclasses.dataclass
class Reputation(_BaseDomain):
    empire: float = 0.0
    federation: float = 0.0
    alliance: float = 0.0


@dataclasses.dataclass
class Engineer(_BaseDomain):
    name: str
    id: int
    progress: str
    rank: Optional[int]
    rank_progress: Optional[int]


@dataclasses.dataclass
class Location(_BaseDomain):
    docked: bool = False
    system: str = UNKNOWN
    address: int = 0
    pos: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    allegiance: str = UNKNOWN
    economy: str = UNKNOWN
    economy_second: str = UNKNOWN
    government: str = UNKNOWN
    security: str = UNKNOWN
    population: int = 0
    faction: str = UNKNOWN
