"""
Define all game and journal entities to have determined and typed behavior
"""
from collections import defaultdict
from operator import attrgetter, methodcaller
from typing import Dict, Optional, Tuple, List

import dataclasses

from edp.contracts import PositiveInt, NotEmptyStr, require_contract
from edp.utils import infer_category


class BaseEntity:
    """Base entity class with logic for watching for changes"""
    __sentinel__ = object()
    __changed__ = False

    def __init__(self, *args, **kwargs):
        super(BaseEntity, self).__init__(*args, **kwargs)
        self.reset_changed()

    def __setattr__(self, key, value):
        if value is self.__sentinel__:
            return None
        if value != getattr(self, key, object()):
            super(BaseEntity, self).__setattr__('__changed__', True)
        return super(BaseEntity, self).__setattr__(key, value)

    def _dataclass_type_fields(self):
        # noinspection PyUnresolvedReferences
        for field_name, field in self.__dataclass_fields__.items():  # pylint: disable=no-member
            if dataclasses.is_dataclass(field.type):
                obj = getattr(self, field_name)
                if isinstance(obj, BaseEntity):
                    yield obj

    @property
    def is_changed(self):
        """Return True if this dataclass or one of its childs is changed"""
        return self.__changed__ or any(map(attrgetter('is_changed'), self._dataclass_type_fields()))

    def reset_changed(self):
        """Reset changed status on this dataclass and its childs"""
        self.__changed__ = False
        list(map(methodcaller('reset_changed'), self._dataclass_type_fields()))

    def clear(self):
        """Reset all fields to their default values, recursive into children"""
        # noinspection PyUnresolvedReferences
        for field_name, field in self.__dataclass_fields__.items():  # pylint: disable=no-member
            value = getattr(self, field_name)
            if dataclasses.is_dataclass(field.type) and isinstance(value, BaseEntity):
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
class Commander(BaseEntity):
    """Describes commander"""
    name: Optional[str] = None
    frontier_id: Optional[str] = None


@dataclasses.dataclass
class Material(BaseEntity):
    """
    Describes material

    Also defines + and - magics to allow easier materials addition and substitution
    """
    name: str
    count: int
    category: str

    def __add__(self, other):
        if not isinstance(other, Material):
            raise TypeError(f"unsupported operand type(s) for +: '{type(self)}' and '{type(other)}'")
        if self.name == other.name and self.category == other.category:
            self.count += abs(other.count)
        else:
            raise TypeError(f'Materials are not the same: {self} != {other}')
        return self

    def __sub__(self, other):
        if not isinstance(other, Material):
            raise TypeError(f"unsupported operand type(s) for +: '{type(self)}' and '{type(other)}'")
        if self.name == other.name and self.category == other.category:
            self.count -= abs(other.count)
            if self.count < 0:
                self.count = 0
        else:
            raise TypeError(f'Materials are not the same: {self} != {other}')
        return self


class MaterialStorage:
    """
    Represents materials storage
    """

    def __init__(self):
        super(MaterialStorage, self).__init__()
        # Material category -> Material name -> Material count
        self._data: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    @require_contract('category', NotEmptyStr)
    def __getitem__(self, category: str) -> Dict[str, int]:
        """Return materials in category"""
        category = infer_category(category)
        return self._data[category]

    @require_contract('name', NotEmptyStr)
    @require_contract('count', PositiveInt)
    @require_contract('category', NotEmptyStr)
    def add_material(self, name: str, count: int, category: str) -> int:
        """
        Add material to storage.

        Returns this material count in storage.
        """
        self[category][name] += count
        return self[category][name]

    @require_contract('name', NotEmptyStr)
    @require_contract('count', PositiveInt)
    @require_contract('category', NotEmptyStr)
    def remove_material(self, name: str, count: int, category: str) -> int:
        """
        Remove material from storage.

        Returns this material count in storage.
        """
        self[category][name] -= count
        if self[category][name] < 0:
            self[category][name] = 0
        return self[category][name]

    @property
    def raw(self) -> Dict[str, int]:
        """Shortcut for raw category materials"""
        return self['raw']

    @property
    def encoded(self) -> Dict[str, int]:
        """Shortcut for encoded category materials"""
        return self['encoded']

    @property
    def manufactured(self) -> Dict[str, int]:
        """Shortcut for manufactured category materials"""
        return self['manufactured']


@dataclasses.dataclass
class Ship(BaseEntity):
    """
    Defines a ship
    """
    model: Optional[str] = None
    id: Optional[int] = None
    name: Optional[str] = None
    ident: Optional[str] = None


@dataclasses.dataclass
class Rank(BaseEntity):
    """
    Container for rank information
    """
    combat: Optional[int] = None
    combat_progress: Optional[int] = None

    trade: Optional[int] = None
    trade_progress: Optional[int] = None

    explore: Optional[int] = None
    explore_progress: Optional[int] = None

    empire: Optional[int] = None
    empire_progress: Optional[int] = None

    federation: Optional[int] = None
    federation_progress: Optional[int] = None

    cqc: Optional[int] = None
    cqc_progress: Optional[int] = None


@dataclasses.dataclass
class Reputation(BaseEntity):
    """
    Reputation info
    """
    empire: Optional[float] = None
    federation: Optional[float] = None
    alliance: Optional[float] = None


@dataclasses.dataclass
class Engineer(BaseEntity):
    """
    Defines engineer and commander reputation with him
    """
    name: str
    id: int
    progress: str
    rank: Optional[int]
    rank_progress: Optional[int]


@dataclasses.dataclass
class Station(BaseEntity):
    """
    Container for station information
    """
    market: Optional[int] = None
    name: Optional[str] = None
    type: Optional[str] = None
    faction: Optional[str] = None
    government: Optional[str] = None
    services: List[str] = dataclasses.field(default_factory=list)
    economy: Optional[str] = None


@dataclasses.dataclass
class Location(BaseEntity):
    """
    Container for location info
    """
    docked: bool = False
    supercruise: bool = False
    system: Optional[str] = None
    address: Optional[int] = None
    pos: Optional[Tuple[float, float, float]] = None
    allegiance: Optional[str] = None
    economy: Optional[str] = None
    economy_second: Optional[str] = None
    government: Optional[str] = None
    security: Optional[str] = None
    population: Optional[int] = None
    faction: Optional[str] = None
    station: Station = dataclasses.field(default_factory=Station)
