from unittest import mock

import pytest

from edp.utils import plugins_helpers
from edp.utils.hypothesis_strategies import TestEvent


@pytest.fixture()
def buffered_events_mixin():
    obj = plugins_helpers.BufferedEventsMixin()
    with mock.patch.object(obj, 'process_buffered_events'):
        yield obj


def test_process_buffered_events_not_called_on_empty_buffer(buffered_events_mixin):
    assert len(buffered_events_mixin._events_buffer) == 0
    buffered_events_mixin.buffer_flush_callback()
    buffered_events_mixin.process_buffered_events.assert_not_called()


def test_on_journal_event_filtered_out(event, buffered_events_mixin):
    with mock.patch.object(buffered_events_mixin, 'filter_event') as m:
        m.return_value = False
        buffered_events_mixin.on_journal_event(event)

    m.assert_called_once_with(event)
    assert len(buffered_events_mixin._events_buffer) == 0


@pytest.fixture()
def event():
    return TestEvent().example()


def test_on_journal_event_added(buffered_events_mixin, event):
    buffered_events_mixin.on_journal_event(event)
    assert len(buffered_events_mixin._events_buffer) == 1
    assert buffered_events_mixin._events_buffer[0] == event


def test_buffer_flush_callback_with_events(buffered_events_mixin, event):
    buffered_events_mixin.on_journal_event(event)
    buffered_events_mixin.buffer_flush_callback()
    assert len(buffered_events_mixin._events_buffer) == 0
    buffered_events_mixin.process_buffered_events.assert_called_once_with([event])


def test_exit_callback_triggers_buffer_flush(buffered_events_mixin, event):
    buffered_events_mixin.on_journal_event(event)
    buffered_events_mixin.exit_callback()
    assert len(buffered_events_mixin._events_buffer) == 0
    buffered_events_mixin.process_buffered_events.assert_called_once_with([event])
