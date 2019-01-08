import threading
import time


class StoppableThread(threading.Thread):
    _stopped = False

    def start(self):
        self._stopped = False
        super(StoppableThread, self).start()

    def stop(self):
        self._stopped = True

    def __enter__(self):
        self.start()

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
