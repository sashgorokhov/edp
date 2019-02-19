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
