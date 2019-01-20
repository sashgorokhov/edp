import threading
from typing import List

from edp import journal, plugins


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
