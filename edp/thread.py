"""Threading helpers"""
import logging
import threading
import time
from typing import List, Callable, Union

logger = logging.getLogger(__name__)


class StoppableThread(threading.Thread):
    """
    Thread that can be stopped.

    Most of the time background threads is something that runs in a `while` loop and executes routines periodically.
    To allow stopping such threads, this class was created.

    When creating such background loop, use `while self.is_stopped` and `self.sleep(10)` to be able to stop
    thread in those places.
    """
    _stopped = False

    def start(self):
        self._stopped = False
        super(StoppableThread, self).start()

    def stop(self):
        """
        Stop thread.

        Does not actually stops thread.
        """
        self._stopped = True

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    @property
    def is_stopped(self):
        """Return True if current thread is stopped."""
        return self._stopped

    def sleep(self, interval: Union[int, float]):
        """
        Thread stop aware sleeping.

        Use this instead of regular time.sleep inside thread.

        :param interval: Sleep interval, in seconds
        """
        while interval > 0 and not self.is_stopped:
            if interval > 1:
                interval -= 1
                time.sleep(1)
            else:
                time.sleep(interval)
                interval = 0


class IntervalRunnerThread(StoppableThread):
    """Thread that executes its target repeatedly with given intervals"""

    def __init__(self, target: Callable, interval: Union[int, float] = 1, skipfirst: bool = False, **kwargs):
        """
        :param interval: sleep interval between executions, in seconds
        """
        self._interval = interval
        self._skipfirst = skipfirst
        kwargs['target'] = target
        super(IntervalRunnerThread, self).__init__(**kwargs)

    # noinspection PyUnresolvedReferences
    def run(self):
        while not self.is_stopped:
            try:
                if not self._skipfirst:
                    self._target(*self._args, **self._kwargs)
                else:
                    self._skipfirst = False
            except:
                logger.exception('Error executing interval function %s', self._target)
            finally:
                self.sleep(self._interval)


class ThreadManager:
    """
    Manages threads across application lifetime

    Implements context manager interface. Starts registered threads on context enter,
    stops them on context exit.
    """

    def __init__(self):
        self._threads: List[StoppableThread] = []
        self._started = False

    def add_interval_thread(self, func: Callable, interval):
        """
        Create and start interval thread with given function as target
        """
        thread = IntervalRunnerThread(func, interval=interval)
        self.add_thread(thread)

    def add_thread(self, thread: StoppableThread):
        """
        Register thread with manager.

        Starts thread only if thread manager already started.
        """
        self._threads.append(thread)
        logger.debug('Registered thread %s', thread)
        if self._started:
            thread.start()

    def add_threads(self, *threads: StoppableThread):
        """Register multiple threads. Just a shortcut."""
        for thread in threads:
            self.add_thread(thread)

    def start(self):
        """Start registered threads"""
        self._started = True
        for thread in self._threads:
            try:
                thread.start()
            except:
                logger.exception('Failed to start thread %s', thread)

    def stop(self):
        """Stop registered threads"""
        for thread in self._threads:
            try:
                thread.stop()
            except:
                logger.exception('Failed to stop thread %s', thread)

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
