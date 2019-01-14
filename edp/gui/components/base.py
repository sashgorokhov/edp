from typing import Optional

from PyQt5 import QtWidgets


class BaseMainWindowSection(QtWidgets.QWidget):
    name: Optional[str] = None
