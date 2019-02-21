from unittest import mock

import pytest

from edp.utils import plugins_helpers


@pytest.fixture()
def registry():
    return plugins_helpers.RoutingSwitchRegistry()


def test_registry_no_callback_execute(registry):
    with pytest.raises(KeyError):
        list(registry.execute('foo'))


def test_registry_no_callback_execute_silent(registry):
    assert list(registry.execute_silently('foo')) == []


def test_registry_callback_execute(registry):
    callback = mock.MagicMock()
    registry.register('test')(callback)

    list(registry.execute('test'))

    callback.assert_called_once_with()


def test_registry_register_callback(registry):
    callback = mock.MagicMock()
    registry.register('test', callbacks=[callback])
    assert callback in registry._callbacks['test']


def test_registry_register_callback_as_decor(registry):
    callback = mock.MagicMock()
    registry.register('test')(callback)
    assert callback in registry._callbacks['test']


def test_registry_register_several_callbacks(registry):
    callback1 = mock.MagicMock()
    callback2 = mock.MagicMock()
    registry.register('test', callbacks=[callback1, callback2])
    assert callback1 in registry._callbacks['test']
    assert callback2 in registry._callbacks['test']
