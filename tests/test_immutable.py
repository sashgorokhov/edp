import functools
import typing

import pytest

from edp.utils import immutable

CASES = [
    [],
    {},
    [{}],
    {1: []},
    [1, 2, 3],
    {1: 2, 3: 4},
    {1: 2, 3: [1, 2, 3]},
    [{1: 2}, {3: 4}],
    [{1: 2, 3: [{4: 5}]}],
]


def pytest_generate_tests(metafunc):
    if 'immutable_obj' in metafunc.fixturenames:
        params = []

        # Parametrize every test that requires immutable_obj fixture with data from every case.
        # case is made immutable and then walked reqursively. Every Mapping or Sequence in that object
        # is passed as param to tests.
        for case in CASES:
            def walk_recursively(obj):
                if isinstance(obj, typing.Mapping):
                    params.append(obj)
                    list(map(walk_recursively, obj.values()))
                elif isinstance(obj, typing.Sequence):
                    params.append(obj)
                    list(map(walk_recursively, obj))

            v = immutable.make_immutable(case)
            walk_recursively(v)

        metafunc.parametrize("immutable_obj", params)


def test_immutable_dict_is_mapping():
    assert isinstance(immutable.make_immutable({}), typing.Mapping)


def test_immutable_list_is_sequence():
    assert isinstance(immutable.make_immutable([]), typing.Sequence)


def need_mapping(func):
    @functools.wraps(func)
    def wrapper(*args, immutable_obj, **kwargs):
        if not isinstance(immutable_obj, typing.Mapping):
            return
        func(*args, immutable_obj, **kwargs)

    return wrapper


def need_sequence(func):
    @functools.wraps(func)
    def wrapper(*args, immutable_obj, **kwargs):
        if not isinstance(immutable_obj, typing.Sequence):
            return
        func(*args, immutable_obj, **kwargs)

    return wrapper


@need_mapping
def test_immutable_dict_update(immutable_obj):
    with pytest.raises(PermissionError):
        immutable_obj.update({})


@need_mapping
def test_immutable_dict_setitem(immutable_obj):
    with pytest.raises(PermissionError):
        immutable_obj[1] = 2


@need_mapping
def test_immutable_dict_pop(immutable_obj):
    with pytest.raises(PermissionError):
        immutable_obj.pop('key')


@need_sequence
def test_immutable_list_append(immutable_obj):
    with pytest.raises(PermissionError):
        immutable_obj.append(1)


@need_sequence
def test_immutable_list_pop(immutable_obj):
    with pytest.raises(PermissionError):
        immutable_obj.pop()


@need_sequence
def test_immutable_list_insert(immutable_obj):
    with pytest.raises(PermissionError):
        immutable_obj.insert(0, 1)


@need_sequence
def test_immutable_list_setitem(immutable_obj):
    with pytest.raises(PermissionError):
        immutable_obj[1] = 2
