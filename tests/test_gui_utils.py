from PyQt5 import QtWidgets

from edp.gui.utils import clear_layout


def test_clear_layout():
    layout = QtWidgets.QVBoxLayout()
    layout.addWidget(QtWidgets.QLabel())
    layout.addWidget(QtWidgets.QLabel())

    assert layout.count() == 2

    clear_layout(layout)
    assert layout.count() == 0
