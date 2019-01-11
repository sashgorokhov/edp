import abc
import collections
import functools
import importlib.util
import inspect
import logging
import pathlib
import queue
from typing import List, Type, Iterator, Callable, NamedTuple, Dict, TypeVar

from edp.thread import IntervalRunnerThread
from edp.utils import StoppableThread

logger = logging.getLogger(__name__)


def callback(*signals: str):
    def decor(func):
        func.__is_callback__ = signals
        return func

    return decor


def scheduled(interval):
    def decor(func):
        func.__scheduled__ = interval
        return func

    return decor


class BasePlugin(metaclass=abc.ABCMeta):
    @property
    def enabled(self) -> bool:
        return True


def _get_plugin_cls(module) -> Iterator[Type[BasePlugin]]:
    for attr in dir(module):
        value = getattr(module, attr)
        if isinstance(value, type) and issubclass(value, BasePlugin) and value != BasePlugin:
            yield value


def _get_cls_methods(cls: Type) -> Iterator:
    for name, t, _, value in inspect.classify_class_attrs(cls):
        if not name.startswith('__') and t == 'method':
            yield value


def _bind_method(func, obj):
    return func.__get__(obj, obj.__class__)


def enabled_only(plugin: BasePlugin):
    def decor(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if plugin.enabled:
                return func(*args, **kwargs)

        return wrapper

    return decor


class SignalItem(NamedTuple):
    name: str
    callbacks: List[Callable]
    kwargs: dict

    def execute(self):
        for callback in self.callbacks:
            try:
                callback(**self.kwargs)
            except:
                logger.exception('Error calling signal "%s" callback %s', self.name, callback)


class SignalExecutorThread(StoppableThread):
    def __init__(self, signal_queue: queue.Queue):
        self._signal_queue = signal_queue
        super(SignalExecutorThread, self).__init__()

    def run(self):
        while not self.is_stopped:
            try:
                signal_item: SignalItem = self._signal_queue.get(block=True, timeout=1)
            except queue.Empty:
                continue

            signal_item.execute()


T = TypeVar('T')


class PluginManager:
    def __init__(self, base_dir: pathlib.Path):
        self._base_dir = base_dir
        self._plugins: Dict[Type[BasePlugin], BasePlugin] = {}
        self._callbacks: Dict[str, List[Callable]] = collections.defaultdict(list)
        self._scheduler_threads: List[StoppableThread] = []
        self._signal_queue = queue.Queue()

    def load_plugins(self):
        if not self._base_dir.exists():
            logger.warning('Plugin dir does not exist: %s', self._base_dir)
            return

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
        if not path.exists():
            raise FileNotFoundError(str(path))

        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except:
            logger.exception('Error while imporing plugin from %s', path)
            return

        for cls in _get_plugin_cls(module):
            if cls not in self._plugins:
                try:
                    self.register_plugin_cls(cls)
                except:
                    logger.exception('Failed to initialize plugin %s from %s', cls, path)

    def register_plugin_cls(self, cls: Type[BasePlugin]):
        plugin = self._init_plugin(cls)
        self._plugins[cls] = plugin
        self._register_callbacks(plugin)
        self._register_scheduled_funcs(plugin)

    def __getitem__(self, item: Type[T]) -> T:
        if isinstance(item, type) and issubclass(item, BasePlugin):
            return self._plugins[item]
        else:
            raise TypeError(f'Can accept only plugin class')

    def _is_module_plugin(self, path: pathlib.Path):
        raise NotImplementedError

    def _load_module_plugin(self, path: pathlib.Path):
        raise NotImplementedError

    def _init_plugin(self, cls: Type[BasePlugin]) -> BasePlugin:
        return cls()

    def _register_callbacks(self, plugin: BasePlugin):
        for method in _get_cls_methods(plugin.__class__):
            if not hasattr(method, '__is_callback__'):
                continue
            signal_names = getattr(method, '__is_callback__')
            bound_method = _bind_method(method, plugin)
            bound_method = self._decorate_bound_method_callback(plugin, bound_method)
            for signal_name in signal_names:
                self._callbacks[signal_name].append(bound_method)
                logger.debug('Registered callback "%s" of %s: %s', signal_name, plugin, bound_method)

    def _register_scheduled_funcs(self, plugin: BasePlugin):
        for method in _get_cls_methods(plugin.__class__):
            if not hasattr(method, '__scheduled__'):
                continue
            interval = getattr(method, '__scheduled__')
            bound_method = _bind_method(method, plugin)
            bound_method = self._decorate_bound_method_callback(plugin, bound_method)
            thread = IntervalRunnerThread(bound_method, interval=interval)
            self._scheduler_threads.append(thread)
            logger.debug('Registered scheduled func %s to thread %s', bound_method, thread)

    def _decorate_bound_method_callback(self, plugin: BasePlugin, method):
        return enabled_only(plugin)(method)

    def emit(self, name, **kwargs):
        logger.debug('Emitting signal: %s', name)
        callbacks = self._callbacks.get(name, [])
        if callbacks:
            self._signal_queue.put_nowait(SignalItem(name, callbacks, kwargs))
