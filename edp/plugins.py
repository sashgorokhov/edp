import importlib.util
import inspect
import logging
from pathlib import Path
from types import ModuleType, FunctionType
from typing import Iterator, Type, List, TypeVar, Dict, Optional, NamedTuple, Tuple, Any

from edp.thread import IntervalRunnerThread

logger = logging.getLogger(__name__)


class MARKS:
    SCHEDULED = 'scheduled'


class FunctionMark(NamedTuple):
    name: str
    options: dict


def mark_function(name: str, **options):
    def decor(func):
        if not hasattr(func, '__edp_plugin_mark__'):
            func.__edp_plugin_mark__ = []
        func.__edp_plugin_mark__.append(FunctionMark(name, options))
        return func

    return decor


def get_marked_methods(mark: str, obj) -> Iterator[Tuple[FunctionType, FunctionMark]]:
    for name, t, _, _ in inspect.classify_class_attrs(type(obj)):
        if not name.startswith('__') and t == 'method':
            method: FunctionType = getattr(obj, name)
            marks = get_function_marks(method)
            for func_mark in marks:
                if func_mark.name == mark:
                    yield method, func_mark


def get_function_marks(func: FunctionType) -> List[FunctionMark]:
    return getattr(func, '__edp_plugin_mark__', [])


def scheduled(interval=1):
    return mark_function(MARKS.SCHEDULED, interval=interval)


class BasePlugin:
    name: Optional[str] = None
    friendly_name: Optional[str] = None
    github_link: Optional[str] = None


def get_module_from_path(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    module = importlib.util.module_from_spec(spec)
    if spec.loader:
        spec.loader.exec_module(module)
    else:
        raise TypeError('Cant execute module')
    return module


def _get_plugin_classes_from_module(module: ModuleType) -> Iterator[Type[BasePlugin]]:
    for attr in dir(module):
        value = getattr(module, attr)
        if isinstance(value, type) and issubclass(value, BasePlugin) and value != BasePlugin:
            yield value


def get_plugins_cls_from_dir(dir: Path) -> Iterator[Type[BasePlugin]]:
    if not dir.is_dir():
        raise TypeError(f'Is not a directory: {dir}')

    for path in dir.iterdir():
        try:
            yield from get_plugins_cls_from_path(path)
        except:
            logger.exception(f'Error getting plugin from path: {path}')


def get_plugins_cls_from_path(path: Path) -> Iterator[Type[BasePlugin]]:
    if not path.exists():
        raise FileNotFoundError(str(path))

    if path.is_file() and path.suffix == '.py':
        logger.debug(f'Loading plugin from file {path}')
        yield from get_plugins_cls_from_file(path)

    elif path.is_dir() and is_plugin_package(path):
        logger.debug(f'Loading plugin from package {path}')
        yield from get_plugins_cls_from_package(path)


def is_plugin_package(path: Path) -> bool:
    return False  # path.is_dir() and (path / 'edp_plugin.py').exists()


def get_plugins_cls_from_file(path: Path) -> Iterator[Type[BasePlugin]]:
    if not path.exists():
        raise FileNotFoundError(path)

    try:
        module = get_module_from_path(path)
    except:
        logger.exception(f'Error imporing plugin module from: {path}')
        return

    yield from _get_plugin_classes_from_module(module)


def get_plugins_cls_from_package(path: Path) -> Iterator[Type[BasePlugin]]:
    pass


T = TypeVar('T', BasePlugin, Any)


class PluginManager:
    # internal during app lifetime, passed as init param
    def __init__(self, plugins: List[BasePlugin]):
        self._plugins = plugins
        self._plugin_cls_map: Dict[Type[BasePlugin], BasePlugin] = {type(p): p for p in plugins}

    def get_plugin(self, plugin_cls: Type[T]) -> Optional[T]:
        return self._plugin_cls_map.get(plugin_cls, None)

    def get_marked_methods(self, name: str) -> Iterator[Tuple[FunctionType, FunctionMark]]:
        for plugin in self._plugins:
            yield from get_marked_methods(name, plugin)

    def get_scheduled_methods_threads(self) -> Iterator[IntervalRunnerThread]:
        for method, mark in self.get_marked_methods(MARKS.SCHEDULED):
            yield IntervalRunnerThread(method, interval=mark.options.get('interval', 1))


class PluginProxy:
    # public to plugins, injection
    def __init__(self, plugin_manager: PluginManager):
        self._plugin_manager = plugin_manager

    def get_plugin(self, plugin_cls: Type[T]) -> Optional[T]:
        return self._plugin_manager.get_plugin(plugin_cls)


class PluginLoader:
    # internal short lifetime, manually created
    # holds logic how to create plugins,
    # will require possible shared configuration state

    def __init__(self, plugin_dir: Path):
        self._plugin_dir = plugin_dir
        self._plugin_list: List[BasePlugin] = []

    def get_plugins(self) -> List[BasePlugin]:  # list preserves load and init order
        return self._plugin_list

    def add_plugin(self, plugin_cls: Type[BasePlugin]):
        try:
            plugin = self._init_plugin_cls(plugin_cls)
        except:
            logger.exception(f'Failed to initialize plugin: {plugin_cls}')
        self._plugin_list.append(plugin)
        logger.debug(f'Registered plugin {plugin.__module__}.{plugin.__class__.__name__}')

    def load_plugins(self):
        for plugin_cls in get_plugins_cls_from_dir(self._plugin_dir):
            logger.debug(f'Loaded plugin {plugin_cls} from {plugin_cls.__module__}')
            try:
                self.add_plugin(plugin_cls)
            except:
                logger.exception(f'Failed to init plugin: {plugin_cls}')

    def _init_plugin_cls(self, plugin_cls: Type[BasePlugin]) -> BasePlugin:
        return plugin_cls()
