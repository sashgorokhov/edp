"""Qt and GUI utility functions"""
from PyQt5 import QtWidgets


def clear_layout(layout: QtWidgets.QLayout):
    """Remove all items from layout"""
    while layout.count():
        item: QtWidgets.QLayoutItem = layout.takeAt(0)
        widget = item.widget()
        widget.setParent(None)
