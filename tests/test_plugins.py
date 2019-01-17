from unittest import mock

import pytest

from edp import plugins, signalslib

SIMPLE_TEST_PLUGIN_MODULE = """
from edp.plugins import BasePlugin

class TestPlugin(BasePlugin): pass    
"""


def test_mark_function():
    def foo(): pass

    plugins.mark_function('test')(foo)

    marks = plugins.get_function_marks(foo)

    assert len(marks) == 1
    assert marks[0].name == 'test'
    assert marks[0].options == {}


def test_mark_function_options():
    def foo(): pass

    plugins.mark_function('test', test='foo')(foo)

    marks = plugins.get_function_marks(foo)

    assert len(marks) == 1
    assert marks[0].name == 'test'
    assert marks[0].options == {'test': 'foo'}


def test_mark_function_of_class():
    class Foo:
        @plugins.mark_function('test')
        def foo(self): pass

    marks = plugins.get_function_marks(Foo.foo)

    assert len(marks) == 1
    assert marks[0].name == 'test'
    assert marks[0].options == {}


def test_get_marked_methods():
    class Foo:
        @plugins.mark_function('test')
        def foo(self):
            pass

    f = Foo()

    method_marks = list(plugins.get_marked_methods('test', f))

    assert len(method_marks) == 1
    assert method_marks[0][0] == f.foo
    assert method_marks[0][1].name == 'test'


def test_get_module_from_path(tempdir):
    module_path = tempdir / 'test_module.py'
    module_path.write_text('test = "hello!"')

    module = plugins.get_module_from_path(module_path)
    assert hasattr(module, 'test')
    assert module.test == 'hello!'


def test_get_plugin_classes_from_module(tempdir):
    module_path = tempdir / 'test_module.py'
    module_path.write_text(SIMPLE_TEST_PLUGIN_MODULE)

    module = plugins.get_module_from_path(module_path)
    classes = list(plugins._get_plugin_classes_from_module(module))

    assert len(classes) == 1
    assert classes[0].__name__ == 'TestPlugin'


def test_get_plugins_cls_from_dir(tempdir):
    (tempdir / 'plugin.py').write_text(SIMPLE_TEST_PLUGIN_MODULE)

    classes = list(plugins.get_plugins_cls_from_dir(tempdir))
    assert len(classes) == 1
    assert classes[0].__name__ == 'TestPlugin'


def test_get_plugins_cls_from_dir_nonexistent(tempdir):
    with pytest.raises(NotADirectoryError):
        list(plugins.get_plugins_cls_from_dir(tempdir / 'bar'))


def test_get_plugins_cls_from_path(tempdir):
    (tempdir / 'plugin.py').write_text(SIMPLE_TEST_PLUGIN_MODULE)

    classes = list(plugins.get_plugins_cls_from_path(tempdir / 'plugin.py'))
    assert len(classes) == 1
    assert classes[0].__name__ == 'TestPlugin'


def test_get_plugins_cls_from_path_nonexistent(tempdir):
    with pytest.raises(FileNotFoundError):
        list(plugins.get_plugins_cls_from_path(tempdir / 'plugin.py'))


def test_get_plugins_cls_from_file(tempdir):
    (tempdir / 'plugin.py').write_text(SIMPLE_TEST_PLUGIN_MODULE)

    classes = list(plugins.get_plugins_cls_from_file(tempdir / 'plugin.py'))
    assert len(classes) == 1
    assert classes[0].__name__ == 'TestPlugin'


def test_get_plugins_cls_from_file_nonexistent(tempdir):
    with pytest.raises(FileNotFoundError):
        list(plugins.get_plugins_cls_from_file(tempdir / 'plugin.py'))


def test_plugin_loader_load_plugins(tempdir):
    (tempdir / 'plugin.py').write_text(SIMPLE_TEST_PLUGIN_MODULE)

    plugin_loader = plugins.PluginLoader(tempdir)
    plugin_loader.load_plugins()

    plugins_list = plugin_loader.get_plugins()

    assert len(plugins_list) == 1
    assert isinstance(plugins_list[0], plugins.BasePlugin)
    assert plugins_list[0].__class__.__name__ == 'TestPlugin'


@pytest.mark.parametrize('plugin_enabled', [True, False])
@pytest.mark.parametrize('interval', [1, 2, 5])
def test_scheduled_decorator(plugin_enabled, interval):
    @plugins.scheduled(interval, plugin_enabled=plugin_enabled)
    def foo(): pass

    marks = plugins.get_function_marks(foo)
    assert len(marks) == 1
    assert marks[0].name == plugins.MARKS.SCHEDULED
    assert marks[0].options['plugin_enabled'] == plugin_enabled
    assert marks[0].options['interval'] == interval


