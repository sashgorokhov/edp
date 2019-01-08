import abc
import collections
import importlib.util
import logging
import pathlib
import inspect
from typing import List, Type, Iterator, Mapping, Callable, Any

logger = logging.getLogger(__name__)


def callback(name=None):
    def decor(func):
        nonlocal name
        name = name or func.__name__
        func.__is_callback__ = name
        return func
    return decor


class BasePlugin(metaclass=abc.ABCMeta):
    pass


def _get_plugin_cls(module) -> Iterator[Type[BasePlugin]]:
    for attr in dir(module):
        value = getattr(module, attr)
        if isinstance(value, type) and issubclass(value, BasePlugin) and value != BasePlugin:
            yield value


class PluginManager:
    def __init__(self, base_dir: pathlib.Path):
        self._base_dir = base_dir
        self._plugins: List[BasePlugin] = []
        self._callbacks: Mapping[str, List[Callable]] = collections.defaultdict(list)

    def load_plugins(self):
        for path in self._base_dir.iterdir():
            try:
                self.load_plugin(path)
            except:
                logger.exception('Failed to load plugin from %s', path)

    def load_plugin(self, path: pathlib.Path):
        if path.is_file() and path.name.endswith('.py'):
            logger.info('Loading file plugin from %s', path)
            self._load_file_plugin(path)
        elif path.is_dir() and self._is_module_plugin(path):
            logger.info('Loading module plugin from %s', path)
            self._load_module_plugin(path)

    def _load_file_plugin(self, path: pathlib.Path):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for cls in _get_plugin_cls(module):
            if cls not in self._plugins:
                try:
                    plugin = self._init_plugin(cls)
                    self._plugins.append(plugin)
                    self._register_callbacks(plugin)
                except:
                    logger.exception('Failed to initialize plugin %s from %s', cls, path)

    def _is_module_plugin(self, path: pathlib.Path):
        raise NotImplementedError

    def _load_module_plugin(self, path: pathlib.Path):
        raise NotImplementedError

    def _init_plugin(self, cls: Type[BasePlugin]) -> BasePlugin:
        return cls()

    def _register_callbacks(self, plugin: BasePlugin):
        for name, t, cls, value in inspect.classify_class_attrs(plugin.__class__):
            if t != 'method' or not hasattr(value, '__is_callback__'):
                continue
            callback_name = getattr(value, '__is_callback__')
            self._callbacks[callback_name].append(value.__get__(plugin, cls))
            logger.debug('Registered callback "%s" of %s', callback_name, plugin)

    def emit(self, name, **kwargs) -> List[Any]:
        logger.debug('Emitting signal: %s', name)
        results = []

        for func in self._callbacks.get(name, []):
            try:
                results.append(func(**kwargs))
            except:
                logger.exception('Error executing callback "%s" %s', name, func)

        return results
