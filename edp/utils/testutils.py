from typing import Tuple, Union

import pytest
from hypothesis.searchstrategy import SearchStrategy


def hypothesis_parametrize(argspec: Union[Tuple[str], str], strategy: SearchStrategy, max_examples=10):
    return pytest.mark.parametrize(argspec, (strategy.example() for i in range(max_examples)))
