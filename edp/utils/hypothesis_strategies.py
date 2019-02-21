"""
Various testing utilities for use with hypothesis.

For god sake, do not import this anywhere outside tests!
"""
import datetime
import json
from typing import Callable, Any

from hypothesis import strategies as st
from hypothesis._strategies import composite, CompositeStrategy
from hypothesis.searchstrategy import SearchStrategy

from edp import journal, utils

sentinel = object()


def make_event(_name, timestamp=None, **kwargs) -> journal.Event:
    """
    Build Event
    """
    dt = timestamp or datetime.datetime.now()
    data = {
        'event': _name,
        'timestamp': utils.to_ed_timestamp(dt),
        **kwargs
    }
    data_str = json.dumps(data)
    return journal.Event(dt, _name, data, data_str)


def event_strategy(event_name, **fields) -> Callable[..., SearchStrategy[Any]]:
    """Build composite strategy that generates Events"""
    @composite
    def func(draw, **kwargs):
        kwargs.setdefault('timestamp', st.datetimes())
        data = fields.copy()
        data.update(kwargs)
        for key, value in data.items():
            if isinstance(value, SearchStrategy):
                data[key] = draw(value)
            elif isinstance(value, type):
                data[key] = draw(st.from_type(value))
        return make_event(event_name, **data)

    return func


CommanderEvent = event_strategy('Commander', Name=str, FID=str)


@composite
def material_strategy(draw, Name=st.text(), Count=st.integers()):  # noqa
    return {'Name': draw(Name), 'Count': draw(Count)}


valid_material = material_strategy(Name=st.text(min_size=1), Count=st.integers(min_value=1))


@composite
def MaterialsEvent(draw, material=material_strategy(), Raw=sentinel, Manufactured=sentinel, Encoded=sentinel):  # noqa
    kwargs = {}
    if Raw is sentinel:
        Raw = st.lists(material)
    if Manufactured is sentinel:
        Manufactured = st.lists(material)
    if Encoded is sentinel:
        Encoded = st.lists(material)

    if Raw is not None:
        kwargs['Raw'] = Raw
    if Manufactured is not None:
        kwargs['Manufactured'] = Manufactured
    if Encoded is not None:
        kwargs['Encoded'] = Encoded

    return draw(event_strategy('Materials', **kwargs)())


TestEvent = event_strategy('Test')

FileheaderEvent = event_strategy('Fileheader', part=int, language=str,
                                 gameversion=st.none() | st.integers() | st.text(),
                                 build=st.none() | st.integers() | st.text())
