import collections
import dataclasses
import logging
import threading
import time

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


def catch_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            logger.exception('Error in %s', func)

    return wrapper


def _dataclass_as_namedtuple_factory(obj):
    if dataclasses.is_dataclass('a'):
        return collections.namedtuple(obj.__class__.__name__, tuple(obj.__dataclass_fields__.keys()))(
            **dataclasses.asdict(obj))
    return tuple(obj)


def dataclass_as_namedtuple(obj):
    return dataclasses.astuple(obj, tuple_factory=_dataclass_as_namedtuple_factory)

# T = TypeVar('T')
#
#
# @contextlib.contextmanager
# def shield_setattr(obj: T, sentinel) -> T:
#     assert dataclasses.is_dataclass(obj)
#
#     if hasattr(obj.__class__.__setattr__, '__shielded__'):
#         return obj
#
#     for field_name, field in obj.__dataclass_fields__.items():
#         if dataclasses.is_dataclass(field.type):
#             setattr(obj, field_name, shield_setattr(getattr(obj, field_name), sentinel))
#
#     def __shielded_setattr__(self, key, value):
#         print(self, key, value, sentinel)
#         if value is sentinel:
#             return
#         return super(self.__class__, self).__setattr__(key, value)
#
#     __shielded_setattr__.__shielded__ = True
#
#     original_setattr = obj.__setattr__
#
#     obj.__class__.__setattr__ = __shielded_setattr__
#
#     yield
#
#     obj.__class__.__setattr__ = original_setattr
#
