from unittest import mock

import pytest

from edp import utils


@pytest.mark.parametrize(('source', 'subset', 'result'), [
    ({}, {}, True),
    ({1: 2}, {}, True),
    ({}, {1: 2}, False),
    ({1: 2}, {1: 2}, True),
    ({1: 3}, {1: 2}, False),
    ({1: 2, 3: 4}, {1: 2}, True),
    ({1: 2, 3: 4}, {1: 2, 5: 6}, False),
])
def test_is_dict_subset(source, subset, result):
    assert utils.is_dict_subset(source, subset) == result


def test_catcherr():
    mock_func = mock.MagicMock()
    mock_func.side_effect = ValueError

    utils.catcherr(mock_func)()


@pytest.mark.parametrize(('d', 'k', 'result'), [
    ({}, [], {}),
    ({}, [1], {}),
    ({1: 2}, [1], {1: 2}),
    ({2: 3}, [1], {}),
    ({1: 2, 2: 3}, [1, 2], {1: 2, 2: 3}),
    ({1: 2, 2: 3}, [1, 2, 4], {1: 2, 2: 3}),
    ({1: 2, 2: 3, 4: 5}, [1, 2], {1: 2, 2: 3}),
])
def test_subset(d, k, result):
    assert utils.dict_subset(d, *k) == result


@pytest.mark.parametrize(('d', 'k', 'result', 'raises'), [
    ({}, [], {}, False),
    ({}, [1], {}, True),
    ({1: 2}, [1], {1: 2}, False),
    ({1: 2}, [1, 2], {1: 2}, True),
])
def test_subset_strict(d, k, result, raises):
    if not raises:
        assert utils.dict_subset(d, *k, strict=True) == result
    else:
        with pytest.raises(KeyError):
            assert utils.dict_subset(d, *k, strict=True)


@pytest.mark.parametrize(('d', 'keys', 'result'), [
    ({}, tuple(), True),
    ({1: 2}, tuple(), True),
    ({}, (1,), False),
    ({1: 2}, (1,), True),
])
def test_has_keys(d, keys, result):
    assert utils.has_keys(d, *keys) == result


@pytest.mark.parametrize(('d', 'keys_map', 'result'), [
    ({}, {}, {}),
    ({1: 2}, {}, {}),
    ({}, {'foo': 'bar'}, {}),
    ({'key': 'value'}, {'foo': 'bar'}, {}),
    ({'foo': 'value'}, {'foo': 'bar'}, {'bar': 'value'}),
])
def test_map_keys(d, keys_map, result):
    assert utils.map_keys(d, **keys_map) == result


@pytest.mark.parametrize(('d', 'keys_map'), [
    ({}, {'foo': 2}),
    ({1: 2}, {'foo': 3}),
])
def test_map_keys_strict(d, keys_map):
    with pytest.raises(KeyError):
        utils.map_keys(d, **keys_map, strict=True)


@pytest.mark.parametrize(('version_string', 'version'), [
    ('0.0.0', (0, 0, 0)),
    ('v0.0.0', (0, 0, 0)),
    ('0.0.1', (0, 0, 1)),
    ('0.1.1', (0, 1, 1)),
    ('1.1.1', (1, 1, 1)),
    ('v1.1.1', (1, 1, 1)),
])
def test_version_bits(version_string, version):
    assert utils.version_bits(version_string) == version


@pytest.mark.parametrize(('v1', 'v2', 'newer'), [
    ('0.0.0', '0.0.0', False),
    ('0.0.0', '0.0.1', False),
    ('0.0.1', '0.0.1', False),
    ('0.1.0', '0.0.1', True),
    ('1.0.0', '0.0.1', True),
    ('1.0.0', '0.1.0', True),
])
def test_is_version_newer(v1, v2, newer):
    assert utils.is_version_newer(v1, v2) == newer


@pytest.mark.parametrize(('p1', 'p2', 'result'), [
    ((1, 1, 1), (2, 2, 2), 1.732)
])
def test_space_distance(p1, p2, result):
    assert round(utils.space_distance(p1, p2), 3)


@pytest.mark.parametrize(('seq', 'size', 'result'), [
    ((1, 2, 3), 1, [(1,), (2,), (3,)]),
    ((1, 2, 3), 2, [(1, 2), (3,)]),
    ((1, 2, 3), 3, [(1, 2, 3)]),
    ((1, 2, 3), 4, [(1, 2, 3)]),
    ((1, 2, 3, 4, 5, 6), 2, [(1, 2), (3, 4), (5, 6)]),
    ((1, 2, 3, 4, 5, 6, 7), 2, [(1, 2), (3, 4), (5, 6), (7,)]),
])
def test_chunked(seq, size, result):
    assert list(utils.chunked(seq, size)) == result


@pytest.mark.parametrize(('d', 'keys', 'result'), [
    ({}, tuple(), {}),
    ({1: 2}, tuple(), {1: 2}),
    ({1: 2}, (1,), {}),
    ({1: 2}, (2,), {1: 2}),
    ({1: 2, 3: 4}, (1,), {3: 4}),
    ({1: 2, 3: 4}, (1, 5), {3: 4}),
])
def test_drop_keys(d, keys, result):
    assert utils.drop_keys(d, *keys) == result
