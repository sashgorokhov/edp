import pytest
from hypothesis import given

from edp.contrib import gamestate
from edp.utils import hypothesis_strategies


@pytest.fixture()
def gamestatedata():
    return gamestate.GameStateData()


@given(hypothesis_strategies.CommanderEvent())
def test_commander_event(request, event):
    state: gamestate.GameStateData = request.getfixturevalue('gamestatedata')
    list(gamestate.mutation_registry.execute(event.name, event=event, state=state))

    assert state.commander.name == event.data['Name']
    assert state.commander.frontier_id == event.data['FID']


@pytest.mark.xfail()
@given(hypothesis_strategies.MaterialsEvent(material=hypothesis_strategies.valid_material))
def test_materials_event(request, event):
    state: gamestate.GameStateData = request.getfixturevalue('gamestatedata')
    list(gamestate.mutation_registry.execute(event.name, event=event, state=state))

    for category in ['Raw', 'Encoded', 'Manufactured']:
        for material in event.data[category]:
            assert material['Name'] in state.material_storage[category]
            assert state.material_storage[category][material['Name']] == material['Count']
