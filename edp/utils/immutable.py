import collections

import dataclasses


def _stub(self, *args, **kwargs):
    raise PermissionError('Mutating immutable object')


class ImmutableList(collections.UserList):
    __immutable_methods__ = ('__setitem__', 'append', 'clear', 'insert', 'pop', 'remove', '__add__', '__iadd__',
                             '__mul__', '__imul__', 'extend')

    for method_name in __immutable_methods__:
        locals()[method_name] = _stub

    def __init__(self, data: list = None):
        self.data = data or []


class ImmutableDict(collections.UserDict):
    __immutable_methods__ = ('__setitem__', '__delitem__', 'pop', 'update', 'setdefault', 'popitem')

    for method_name in __immutable_methods__:
        locals()[method_name] = _stub

    def __init__(self, data: dict = None):
        self.data = data or {}


def make_immutable(obj):
    if isinstance(obj, dict):
        return ImmutableDict({k: make_immutable(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return ImmutableList([make_immutable(v) for v in obj])
    elif dataclasses.is_dataclass(obj):
        return make_immutable(dataclasses.asdict(obj))
    return obj
