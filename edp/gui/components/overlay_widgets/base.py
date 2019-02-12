"""Base things for overlay ui widgets"""
from PyQt5 import QtWidgets


class BaseOverlayWidget(QtWidgets.QWidget):
    """Base class for overlay widgets"""
    friendly_name: str = ''
