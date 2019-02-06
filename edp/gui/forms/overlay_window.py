import enum
import logging
import win32gui
from functools import partial
from typing import NamedTuple, Optional, NewType, Iterator, Dict, Mapping

import inject
import win32con
from PyQt5 import QtWidgets, QtCore

from edp import config, thread, signalslib, journal
from edp.gui.compiled.overlay_window import Ui_Form
from edp.gui.components.base import JournalEventHandlerMixin
from edp.gui.components.overlay_widgets.base import BaseOverlayWidget
from edp.gui.components.overlay_widgets.manager import get_registered_widgets
from edp.gui.utils import clear_layout
from edp.utils import winhotkeys, catcherr

OPACITY_ALMOST_NONE = 0.08

OPACITY_HALF = 0.5

OPACITY_FULL = 1.0

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


class OverlayWidgetSelector(QtCore.QObject):
    def __init__(self, layouts: Mapping[str, QtWidgets.QLayout], widgets: Iterator[BaseOverlayWidget]):
        super(OverlayWidgetSelector, self).__init__()
        self._layouts = layouts
        self._widgets: Dict[str, BaseOverlayWidget] = {w.friendly_name: w for w in widgets}
        from edp.contrib.overlay_ui import OverlaySettings
        self._settings = OverlaySettings.get_insance()
        # seems like dict is not needed here
        self._widget_selectors: Dict[str, QtWidgets.QComboBox] = {}

    def setup(self):
        if self._widget_selectors:
            self._settings.layout_widgets.clear()

        while self._widget_selectors:
            layout_name, combobox = self._widget_selectors.popitem()
            text = combobox.currentText()
            widget = self._widgets.get(text, None)
            if widget:
                self._settings.layout_widgets[layout_name] = widget.friendly_name

        for layout_name, layout in self._layouts.items():
            clear_layout(layout)

            if layout_name not in self._settings.layout_widgets:
                continue

            widget_name = self._settings.layout_widgets[layout_name]
            widget = self._widgets.get(widget_name, None)

            if not widget:
                logger.warning(f'Widget not registered: {widget_name}')
                self._settings.layout_widgets.pop(layout_name)
                continue

            layout.addWidget(widget)

    @catcherr
    def create_widget_selectors(self):
        for layout_name, layout in self._layouts.items():
            clear_layout(layout)
            combobox = self._create_widget_selector()
            layout.addWidget(combobox)
            self._widget_selectors[layout_name] = combobox

            if layout_name in self._settings.layout_widgets:
                widget_name = self._settings.layout_widgets[layout_name]
                if widget_name not in self._widgets:
                    logger.warning(f'Unregistered widget: {widget_name}')
                    self._settings.layout_widgets.pop(layout_name)
                    continue
                combobox.setCurrentText(widget_name)

    def _create_widget_selector(self) -> QtWidgets.QComboBox:
        combobox = QtWidgets.QComboBox()
        combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        combobox.addItem('---')
        for widget_name in self._widgets.keys():
            combobox.addItem(widget_name)
        combobox.setCurrentIndex(0)
        combobox.currentTextChanged.connect(partial(self._on_selector_text_changed, combobox))
        return combobox

    @catcherr
    def _on_selector_text_changed(self, combobox: QtWidgets.QComboBox, text: str):
        if text == '---':
            for selector in self._widget_selectors.values():
                for widget_name in self._widgets:
                    if selector.findText(widget_name) < 0:
                        selector.addItem(widget_name)
            return

        for selector in self._widget_selectors.values():
            if selector is combobox:
                continue

            index = selector.findText(text)
            if index >= 0:
                if selector.currentIndex() == index:
                    selector.setCurrentIndex(0)
                selector.removeItem(index)


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

        widgets = list(get_registered_widgets())
        logger.info(f'Registered overlay widgets: {[w.friendly_name for w in widgets]}')

        self._widget_selector = OverlayWidgetSelector(self.get_layouts(), widgets)
        self._widget_selector.setup()

        self.setup_button.toggled.connect(self.on_setup_buttin_toggled)

    @catcherr
    def on_setup_buttin_toggled(self, state: bool):
        if state:
            self._widget_selector.create_widget_selectors()
        else:
            self._widget_selector.setup()

    def get_layouts(self) -> Dict[str, QtWidgets.QLayout]:
        return {
            'top_left': self.vlayout_top_left,
            'top_center': self.vlayout_top_center,
            'top_right': self.vlayout_top_right,
            'middle_left': self.vlayout_center_left,
            'middle_center': self.vlayout_center,
            'middle_right': self.vlayout_center_right,
            'bottom_left': self.vlayout_bottom_left,
            'bottom_center': self.vlayout_bottom_center,
            'bottom_right': self.vlayout_bottom_right
        }

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
        # self.setFixedSize(800, 600)
        # self.move(400, 400)
        # win32gui.SetFocus(self.ed_window_handler)
        super(GameOverlayWindow, self).show()

    def on_journal_event(self, event: journal.Event):
        if event.name == 'Status':
            gui_focus = GuiFocus(event.data.get('GuiFocus', 0))
            if gui_focus is not GuiFocus.NoFocus:
                self.setWindowOpacity(OPACITY_ALMOST_NONE)
            else:
                self.setWindowOpacity(OPACITY_HALF)

    def enterEvent(self, *args, **kwargs):
        self.setWindowOpacity(OPACITY_FULL)

    def leaveEvent(self, *args, **kwargs):
        self.setWindowOpacity(OPACITY_HALF)
