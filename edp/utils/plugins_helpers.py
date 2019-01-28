import logging
import logging
import threading
from typing import List, Dict, Generic, TypeVar, Callable, Iterator

from edp import journal, plugins

logger = logging.getLogger(__name__)


class BufferedEventsMixin:
    def __init__(self, *args, **kwargs):
        super(BufferedEventsMixin, self).__init__(*args, **kwargs)

        self._events_buffer: List[journal.Event] = []
        self._events_buffer_lock = threading.Lock()

    def filter_event(self, event: journal.Event) -> bool:
        return True

    @plugins.bind_signal(journal.journal_event_signal)
    def on_journal_event(self, event: journal.Event):
        if not self.filter_event(event):
            return
        with self._events_buffer_lock:
            self._events_buffer.append(event)

    @plugins.scheduled(60)
    def buffer_flush_callback(self):
        if not self._events_buffer:
            return

        with self._events_buffer_lock:
            events = self._events_buffer.copy()
            self._events_buffer.clear()

        self.process_buffered_events(events)

    def process_buffered_events(self, events: List[journal.Event]):
        raise NotImplementedError


CT = TypeVar('CT', bound=Callable)  # Callback Type
RT = TypeVar('RT')


class RoutingSwitchRegistry(Generic[CT, RT]):
    def __init__(self):
        self._callbacks: Dict[str, List[Callable]] = {}

    def register(self, *routing_keys: str):
        def decor(func: CT):
            for key in routing_keys:
                if key in self._callbacks:
                    self._callbacks[key].append(func)
                else:
                    self._callbacks[key] = [func]
            return func

        return decor

    def execute(self, routing_key: str, **kwargs) -> Iterator[RT]:
        if routing_key not in self._callbacks:
            raise KeyError(f'Callback for key {routing_key} not registered')
        for callback in self._callbacks[routing_key]:
            try:
                yield callback(**kwargs)
            except:
                logger.exception(f'Error executing callback for key {routing_key}: {callback}')
                logger.error(kwargs)

    def execute_silently(self, routing_key: str, **kwargs) -> Iterator[RT]:
        try:
            yield from self.execute(routing_key, **kwargs)
        except KeyError:
            yield from []
