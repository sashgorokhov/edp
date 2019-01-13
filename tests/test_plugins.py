from edp import plugins

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


def get_plugins_cls_from_path(tempdir):
    (tempdir / 'plugin.py').write_text(SIMPLE_TEST_PLUGIN_MODULE)

    classes = list(plugins.get_plugins_cls_from_path(tempdir / 'plugin.py'))
    assert len(classes) == 1
    assert classes[0].__name__ == 'TestPlugin'


def test_get_plugins_cls_from_file(tempdir):
    (tempdir / 'plugin.py').write_text(SIMPLE_TEST_PLUGIN_MODULE)

    classes = list(plugins.get_plugins_cls_from_file(tempdir / 'plugin.py'))
    assert len(classes) == 1
    assert classes[0].__name__ == 'TestPlugin'


def test_plugin_loader_load_plugins(tempdir):
    (tempdir / 'plugin.py').write_text(SIMPLE_TEST_PLUGIN_MODULE)

    plugin_loader = plugins.PluginLoader(tempdir)
    plugin_loader.load_plugins()

    plugins_list = plugin_loader.get_plugins()

    assert len(plugins_list) == 1
    assert isinstance(plugins_list[0], plugins.BasePlugin)
    assert plugins_list[0].__class__.__name__ == 'TestPlugin'
