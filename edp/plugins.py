"""
Implementation of EDP's plugin system
"""
import functools
import importlib.util
import inspect
import logging
from pathlib import Path
from types import ModuleType
from typing import Iterator, Type, List, Dict, Optional, NamedTuple, Tuple, Iterable, Callable, Union

from PyQt5 import QtWidgets

from edp import signalslib
from edp.thread import IntervalRunnerThread

logger = logging.getLogger(__name__)


class MARKS:
    """
    Available function mark names
    """
    SCHEDULED = 'scheduled'
    SIGNAL = 'signal'


class FunctionMark(NamedTuple):
    """
    Container for function mark data
    """
    name: str
    options: dict


def mark_function(name: str, **options):
    """
    Mark given function with mark name and some options.

    This information will be available to :py:func:get_marked_methods
    """

    def decor(func):
        if not hasattr(func, '__edp_plugin_mark__'):
            func.__edp_plugin_mark__ = []
        func.__edp_plugin_mark__.append(FunctionMark(name, options))
        return func

    return decor


def get_marked_methods(mark: str, obj) -> Iterator[Tuple[Callable, FunctionMark]]:
    """
    Return object methods that was marked
    """
    for name, t, _, _ in inspect.classify_class_attrs(type(obj)):
        if not name.startswith('__') and t == 'method':
            method: Callable = getattr(obj, name)
            marks = get_function_marks(method)
            for func_mark in marks:
                if func_mark.name == mark:
                    yield method, func_mark


def get_function_marks(func: Callable) -> List[FunctionMark]:
    """Return marks on given function"""
    return getattr(func, '__edp_plugin_mark__', [])


def scheduled(interval: Union[float, int] = 1, plugin_enabled=True):
    """
    Decorator to mark wrapped function as scheduled.

    After plugin registration, a special routine will be called that will create :py:class:IntervalRunnerThread
    for every marked function. This function then will be executed in background thread every `interval` seconds.

    :param interval: Seconds to wait between function execution
    :param plugin_enabled: Execute function only if plugin enabled (is_enabled method returns True)
    """
    if interval <= 0:
        raise ValueError(f'interval must be greater than zero: {interval}')
    return mark_function(MARKS.SCHEDULED, interval=interval, plugin_enabled=plugin_enabled)


def bind_signal(*signals: signalslib.Signal, plugin_enabled=True):
    """
    Decorator to mark wrapped function as binded

    After plugin registration, a special routine will be called that will bind all specified signals to this function.

    :param signals: List of signals to bind this function to
    :param plugin_enabled: Execute function only if plugin enabled (is_enabled method returns True)
    """
    if not signals:
        raise ValueError('At least one signal must be specified')
    return mark_function(MARKS.SIGNAL, signals=signals, plugin_enabled=plugin_enabled)


class BasePlugin:
    """
    Base plugin class that all other plugins should subclass.
    """
    name: Optional[str] = None
    friendly_name: Optional[str] = None
    github_link: Optional[str] = None

    def is_enalbed(self) -> bool:  # pylint: disable=no-self-use
        """
        Return True if this plugin enabled.

        Checked when firing bind signals and scheduled functions
        """
        return True

    def get_settings_widget(self) -> Optional[QtWidgets.QWidget]:
        """
        Return widget that will be shown in settings window
        """
        raise NotImplementedError


def get_module_from_path(path: Path) -> ModuleType:
    """
    Import and return python module
    """
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    module = importlib.util.module_from_spec(spec)
    if spec.loader:
        spec.loader.exec_module(module)  # type: ignore
    else:
        raise TypeError('Cant execute module')
    return module


def _get_plugin_classes_from_module(module: ModuleType) -> Iterator[Type[BasePlugin]]:
    """
    Iterate over all BasePlugin implementations in module
    """
    for attr in dir(module):
        value = getattr(module, attr)
        if isinstance(value, type) and issubclass(value, BasePlugin) and value != BasePlugin:
            yield value


def get_plugins_cls_from_dir(path: Path) -> Iterator[Type[BasePlugin]]:
    """
    Iterate over all BasePlugin implementations in all modules and files in directory
    """
    if not path.is_dir():
        raise NotADirectoryError(f'Is not a directory: {path}')

    for p in path.iterdir():
        try:
            yield from get_plugins_cls_from_path(p)
        except:
            logger.exception(f'Error getting plugin from path: {p}')


def get_plugins_cls_from_path(path: Path) -> Iterator[Type[BasePlugin]]:
    """
    Iterate over all BasePlugin implementations in given path
    """
    if not path.exists():
        raise FileNotFoundError(str(path))

    if path.is_file() and path.suffix == '.py':
        logger.debug(f'Loading plugin from file {path}')
        yield from get_plugins_cls_from_file(path)

    elif path.is_dir() and is_plugin_package(path):
        logger.debug(f'Loading plugin from package {path}')
        yield from get_plugins_cls_from_package(path)


def is_plugin_package(path: Path) -> bool:  # pylint: disable=unused-argument
    """
    Check if given path is a plugin package
    """
    return False  # path.is_dir() and (path / 'edp_plugin.py').exists()


def get_plugins_cls_from_file(path: Path) -> Iterator[Type[BasePlugin]]:
    """Iterate over all BasePlugin implementations in file"""
    if not path.exists():
        raise FileNotFoundError(path)

    try:
        module = get_module_from_path(path)
    except:
        logger.exception(f'Error imporing plugin module from: {path}')
        return

    yield from _get_plugin_classes_from_module(module)