@pytest.mark.parametrize('interval', [-1, 0])
def test_scheduled_decorator_bad_interval(interval):
    with pytest.raises(ValueError):
        @plugins.scheduled(interval)
        def foo(): pass


def test_bind_signal_decorator():
    signal = signalslib.Signal('test')

    @plugins.bind_signal(signal)
    def foo(): pass

    marks = plugins.get_function_marks(foo)
    assert len(marks) == 1
    assert marks[0].name == plugins.MARKS.SIGNAL
    assert marks[0].options['signals'] == (signal,)


def test_bind_signal_decorator_no_signals():
    with pytest.raises(ValueError):
        @plugins.bind_signal()
        def foo(): pass


@pytest.mark.parametrize(('plugin', 'plugins_list', 'result'), [
    (type('foo'), [], None),
    (type('foo'), [type('foo')()], type('foo')()),  # i just dont know why it works???
    (type('foo'), [type('foo')(), type('foo')()], type('foo')()),
])
def test_plugin_manager_get_plugin(plugin, plugins_list, result):
    plugin_manager = plugins.PluginManager(plugins_list)
    assert plugin_manager.get_plugin(plugin) == result


def test_plugin_manager_get_marked_methods():
    class SomePlugin(plugins.BasePlugin):
        @plugins.mark_function('test')
        def test_method(self): pass

    plugin = SomePlugin()

    plugin_manager = plugins.PluginManager([plugin])

    marked_methods = list(plugin_manager.get_marked_methods('test'))
    assert len(marked_methods) == 1
    assert isinstance(marked_methods[0], plugins.MarkedMethodType)
    assert marked_methods[0].plugin == plugin
    assert marked_methods[0].method == plugin.test_method
    assert marked_methods[0].mark.name == 'test'


def test_get_scheduled_methods_threads():
    class SomePlugin(plugins.BasePlugin):
        @plugins.scheduled(0.4)
        def test_method(self): pass

    plugin = SomePlugin()
    plugin_manager = plugins.PluginManager([plugin])

    interval_threads = list(plugin_manager.get_scheduled_methods_threads())
    assert len(interval_threads) == 1
    assert interval_threads[0]._interval == 0.4


def test_set_plugin_annotation_references():
    class SomePlugin(plugins.BasePlugin): pass

    class OtherPlugin(plugins.BasePlugin):
        ref: SomePlugin

    some_plugin = SomePlugin()
    other_plugin = OtherPlugin()
    plugin_manager = plugins.PluginManager([some_plugin, other_plugin])

    assert not hasattr(other_plugin, 'ref')
    plugin_manager.set_plugin_annotation_references()
    assert hasattr(other_plugin, 'ref')

    assert other_plugin.ref == some_plugin


def test_get_settings_widgets():
    plugin1 = mock.MagicMock(spec=plugins.BasePlugin)
    plugin1.get_settings_widget.side_effect = NotImplementedError
    plugin2 = mock.MagicMock(spec=plugins.BasePlugin)
    plugin2.get_settings_widget.return_value = 'test'
    plugin3 = mock.MagicMock(spec=plugins.BasePlugin)
    plugin3.get_settings_widget.side_effect = ValueError

    plugin_manager = plugins.PluginManager([plugin1, plugin3, plugin2])
    settings_widgets = list(plugin_manager.get_settings_widgets())

    plugin1.get_settings_widget.assert_called_once()
    plugin2.get_settings_widget.assert_called_once()
    plugin3.get_settings_widget.assert_called_once()

    assert len(settings_widgets) == 1
    assert settings_widgets[0] == 'test'


def test_register_plugin_signals():
    signal = signalslib.Signal('test')

    class Plugin1(plugins.BasePlugin):
        @plugins.bind_signal(signal)
        def method(self): pass

    plugin1 = Plugin1()

    plugin_manager = plugins.PluginManager([plugin1])
    plugin_manager.register_plugin_signals()

    assert len(signal.callbacks) == 1


def test_callback_wrapper_plugin_disabled():
    mock_plugin = mock.MagicMock()
    mock_plugin.is_enalbed.return_value = False
    mock_func = mock.MagicMock()

    plugin_manager = plugins.PluginManager([])

    plugin_manager._callback_wrapper(mock_func, mock_plugin, plugin_enabled=True)(foo='bar')

    mock_func.assert_not_called()


def test_callback_wrapper_plugin_enabled():
    mock_plugin = mock.MagicMock()
    mock_plugin.is_enalbed.return_value = True
    mock_func = mock.MagicMock()

    plugin_manager = plugins.PluginManager([])

    plugin_manager._callback_wrapper(mock_func, mock_plugin, plugin_enabled=True)(foo='bar')

    mock_func.assert_called_once_with(foo='bar')
