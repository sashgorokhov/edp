import threading


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
