import os

import PyQt5
from PyQt5.QtWidgets import QApplication, QWidget

pyqt = os.path.dirname(PyQt5.__file__)
QApplication.addLibraryPath(os.path.join(pyqt, "qt", "plugins"))


class MainWindow(QWidget):
    pass
