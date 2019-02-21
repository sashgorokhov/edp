import time
from unittest import mock

import pytest

from edp.thread import IntervalRunnerThread, ThreadManager, StoppableThread


class ThreadTest(StoppableThread):
    def __init__(self, *args, **kwargs):
        self.mock = mock.MagicMock()
        super(ThreadTest, self).__init__(*args, **kwargs)

    def run(self):
        while not self.is_stopped:
            self.mock()
            self.sleep(0.1)


def test_stoppable_thread_starts():
    mockfunc = mock.MagicMock()

    thread = StoppableThread(target=mockfunc, args=('test',))
    thread.start()
    time.sleep(0.1)

    mockfunc.assert_called_once_with('test')


def test_stoppable_thread_stops():
    thread = ThreadTest()
    thread.start()
    time.sleep(0.5)

    thread.stop()

    time.sleep(1)

    thread.mock.assert_called()
    assert thread.is_stopped
    assert not thread.is_alive()


def test_stoppable_thread_contextmanager():
    with ThreadTest() as thread:
        time.sleep(0.5)

    time.sleep(1)

    thread.mock.assert_called()
    assert thread.is_stopped
    assert not thread.is_alive()


@pytest.mark.parametrize('interval', [2, 1, 0.5])
def test_stoppable_thread_sleep(interval):
    class MyTestThread(ThreadTest):
        def run(self):
            self.mock()
            self.sleep(interval)

    start = time.time()

    with MyTestThread() as thread:
        time.sleep(2)

    end = time.time()

    time.sleep(1)

    assert end - start < 5

    thread.mock.assert_called()
    assert thread.is_stopped
    assert not thread.is_alive()


def test_interval_runner_thread():
    mockfunc = mock.MagicMock()

    with IntervalRunnerThread(mockfunc, interval=0.2) as thread:
        time.sleep(0.5)

    time.sleep(1)

    assert mockfunc.call_count == 3
    assert thread.is_stopped
    assert not thread.is_alive()


def test_interval_runner_thread_exception():
    mockfunc = mock.MagicMock(side_effect=ValueError)

    with IntervalRunnerThread(mockfunc, interval=0.2) as thread:
        time.sleep(0.5)

    time.sleep(1)

    assert mockfunc.call_count == 3
    assert thread.is_stopped
    assert not thread.is_alive()


def test_thread_manager_start_threads():
    mock_thread_1 = mock.MagicMock(spec=StoppableThread)
    mock_thread_2 = mock.MagicMock(spec=StoppableThread)

    manager = ThreadManager()
    manager.add_threads(mock_thread_1, mock_thread_2)

    manager.start()

    mock_thread_1.start.assert_called_once()
    mock_thread_2.start.assert_called_once()


def test_thread_manager_stop_threads():
    mock_thread_1 = mock.MagicMock(spec=StoppableThread)
    mock_thread_2 = mock.MagicMock(spec=StoppableThread)

    manager = ThreadManager()
    manager.add_threads(mock_thread_1, mock_thread_2)

    manager.start()
    manager.stop()

    mock_thread_1.stop.assert_called_once()
    mock_thread_2.stop.assert_called_once()


def test_thread_manager_start_threads_exception():
    mock_thread_1 = mock.MagicMock(spec=StoppableThread)
    mock_thread_1.start.side_effect = ValueError
    mock_thread_2 = mock.MagicMock(spec=StoppableThread)

    manager = ThreadManager()
    manager.add_threads(mock_thread_1, mock_thread_2)

    manager.start()

    mock_thread_1.start.assert_called_once()
    mock_thread_2.start.assert_called_once()


def test_thread_manager_stop_threads_exception():
    mock_thread_1 = mock.MagicMock(spec=StoppableThread)
    mock_thread_1.stop.side_effect = ValueError
    mock_thread_2 = mock.MagicMock(spec=StoppableThread)

    manager = ThreadManager()
    manager.add_threads(mock_thread_1, mock_thread_2)

    manager.stop()

    mock_thread_1.stop.assert_called_once()
    mock_thread_2.stop.assert_called_once()


def test_thread_manager_contextmanager():
    mock_thread_1 = mock.MagicMock(spec=StoppableThread)
    mock_thread_2 = mock.MagicMock(spec=StoppableThread)

    manager = ThreadManager()
    manager.add_threads(mock_thread_1, mock_thread_2)

    with manager:
        time.sleep(0.1)

    mock_thread_1.start.assert_called_once()
    mock_thread_2.start.assert_called_once()

    mock_thread_1.stop.assert_called_once()
    mock_thread_2.stop.assert_called_once()


def test_interval_runner_thread_skipfirst():
    mockfunc = mock.MagicMock()

    with IntervalRunnerThread(mockfunc, interval=0.2, skipfirst=True) as thread:
        time.sleep(0.5)

    time.sleep(0.1)

    assert mockfunc.call_count == 2


def test_thread_manager_starts_threads_if_started():
    manager = ThreadManager()
    manager.start()

    assert manager._started

    mock_thread_1 = mock.MagicMock(spec=StoppableThread)
    manager.add_thread(mock_thread_1)

    mock_thread_1.start.assert_called_once()


def test_thread_manager_add_interval_thread():
    manager = ThreadManager()
    target = mock.MagicMock()
    manager.add_interval_thread(target, interval=0.1)

    assert len(manager._threads) == 1
    assert manager._threads[0]._target is target
