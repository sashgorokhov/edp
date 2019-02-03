import enum
import logging
import win32gui
from typing import NamedTuple, Optional, NewType

import inject
import win32con
from PyQt5 import QtWidgets, QtCore

from edp import config, thread, signalslib, journal
from edp.gui.compiled.overlay_window import Ui_Form
from edp.gui.components.base import JournalEventHandlerMixin
from edp.utils import winhotkeys, catcherr

logger = logging.getLogger(__name__)

toggle_overlay_signal = signalslib.Signal('toggle overlay ui')

hotkey_list = [
    winhotkeys.HotkeyInfo(winhotkeys.signal_emit_action(toggle_overlay_signal), win32con.VK_TAB, win32con.MOD_CONTROL)
]


class WindowRect(NamedTuple):
    x: int
    y: int
    h: int
    w: int


class GuiFocus(enum.Enum):
    NoFocus = 0
    InternalPanel = 1
    ExternalPanel = 2
    CommsPanel = 3
    RolePanel = 4
    StationServices = 5
    GalaxyMap = 6
    SystemMap = 7


WindowHandler = NewType('WindowHandler', int)


def get_ed_window_handler() -> Optional[WindowHandler]:
    handler: Optional[WindowHandler] = None

    def callback(hwnd: WindowHandler, extra):
        nonlocal handler

        window_class = win32gui.GetClassName(hwnd)
        if window_class == 'FrontierDevelopmentsAppWinClass':
            handler = hwnd
            return

    win32gui.EnumWindows(callback, None)
    return handler


def get_ed_window_rect(handler: WindowHandler) -> WindowRect:
    rect = win32gui.GetWindowRect(handler)
    return WindowRect(rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])


class GameOverlayWindow(JournalEventHandlerMixin, Ui_Form, QtWidgets.QWidget):
    thread_manager: thread.ThreadManager = inject.attr(thread.ThreadManager)

    toggle_visibility_signal = QtCore.pyqtSignal()

    def __init__(self):
        super(GameOverlayWindow, self).__init__()
        self.setupUi(self)

        self.setWindowTitle(f'{config.APPNAME_SHORT} - Overlay')
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowOpacity(0.5)
        # self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.ed_window_handler: Optional[WindowHandler] = None

        self.toggle_visibility_signal.connect(self.toggle_visibility)

        toggle_overlay_signal.bind_nonstrict(lambda: self.toggle_visibility_signal.emit())

        self.thread_manager.add_thread(
            winhotkeys.KeyMessageDispatchThread(hotkey_list)
        )

    @catcherr
    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def show(self):
        if not self.ed_window_handler:
            handler = get_ed_window_handler()
            if not handler:
                logger.warning('ED window not found')
                return
            self.ed_window_handler = handler

        focus_handler = win32gui.GetFocus()
        if self.ed_window_handler != focus_handler and focus_handler != 0:
            return

        rect = get_ed_window_rect(self.ed_window_handler)
        logger.debug(f'ED window rect is {rect}')
        self.setFixedSize(rect.h, rect.w)
        self.move(rect.x, rect.y)
        # win32gui.SetFocus(self.ed_window_handler)
        super(GameOverlayWindow, self).show()

    def on_journal_event(self, event: journal.Event):
        if event.name == 'Status':
            gui_focus = GuiFocus(event.data.get('GuiFocus', 0))
            if gui_focus is not GuiFocus.NoFocus:
                self.setWindowOpacity(0.1)
            else:
                self.setWindowOpacity(0.5)
