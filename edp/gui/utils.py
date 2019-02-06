from PyQt5 import QtWidgets


def clear_layout(layout: QtWidgets.QLayout):
    while layout.count():
        item: QtWidgets.QLayoutItem = layout.takeAt(0)
        widget = item.widget()
        widget.setParent(None)
