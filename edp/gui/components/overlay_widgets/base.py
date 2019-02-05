from PyQt5 import QtWidgets


class BaseOverlayWidget(QtWidgets.QWidget):
    friendly_name: str = ''

    def __init__(self):
        super(BaseOverlayWidget, self).__init__()
