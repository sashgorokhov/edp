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
