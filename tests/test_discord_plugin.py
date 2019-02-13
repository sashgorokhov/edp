from unittest import mock

import pytest

from edp.contrib import discord_rich_presence, gamestate


@pytest.fixture()
def client_mock():
    return mock.MagicMock()


@pytest.fixture()
def discord_plugin(client_mock):
    plugin = discord_rich_presence.DiscordRichPresencePlugin()
    with mock.patch.object(plugin, '_rpc_client', new=client_mock):
        yield plugin


@pytest.mark.parametrize('enabled', [True, False])
def test_plugin_enabled(enabled, discord_plugin):
    settings = discord_rich_presence.DRPSettings.get_insance()
    settings.enabled = enabled
    assert discord_plugin.is_enalbed() == enabled


def test_set_state_sets_timestamp(discord_plugin):
    state = discord_rich_presence.DRPState('test', 'test', 100.0)

    discord_plugin.set_state(state)

    assert discord_plugin._current_state is not None
    assert discord_plugin._current_state is state
    assert discord_plugin._current_state.timestamp_start != 100.0


def test_on_game_state_changed_hides_location(discord_plugin):
    state = gamestate.GameStateData()
    state.location.system = 'test 1234'

    settings = discord_rich_presence.DRPSettings.get_insance()

    settings.show_location = True
    discord_plugin.on_game_state_changed(state)
    assert state.location.system in discord_plugin._current_state.details

    settings.show_location = False
    discord_plugin.on_game_state_changed(state)
    assert state.location.system not in discord_plugin._current_state.details


def test_update_discord_state(discord_plugin, client_mock):
    state = discord_rich_presence.DRPState('foo', 'bar')
    discord_plugin.set_state(state)

    discord_plugin.update_discord_state()

    client_mock.set_activity.assert_called_once()
    assert discord_plugin._current_state is None
    activity = client_mock.set_activity.call_args[0][0]
    assert activity['state'] == 'foo'
    assert activity['details'] == 'bar'


def test_update_discord_state_no_state(discord_plugin, client_mock):
    discord_plugin._current_state = None

    discord_plugin.update_discord_state()

    client_mock.set_activity.assert_not_called()


def test_update_discord_state_assets_large_text_set(discord_plugin, client_mock):
    state = discord_rich_presence.DRPState('foo', 'bar', assets_large_text='test')
    discord_plugin.set_state(state)

    discord_plugin.update_discord_state()

    client_mock.set_activity.assert_called_once()
    activity = client_mock.set_activity.call_args[0][0]

    assert 'assets' in activity
    assert activity['assets']['large_text'] == 'test'


def test_update_discord_state_assets_large_image_set(discord_plugin, client_mock):
    state = discord_rich_presence.DRPState('foo', 'bar', assets_large_image='test')
    discord_plugin.set_state(state)

    discord_plugin.update_discord_state()

    client_mock.set_activity.assert_called_once()
    activity = client_mock.set_activity.call_args[0][0]

    assert 'assets' in activity
    assert activity['assets']['large_image'] == 'test'


def test_update_discord_state_assets_small_text_set(discord_plugin, client_mock):
    state = discord_rich_presence.DRPState('foo', 'bar', assets_small_text='test')
    discord_plugin.set_state(state)

    discord_plugin.update_discord_state()

    client_mock.set_activity.assert_called_once()
    activity = client_mock.set_activity.call_args[0][0]

    assert 'assets' in activity
    assert activity['assets']['small_text'] == 'test'


def test_update_discord_state_assets_small_image_set(discord_plugin, client_mock):
    state = discord_rich_presence.DRPState('foo', 'bar', assets_small_image='test')
    discord_plugin.set_state(state)

    discord_plugin.update_discord_state()

    client_mock.set_activity.assert_called_once()
    activity = client_mock.set_activity.call_args[0][0]

    assert 'assets' in activity
    assert activity['assets']['small_image'] == 'test'
