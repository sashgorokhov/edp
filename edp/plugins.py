import importlib.util
import logging
from pathlib import Path
from types import ModuleType
from typing import Iterator, Type, List, TypeVar, Dict, Optional

logger = logging.getLogger(__name__)


class BasePlugin:
    name: str = None
    friendly_name: str = None
    github_link: str = None

    def is_enabled(self) -> bool:
        return True


def get_module_from_path(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

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


T = TypeVar('T')


class PluginManager:
    # internal during app lifetime, passed as init param
    def __init__(self, plugins: List[BasePlugin]):
        self._plugins = plugins
        self._plugin_cls_map: Dict[Type[BasePlugin], BasePlugin] = {p.__class__: p for p in plugins}

    def get_plugin(self, plugin_cls: Type[T]) -> Optional[T]:
        return self._plugin_cls_map.get(plugin_cls, None)


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
        plugin = self._init_plugin_cls(plugin_cls)
        self._plugin_list.append(plugin)
        logger.debug(f'Registered plugin {plugin.__module__}.{plugin.__class__.__name__}')

    def load_plugins(self):
        for plugin_cls in get_plugins_cls_from_dir(self._plugin_dir):
            try:
                self.add_plugin(plugin_cls)
            except:
                logger.exception(f'Failed to init plugin: {plugin_cls}')

    def _init_plugin_cls(self, plugin_cls: Type[BasePlugin]) -> BasePlugin:
        return plugin_cls()