def get_plugins_cls_from_package(path: Path) -> Iterator[Type[BasePlugin]]:
    """Iterate over all BasePlugin implementations in plugin package"""
    raise NotImplementedError


class MarkedMethodType(NamedTuple):
    """Container for plugin method mark information"""
    plugin: BasePlugin
    method: Callable
    mark: FunctionMark


class PluginManager:
    """
    Internal class that contains various routines operating with plugins, e.g. binding signals, creating threads.

    This considered a private api and is not available through injection.
    """

    def __init__(self, plugins: List[BasePlugin]):
        self._plugins = plugins
        self._plugins_cls_map: Dict[Type[BasePlugin], BasePlugin] = {type(p): p for p in plugins}

    def get_plugin(self, plugin_cls: Type[BasePlugin]) -> Optional[BasePlugin]:
        """
        If found return plugin instance of given type
        """
        return self._plugins_cls_map.get(plugin_cls, None)

    def get_marked_methods(self, name: str) -> Iterator[MarkedMethodType]:
        """
        Iterate over all methods of all plugins that marked with given mark name
        """
        for plugin in self._plugins:
            try:
                yield from (MarkedMethodType(plugin, method, mark) for method, mark in get_marked_methods(name, plugin))
            except:
                logger.exception(f'Failed to get plugin marked methods: {plugin}')

    def get_scheduled_methods_threads(self) -> Iterator[IntervalRunnerThread]:
        """
        Iterate over threads created to run plugin methods marked as scheduled.
        """
        for marked_method in self.get_marked_methods(MARKS.SCHEDULED):
            plugin_enabled: bool = marked_method.mark.options['plugin_enabled']
            interval: int = marked_method.mark.options.get('interval', 1)

            callback = self._callback_wrapper(marked_method.method, marked_method.plugin, plugin_enabled)
            yield IntervalRunnerThread(callback, interval=interval)

    def set_plugin_annotation_references(self):
        """
        If plugin class has annotation of type of registered plugin, set this attribute to that plugin instance
        """
        for plugin in self._plugins:
            for key, cls in getattr(plugin, '__annotations__', {}).items():
                if isinstance(cls, type) and issubclass(cls, BasePlugin) and cls in self._plugins_cls_map:
                    setattr(plugin, key, self._plugins_cls_map[cls])

    # pylint: disable=no-self-use
    def _callback_wrapper(self, func: Callable, plugin: BasePlugin, plugin_enabled: bool):
        @functools.wraps(func)
        def callback(**kwargs):
            if plugin_enabled and not plugin.is_enalbed():
                return None
            return func(**kwargs)

        return callback

    def register_plugin_signals(self):
        """
        Bind marked plugin methods to signals
        """
        for marked_method in self.get_marked_methods(MARKS.SIGNAL):
            signals: Iterable[signalslib.Signal] = marked_method.mark.options['signals']
            plugin_enabled: bool = marked_method.mark.options['plugin_enabled']

            for signal in signals:
                try:
                    callback = self._callback_wrapper(marked_method.method, marked_method.plugin, plugin_enabled)
                    signal.bind(callback)
                except:
                    logger.exception(f'Failed to bind plugin signal "{signal.name}" {marked_method.method}')

    def get_settings_widgets(self) -> Iterator[QtWidgets.QWidget]:
        """
        Iterate over plugins settings widgets
        """
        for plugin in self._plugins:
            try:
                widget = plugin.get_settings_widget()
                if widget is not None:
                    yield widget
            except NotImplementedError:
                pass
            except:
                logger.exception(f'Failed to get settings widget from {plugin}')


class PluginProxy:
    """
    Public class available through injection, allows to get other plugin instance by its type.
    """

    def __init__(self, plugin_manager: PluginManager):
        self._plugin_manager = plugin_manager

    def get_plugin(self, plugin_cls: Type[BasePlugin]) -> Optional[BasePlugin]:
        """If found return plugin instance of given type"""
        return self._plugin_manager.get_plugin(plugin_cls)


class PluginLoader:
    """
    Used to load and initialize plugins. Feeds results to PluginManager.

    Inernal.
    """

    def __init__(self, plugin_dir: Path):
        self._plugin_dir = plugin_dir
        self._plugin_list: List[BasePlugin] = []

    def get_plugins(self) -> List[BasePlugin]:
        """Return list of loaded plugins"""
        return self._plugin_list

    def add_plugin(self, plugin_cls: Type[BasePlugin]):
        """
        Register and initialise plugin with given type
        """
        try:
            plugin = self._init_plugin_cls(plugin_cls)
        except:
            logger.exception(f'Failed to initialize plugin: {plugin_cls}')
            return
        self._plugin_list.append(plugin)
        logger.debug(f'Registered plugin {plugin.__module__}.{plugin.__class__.__name__}')

    def load_plugins(self):
        """
        Load plugins from plugin directory
        """
        try:
            for plugin_cls in get_plugins_cls_from_dir(self._plugin_dir):
                logger.debug(f'Loaded plugin {plugin_cls} from {plugin_cls.__module__}')
                self.add_plugin(plugin_cls)
        except:
            logger.exception('Failed to load any plugin')

    # pylint: disable=no-self-use
    def _init_plugin_cls(self, plugin_cls: Type[BasePlugin]) -> BasePlugin:
        return plugin_cls()
