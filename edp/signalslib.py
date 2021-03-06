"""
Application signals implementation.

Allows creating declarative, typed and asynhronous signals to send events across an application.


"""
import copy
import logging
import queue
from types import FunctionType
from typing import Type, List, NamedTuple, Dict, Union, Callable

from edp.thread import StoppableThread
from edp.utils import is_dict_subset

logger = logging.getLogger(__name__)


def check_signature(func: FunctionType, signature: Dict[str, Type]) -> bool:
    """
    Check function signature that match given param name -> type mapping. Uses function type annotations.
    """
    return is_dict_subset(func.__annotations__, signature)


def get_data_signature(data: dict) -> Dict[str, Type]:
    """
    Return dict values types.
    """
    d: Dict[str, Type] = {}

    for key, value in data.items():
        d[key] = type(value)

    return d


class Signal:
    """
    Define signal with name and signature

    Signature is used to verify binded callbacks and sent data.
    """
    # need support for typing types, like Optional[int]
    def __init__(self, name: str, **signature: Type):
        self.name = name
        self.signature: Dict[str, Type] = signature
        self.callbacks: List[Callable] = []

    def bind_nonstrict(self, func: Callable):
        """
        Bind callback without checking signature.

        Most of the time you dont want to use this,
        unless you bind lambdas that emit pyqt signals.
        """
        self.callbacks.append(func)
        return func

    def bind(self, func: Callable):
        """
        Bind callback, check its signature.

        :raises TypeError: If callback and signal signatures does not match
        """
        self.check_signature(func)  # runtime type checking, yay!
        self.callbacks.append(func)
        return func  # to be used as decorator

    def emit(self, **data):
        """
        Execute signals callbacks with given data, asynchronously. Checks data signature.
        """
        self.check_signature(data)
        signal_manager.emit(self, **data)

    def emit_eager(self, **data):
        """
        Execute signals callbacks with given data, synchronously. Checks data signature.

        Should be used with cauton.
        """
        self.check_signature(data)
        signal_manager.emit_eager(self, **data)

    def check_signature(self, func_or_data: Union[Callable, Dict]):
        """
        Check function or data signature with signal signature.

        :raises TypeError: If signatures does not match.
        """
        if isinstance(func_or_data, FunctionType) and not check_signature(func_or_data, self.signature):
            raise TypeError(f'Signature mismatch: {self.signature} != {func_or_data} {func_or_data.__annotations__}')
        elif isinstance(func_or_data, Dict):
            data_signature = get_data_signature(func_or_data)
            if data_signature != self.signature:
                raise TypeError(f'Signature mismatch: {self.signature} != {data_signature}')


class SignalExecutionItem(NamedTuple):
    """
    Container for signal data to be executed asynchronously.
    """
    name: str
    callbacks: List[Callable]
    kwargs: dict


class SignalExecutorThread(StoppableThread):
    """
    Thread for asynchronous signal execution.
    """

    def __init__(self, signal_queue: queue.Queue):
        self._signal_queue = signal_queue
        super(SignalExecutorThread, self).__init__()

    def run(self):
        while not self.is_stopped:
            try:
                signal_item: SignalExecutionItem = self._signal_queue.get(block=True, timeout=1)
            except queue.Empty:
                continue

            execute_signal_item(signal_item)


def execute_signal_item(signal_item: SignalExecutionItem):
    """Execute all callbacks in given SignalExecutionItem"""
    for callback in signal_item.callbacks:
        try:
            kwargs = copy.deepcopy(signal_item.kwargs)
        except Exception as e:
            logger.debug(f'Failed to deepcopy signal data: {e}')
            kwargs = signal_item.kwargs
        try:
            callback(**kwargs)
        except:
            logger.exception(f'Error calling callback {callback} of signal {signal_item.name}')


class SignalManager:
    """Manages asynchronous signal execution. Private api."""
    def __init__(self):
        self._signal_queue = queue.Queue()
        self._signal_executor_thread = SignalExecutorThread(self._signal_queue)

    def get_signal_executor_thread(self) -> SignalExecutorThread:
        """Return thread that executes signals"""
        return self._signal_executor_thread

    def emit(self, signal: Signal, **kwargs):
        """Asynchronously execute given signal with data"""
        if signal.callbacks:
            signal_item = SignalExecutionItem(signal.name, signal.callbacks, kwargs)
            self._signal_queue.put_nowait(signal_item)

    # pylint: disable=no-self-use
    def emit_eager(self, signal: Signal, **kwargs):
        """Synchronously execute given signal with data"""
        if signal.callbacks:
            signal_item = SignalExecutionItem(signal.name, signal.callbacks, kwargs)
            execute_signal_item(signal_item)


signal_manager = SignalManager()
