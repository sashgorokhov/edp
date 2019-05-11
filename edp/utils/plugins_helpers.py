"""Various helpers for plugin development"""
import logging
import threading
from typing import List, Dict, Generic, TypeVar, Callable, Iterator, Optional

from edp import journal, plugins, signals

logger = logging.getLogger(__name__)


class BufferedEventsMixin:
    """
    Buffers journal events and processes them every minute
    """
    def __init__(self, *args, **kwargs):
        super(BufferedEventsMixin, self).__init__(*args, **kwargs)

        self._events_buffer: List[journal.Event] = []
        self._events_buffer_lock = threading.Lock()

    # pylint: disable=unused-argument,no-self-use
    def filter_event(self, event: journal.Event) -> bool:
        """
        Put event into buffer if this returns True

        Can be overriden by subclass to adjust its behavior.
        """
        return True

    @plugins.bind_signal(journal.journal_event_signal)
    def on_journal_event(self, event: journal.Event):
        """
        Called on every journal event.

        Event is put into buffer if filter_event returns True.
        """
        if not self.filter_event(event):
            return
        with self._events_buffer_lock:
            self._events_buffer.append(event)

    @plugins.scheduled(60)
    def buffer_flush_callback(self):
        """
        Flush buffer and process all buffered events
        """
        if not self._events_buffer:
            return

        with self._events_buffer_lock:
            events = self._events_buffer.copy()
            self._events_buffer.clear()

        self.process_buffered_events(events)

    def process_buffered_events(self, events: List[journal.Event]):
        """
        Process buffered events.

        Should be overriden by subclass.
        """
        raise NotImplementedError

    @plugins.bind_signal(signals.exiting)
    def exit_callback(self):
        """
        Flush buffer on application exit
        """
        self.buffer_flush_callback()


CT = TypeVar('CT', bound=Callable)  # Callback Type
RT = TypeVar('RT')


class RoutingSwitchRegistry(Generic[CT, RT]):
    """
    Allows callback registration on routing keys.

    Think of it as routing key could be a url, and callback a web server url handler.
    But here you can have several callbacks registered on one routing key.

    This used by EDPs core and Inara plugin to call required functions on different event types.

    It also subclasses typing.Generic so it can be typed:

        registry: RoutingSwitchRegistry[Callable[[Event], str], str] = ...

    Where `CT` is callback type, and `RT` callback return value type.
    """
    def __init__(self):
        self._callbacks: Dict[str, List[Callable]] = {}

    def register(self, *routing_keys: str, callbacks: Optional[List[CT]] = None):
        """
        Register callback on given routing keys.

        You can register multiple callbacks on multiple routing keys.

        If callbacks param is set, this will register these callbacks to given routing keys.
        If callbacks param is not set, this will act as a decorator and register decorated function on routing keys.
        """
        def decor(func: CT):
            for key in routing_keys:
                if key in self._callbacks:
                    self._callbacks[key].append(func)
                else:
                    self._callbacks[key] = [func]
            return func

        if callbacks is not None:
            for callback in callbacks:
                decor(callback)
            return None

        return decor

    def execute(self, routing_key: str, **kwargs) -> Iterator[RT]:
        """
        Execute callbacks registered on routing key with given parameters.

        :raises KeyError: If callbacks for routing_key are not registered
        :returns: Iterator over callback results
        """
        if routing_key not in self._callbacks:
            raise KeyError(f'Callback for key {routing_key} not registered')
        for callback in self._callbacks[routing_key]:
            try:
                yield callback(**kwargs)
            except:
                logger.exception(f'Error executing callback for key {routing_key}: {callback}: {kwargs}')

    def execute_silently(self, routing_key: str, **kwargs) -> Iterator[RT]:
        """
        Execute callbacks registered on routing key with given parameters.

        Do nothing if callbacks for routing_key are not registered.

        :returns: Iterator over callback results
        """
        try:
            yield from self.execute(routing_key, **kwargs)
        except KeyError:
            yield from []
