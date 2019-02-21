"""
Experimental module to extend and simplify dpcontracts functionality
"""
import collections
import inspect
import typing

from dpcontracts import require

NotEmptyStr = typing.NewType('NotEmptyStr', str)
PositiveInt = typing.NewType('PositiveInt', int)

not_none = lambda v: v is not None
is_none = lambda v: v is None
is_str = lambda v: not_none(v) and isinstance(v, str)
is_int = lambda v: not_none(v) and isinstance(v, int)
has_positive_len = lambda v: isinstance(v, collections.Sized) and len(v) > 0
is_not_empty_str = lambda v: is_str(v) and has_positive_len(v)
is_positive_int = lambda v: is_int(v) and v > 0


def require_arg(arg: typing.Any, description: str, predicate: typing.Callable[[typing.Any], bool]):
    """Shortcut to add predicate on single argument"""
    return require(description, lambda args: predicate(getattr(args, arg)))


# Define contracts for types
# pylint: disable=unnecessary-lambda
TYPE_CONTRACTS = {
    str: lambda name: require_arg(name, f'`{name}` must be string',
                                  lambda arg: is_str(arg)),
    int: lambda name: require_arg(name, f'`{name}` must be integer',
                                  lambda arg: is_int(arg)),
    PositiveInt: lambda name: require_arg(name, f'`{name}` must be positive integer',
                                          lambda arg: is_positive_int(arg)),
    NotEmptyStr: lambda name: require_arg(name, f'`{name}` must be not empty string',
                                          lambda arg: is_not_empty_str(arg)),
    typing.Optional[str]: lambda name: require_arg(name, f'`{name}` must be string or None',
                                                   lambda arg: is_none(arg) or is_str(arg)),
    typing.Optional[int]: lambda name: require_arg(name, f'`{name}` must be integer or None',
                                                   lambda arg: is_none(arg) or is_int(arg)),
}


def set_contracts(func):
    """Automatically set contracts on function arguments with types from TYPE_CONTRACTS"""
    s = inspect.signature(func)
    for key, value in s.parameters.items():
        contract = TYPE_CONTRACTS.get(value.annotation, None)
        if contract:
            func = contract(key)(func)
    return func


def require_contract(name, t):
    """Shortcut to get contract for type `t` and arg name `name`"""
    return TYPE_CONTRACTS[t](name)
