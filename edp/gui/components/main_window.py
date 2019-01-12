from PyQt5.QtWidgets import QMainWindow

from edp.gui.compiled.main_window import Ui_MainWindow


class MainWindow(Ui_MainWindow, QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
