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
    assert utils.subset(d, *k) == result


@pytest.mark.parametrize(('d', 'k', 'result', 'raises'), [
    ({}, [], {}, False),
    ({}, [1], {}, True),
    ({1: 2}, [1], {1: 2}, False),
    ({1: 2}, [1, 2], {1: 2}, True),
])
def test_subset_strict(d, k, result, raises):
    if not raises:
        assert utils.subset(d, *k, strict=True) == result
    else:
        with pytest.raises(KeyError):
            assert utils.subset(d, *k, strict=True)


@pytest.mark.parametrize(('d', 'keys', 'result'), [
    ({}, tuple(), True),
    ({1: 2}, tuple(), True),
    ({}, (1,), False),
    ({1: 2}, (1,), True),
])
def test_has_keys(d, keys, result):
    assert utils.has_keys(d, *keys) == result
