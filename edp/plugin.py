import abc
import importlib.util
import logging
import pathlib
from typing import List, Type, Iterator

logger = logging.getLogger(__name__)


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
                except:
                    logger.exception('Failed to initialize plugin %s from %s', cls, path)

    def _is_module_plugin(self, path: pathlib.Path):
        raise NotImplementedError

    def _load_module_plugin(self, path: pathlib.Path):
        raise NotImplementedError

    def _init_plugin(self, cls: Type[BasePlugin]) -> BasePlugin:
        return cls()
