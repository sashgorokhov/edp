# Define builtin signals
import logging
import queue
from types import FunctionType
from typing import Type, List, NamedTuple, Dict, Union, Callable

from edp.thread import StoppableThread
from edp.utils import is_dict_subset

JOURNAL_EVENT = 'journal event'
INIT_COMPLETE = 'init complete'

logger = logging.getLogger(__name__)


def check_signature(func: FunctionType, signature: Dict[str, Type]) -> bool:
    return is_dict_subset(func.__annotations__, signature)


def get_data_signature(data: dict) -> Dict[str, Type]:
    d: Dict[str, Type] = {}

    for key, value in data.items():
        d[key] = type(value)

    return d


class Signal:
    # TODO: Support typing types signature, e.g. Optional[str] and so on
    def __init__(self, name: str, **signature: Type):
        self.name = name
        self.signature: Dict[str, Type] = signature
        self.callbacks: List[Callable] = []

    def bind_nonstrict(self, func: Callable):
        self.callbacks.append(func)
        return func

    def bind(self, func: Callable):
        self.check_signature(func)  # runtime type checking, yay!
        self.callbacks.append(func)
        return func  # to be used as decorator

    def emit(self, **data):
        self.check_signature(data)
        signal_manager.emit(self, **data)

    def check_signature(self, func_or_data: Union[Callable, Dict]):
        if isinstance(func_or_data, FunctionType) and not check_signature(func_or_data, self.signature):
            raise TypeError(f'Signature mismatch: {self.signature} != {func_or_data} {func_or_data.__annotations__}')
        elif isinstance(func_or_data, Dict):
            data_signature = get_data_signature(func_or_data)
            if data_signature != self.signature:
                raise TypeError(f'Signature mismatch: {self.signature} != {data_signature}')


class SignalExecutionItem(NamedTuple):
    name: str
    callbacks: List[Callable]
    kwargs: dict


class SignalExecutorThread(StoppableThread):
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
    for callback in signal_item.callbacks:
        try:
            callback(**signal_item.kwargs)
        except:
            logger.exception(f'Error calling callback {callback} of signal {signal_item.name}')


class SignalManager:
    def __init__(self):
        self._signal_queue = queue.Queue()
        self._signal_executor_thread = SignalExecutorThread(self._signal_queue)

    def get_signal_executor_thread(self) -> SignalExecutorThread:
        return self._signal_executor_thread

    def emit(self, signal: Signal, **kwargs):
        if signal.callbacks:
            signal_item = SignalExecutionItem(signal.name, signal.callbacks, kwargs)
            self._signal_queue.put_nowait(signal_item)


signal_manager = SignalManager()
