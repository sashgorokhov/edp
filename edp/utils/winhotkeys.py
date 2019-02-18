"""
Register handler for windows hotkeys

http://timgolden.me.uk/python/win32_how_do_i/catch_system_wide_hotkeys.html
"""

import ctypes
import logging
from typing import List, Callable, NamedTuple, Any, Optional

import win32con  # pylint: disable=import-error

from edp import thread, signalslib

byref = ctypes.byref
user32 = ctypes.windll.user32

logger = logging.getLogger(__name__)


class HotkeyInfo(NamedTuple):
    """Container for hotkey handler data"""
    action: Callable[[], None]
    key: Any
    modifier: Optional[Any]


def signal_emit_action(signal: signalslib.Signal) -> Callable[[], None]:
    """
    Helper shortcut for emitting signal on hotkey
    """
    def wrapper():
        signal.emit()

    return wrapper


class KeyMessageDispatchThread(thread.StoppableThread):
    """
    Thread for processing windows events and executing actions on hotkey events.
    """
    def __init__(self, hotkey_list: List[HotkeyInfo]):
        super(KeyMessageDispatchThread, self).__init__()

        self._hotkey_list = hotkey_list

    def run(self):
        msg = ctypes.wintypes.MSG()

        def dummy():
            pass

        actions: List[Callable[[], None]] = [dummy]

        for hotkey in self._hotkey_list:
            actions.append(hotkey.action)

            if not user32.RegisterHotKey(None, len(actions) - 1, hotkey.modifier, hotkey.key):
                logger.error(f'Failed to register hotkey {hotkey.action} {hotkey.key} {hotkey.modifier}')

        while not self.is_stopped:
            self.sleep(0.1)
            # (ಠ‿ಠ)
            if user32.PeekMessageA(byref(msg), None, 0, 0, win32con.PM_REMOVE) == 0:
                continue

            if msg.message == win32con.WM_HOTKEY and 0 < msg.wParam < len(actions):
                action = actions[msg.wParam]
                logger.debug(f'Pressed hotkey for action {action}')

                try:
                    action()
                except:
                    logger.exception(f'Failed to execute hotkey action {action}')

            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageA(byref(msg))

        for i in range(1, len(self._hotkey_list)):
            user32.UnregisterHotKey(None, i)
