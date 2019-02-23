"""
Various testing utilities for use with hypothesis.

For god sake, do not import this anywhere outside tests!
"""
import datetime
import json
from typing import Callable, Any

from hypothesis import strategies as st
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

    @st.composite
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


# noinspection PyPep8Naming
def material(Name=st.text(), Count=st.integers()):  # noqa
    return st.fixed_dictionaries({'Name': Name, 'Count': Count})


valid_material = material(Name=st.text(min_size=1), Count=st.integers(min_value=1))


# noinspection PyPep8Naming
def MaterialsEvent(material=material(), Raw=sentinel, Manufactured=sentinel, Encoded=sentinel):  # noqa
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

    return event_strategy('Materials', **kwargs)


TestEvent = event_strategy('Test')

FileheaderEvent = event_strategy('Fileheader', part=int, language=str,
                                 gameversion=st.none() | st.integers() | st.text(),
                                 build=st.none() | st.integers() | st.text())


# noinspection PyPep8Naming
def Faction(Name=st.text(), FactionState=st.text(), Government=st.text(), Influence=st.floats()):  # noqa
    state = st.fixed_dictionaries({'State': st.text(), 'Trend': st.integers()})
    return st.fixed_dictionaries({
        'Name': Name,
        'FactionState': FactionState,
        'Government': Government,
        'Influence': Influence,
        'PendingStates': st.lists(state),
        'RecovingStates': st.lists(state),
    })


FSDJumpEvent = event_strategy(
    event_name='FSDJump',
    StarSystem=st.text(),
    SystemAddress=st.integers(),
    StarPos=st.tuples(st.floats(), st.floats(), st.floats()),
    Body=st.text(),
    FuelUsed=st.floats(),
    JumpDist=st.floats(),
    BoostUsed=st.booleans(),
    SystemFaction=st.text(),
    FactionState=st.text(),
    SystemAllegiance=st.text(),
    SystemEconomy=st.text(),
    SystemSecondEconomy=st.text(),
    SystemGovernment=st.text(),
    SystemSecurity=st.text(),
    Population=st.integers(),
    Wanted=st.booleans(),
    Factions=st.lists(Faction())
)


LocationEvent = event_strategy(
    event_name='Location',
    Docked=st.booleans(),
    StarSystem=st.text(),
    SystemAddress=st.integers(),
    StarPos=st.tuples(st.floats(), st.floats(), st.floats()),
    Body=st.text(),
    SystemFaction=st.text(),
    FactionState=st.text(),
    SystemAllegiance=st.text(),
    SystemEconomy=st.text(),
    SystemSecondEconomy=st.text(),
    SystemGovernment=st.text(),
    SystemSecurity=st.text(),
    Wanted=st.booleans(),
    Factions=st.lists(Faction()),
)


def random_keys_removed(strategy: SearchStrategy[journal.Event]) -> SearchStrategy[journal.Event]:
    keys = tuple(utils.drop_keys(strategy.example().data, 'timestamp', 'event').keys())

    @st.composite
    def func(draw, drop_keys=st.lists(st.sampled_from(keys), unique=True)):
        event = draw(strategy)
        return make_event(event.name, event.timestamp,
                          **utils.drop_keys(event.data, 'event', 'timestamp', *draw(drop_keys)))

    return func()
