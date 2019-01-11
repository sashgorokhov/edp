import logging
import threading
import time
from typing import List, Callable

logger = logging.getLogger(__name__)


class StoppableThread(threading.Thread):
    _stopped = False

    def start(self):
        self._stopped = False
        super(StoppableThread, self).start()

    def stop(self):
        self._stopped = True

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    @property
    def is_stopped(self):
        return self._stopped

    def sleep(self, interval: int):
        while interval > 0 and not self.is_stopped:
            if interval > 1:
                interval -= 1
                time.sleep(1)
            else:
                time.sleep(interval)
                interval = 0


class IntervalRunnerThread(StoppableThread):
    def __init__(self, target: Callable, *args, interval=1, **kwargs):
        self._interval = interval
        super(IntervalRunnerThread, self).__init__(*args, target=target, **kwargs)

    # noinspection PyUnresolvedReferences
    def run(self):
        while not self.is_stopped:
            try:
                self._target(*self._args, **self._kwargs)
            except:
                logger.exception('Error executing interval function %s', self._target)
            finally:
                self.sleep(self._interval)


class ThreadManager:
    def __init__(self):
        self._threads: List[StoppableThread] = []

    def add_interval_thread(self, func: Callable, interval):
        thread = IntervalRunnerThread(func, interval=interval)
        self.add_thread(thread)

    def add_thread(self, thread: StoppableThread):
        self._threads.append(thread)
        logger.debug('Registered thread %s', thread)

    def add_threads(self, *threads: StoppableThread):
        for thread in threads:
            self.add_thread(thread)

    def start(self):
        for thread in self._threads:
            try:
                thread.start()
            except:
                logger.exception('Failed to start thread %s', thread)

    def stop(self):
        for thread in self._threads:
            try:
                thread.stop()
            except:
                logger.exception('Failed to stop thread %s', thread)

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
