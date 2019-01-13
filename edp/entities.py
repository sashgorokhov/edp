from operator import attrgetter, methodcaller
from typing import Dict, Optional, Tuple, List

import dataclasses


class _BaseEntity:
    __sentinel__ = object()
    __changed__ = False

    def __setattr__(self, key, value):
        if value is self.__sentinel__:
            return
        if value != getattr(self, key, object()):
            super(_BaseEntity, self).__setattr__('__changed__', True)
        return super(_BaseEntity, self).__setattr__(key, value)

    def _dataclass_type_fields(self):
        for field_name, field in self.__dataclass_fields__.items():
            if dataclasses.is_dataclass(field.type):
                obj = getattr(self, field_name)
                if isinstance(obj, _BaseEntity):
                    yield obj

    @property
    def is_changed(self):
        return self.__changed__ or any(map(attrgetter('is_changed'), self._dataclass_type_fields()))

    def reset_changed(self):
        self.__changed__ = False
        list(map(methodcaller('reset_changed'), self._dataclass_type_fields()))

    def clear(self):
        for field_name, field in self.__dataclass_fields__.items():
            value = getattr(self, field_name)
            if dataclasses.is_dataclass(field.type) and isinstance(value, _BaseEntity):
                value.clear()
            else:
                if field.default is dataclasses.MISSING:
                    if field.default_factory is dataclasses.MISSING:
                        setattr(self, field_name, None)
                    else:
                        setattr(self, field_name, field.default_factory())
                else:
                    setattr(self, field_name, field.default)


@dataclasses.dataclass()
class Commander(_BaseEntity):
    name: str = None
    frontier_id: str = None


@dataclasses.dataclass
class Material(_BaseEntity):
    name: str
    count: int


@dataclasses.dataclass
class MaterialStorage(_BaseEntity):
    raw: Dict[str, Material] = dataclasses.field(default_factory=dict)
    encoded: Dict[str, Material] = dataclasses.field(default_factory=dict)
    manufactured: Dict[str, Material] = dataclasses.field(default_factory=dict)

    _category_map = {
        'Raw': 'raw',
        'Encoded': 'encoded',
        'Manufactured': 'manufactured'
    }

    def __getitem__(self, item):
        if item in self._category_map:
            return getattr(self, self._category_map[item])
        # noinspection PyUnresolvedReferences
        return super(MaterialStorage, self).__getitem__(item)


@dataclasses.dataclass
class Ship(_BaseEntity):
    model: str = None
    id: int = None
    name: str = None
    ident: str = None


@dataclasses.dataclass
class Rank(_BaseEntity):
    combat: int = None
    combat_progress: int = None

    trade: int = None
    trade_progress: int = None

    explore: int = None
    explore_progress: int = None

    empire: int = None
    empire_progress: int = None

    federation: int = None
    federation_progress: int = None

    cqc: int = None
    cqc_progress: int = None


@dataclasses.dataclass
class Reputation(_BaseEntity):
    empire: float = None
    federation: float = None
    alliance: float = None


@dataclasses.dataclass
class Engineer(_BaseEntity):
    name: str
    id: int
    progress: str
    rank: Optional[int]
    rank_progress: Optional[int]


@dataclasses.dataclass
class Station(_BaseEntity):
    market: int = None
    name: str = None
    type: str = None
    faction: str = None
    government: str = None
    services: List[str] = dataclasses.field(default_factory=list)
    economy: str = None


@dataclasses.dataclass
class Location(_BaseEntity):
    docked: bool = False
    supercruise: bool = False
    system: str = None
    address: int = None
    pos: Tuple[float, float, float] = None
    allegiance: str = None
    economy: str = None
    economy_second: str = None
    government: str = None
    security: str = None
    population: int = None
    faction: str = None
    station: Station = dataclasses.field(default_factory=Station)
