import queue
import time
from unittest import mock

import inject
import pytest

from edp import plugin


def test_callback_decor():
    @plugin.callback('test')
    def func(): pass

    assert hasattr(func, '__is_callback__')
    assert func.__is_callback__ == ('test',)


def test_callback_decor_several_signals():
    @plugin.callback('test', 'test 2')
    def func(): pass

    assert hasattr(func, '__is_callback__')
    assert func.__is_callback__ == ('test', 'test 2')


def test_scheduled_decor():
    @plugin.scheduled(1)
    def func(): pass

    assert hasattr(func, '__scheduled__')
    assert func.__scheduled__ == 1


def test_get_cls_methods():
    class Test:
        not_method = None

        class AnotherClass:
            pass

        def foo(self):
            pass

    assert list(plugin._get_cls_methods(Test)) == [Test.foo]


def test_signal_item_execute():
    callback1 = mock.MagicMock()
    callback2 = mock.MagicMock()

    signal_item = plugin.SignalItem('test', [callback1, callback2], {'foo': 'bar'})
    signal_item.execute()

    callback1.assert_called_once_with(foo='bar')
    callback2.assert_called_once_with(foo='bar')


def test_signal_item_execute_callback_exception():
    callback1 = mock.MagicMock()
    callback1.side_effect = ValueError
    callback2 = mock.MagicMock()

    signal_item = plugin.SignalItem('test', [callback1, callback2], {'foo': 'bar'})
    signal_item.execute()

    callback1.assert_called_once_with(foo='bar')
    callback2.assert_called_once_with(foo='bar')


def test_signal_executor_thread():
    callback = mock.MagicMock()
    signal_item = plugin.SignalItem('test', [callback], {})

    signal_queue = queue.Queue()
    signal_queue.put_nowait(signal_item)

    with plugin.SignalExecutorThread(signal_queue):
        time.sleep(1)

    callback.assert_called_once()
    assert signal_queue.qsize() == 0


@pytest.fixture()
def plugin_manager(tempdir):
    return plugin.PluginManager(tempdir)


def test_load_file_plugin(tempdir, plugin_manager):
    plugin_src = """
from edp.plugin import BasePlugin

class TestPlugin(BasePlugin):
    pass
    """

    (tempdir / 'test-plugin.py').write_text(plugin_src)

    plugin_manager._load_file_plugin(tempdir / 'test-plugin.py')

    assert len(plugin_manager._plugins)


def test_load_plugin_no_plugin(tempdir, plugin_manager):
    plugin_src = """
from edp.plugin import BasePlugin

class TestPlugin:
    pass
    """

    (tempdir / 'test-plugin.py').write_text(plugin_src)

    plugin_manager.load_plugin(tempdir / 'test-plugin.py')

    assert len(plugin_manager._plugins) == 0


def test_load_plugin_bad_plugin(tempdir, plugin_manager):
    plugin_src = """
raise ValueError()
    """

    (tempdir / 'test-plugin.py').write_text(plugin_src)

    plugin_manager.load_plugin(tempdir / 'test-plugin.py')

    assert len(plugin_manager._plugins) == 0


def test_load_plugins(tempdir, plugin_manager):
    plugin_src = """
from edp.plugin import BasePlugin

class TestPlugin(BasePlugin):
    pass
    """

    (tempdir / 'test-plugin.py').write_text(plugin_src)

    plugin_manager.load_plugins()

    assert len(plugin_manager._plugins)


def test_load_plugin_with_callback(tempdir, plugin_manager):
    plugin_src = """
from edp.plugin import BasePlugin, callback

class TestPlugin(BasePlugin):
    mock = None

    @callback('test signal')
    def foo(self, data):
        return self.mock(data)
    """

    (tempdir / 'test_plugin.py').write_text(plugin_src)

    callback_mock = mock.MagicMock()

    plugin_manager.load_plugin(tempdir / 'test_plugin.py')
    list(plugin_manager._plugins.items())[0][1].mock = callback_mock

    plugin_manager.emit('test signal', data={'foo': 'bar'})

    assert plugin_manager._signal_queue.qsize() == 1
    signal_item: plugin.SignalItem = plugin_manager._signal_queue.get_nowait()

    assert signal_item.name == 'test signal'
    assert signal_item.kwargs == {'data': {'foo': 'bar'}}
    assert len(signal_item.callbacks) == 1

    signal_item.execute()

    callback_mock.assert_called_once_with({'foo': 'bar'})


def test_load_plugin_with_sheduled_callback(tempdir, plugin_manager):
    plugin_src = """
from edp.plugin import BasePlugin, scheduled

class TestPlugin(BasePlugin):
    @scheduled(1)
    def foo(self):
        return str(data)
    """

    (tempdir / 'test_plugin.py').write_text(plugin_src)

    plugin_manager.load_plugin(tempdir / 'test_plugin.py')

    assert len(plugin_manager._scheduler_threads) == 1


def test_plugin_disabled(tempdir, plugin_manager):
    plugin_src = """
from edp.plugin import BasePlugin, callback

class TestPlugin(BasePlugin):
    mock = None
    
    @property
    def enabled(self) -> bool:
        return False
    
    @callback('test signal')
    def foo(self, data):
        return self.mock(data)
    """

    (tempdir / 'test_plugin.py').write_text(plugin_src)

    callback_mock = mock.MagicMock()

    plugin_manager.load_plugin(tempdir / 'test_plugin.py')
    plugin_obj = list(plugin_manager._plugins.items())[0][1]
    plugin_obj.mock = callback_mock

    plugin_manager.emit('test signal', data={'foo': 'bar'})

    assert plugin_manager._signal_queue.qsize() == 1
    signal_item: plugin.SignalItem = plugin_manager._signal_queue.get_nowait()

    assert signal_item.name == 'test signal'
    assert signal_item.kwargs == {'data': {'foo': 'bar'}}
    assert len(signal_item.callbacks) == 1

    signal_item.execute()

    callback_mock.assert_not_called()


def test_plugin_with_injection(tempdir, plugin_manager):
    plugin_src = """
from edp.plugin import BasePlugin, callback
from unittest import mock
import inject

class TestPlugin(BasePlugin):
    _mock = inject.attr(mock.MagicMock)

    @callback('test signal')
    def foo(self, data):
        return self._mock(data)
    """

    (tempdir / 'test_plugin.py').write_text(plugin_src)

    callback_mock = mock.MagicMock()

    def config(binder: inject.Binder):
        binder.bind(mock.MagicMock, callback_mock)

    inject.clear_and_configure(config)

    plugin_manager.load_plugin(tempdir / 'test_plugin.py')
    plugin_manager.emit('test signal', data={'foo': 'bar'})

    assert plugin_manager._signal_queue.qsize() == 1
    signal_item: plugin.SignalItem = plugin_manager._signal_queue.get_nowait()

    assert signal_item.name == 'test signal'
    assert signal_item.kwargs == {'data': {'foo': 'bar'}}
    assert len(signal_item.callbacks) == 1

    signal_item.execute()

    callback_mock.assert_called_once_with({'foo': 'bar'})
