import pytest
from PyQt5 import QtWidgets


@pytest.fixture('module', autouse=True)
def qapp():
    app = QtWidgets.QApplication([])
    yield app
    app.quit()


@pytest.fixture()
def process_events(qapp):
    return lambda: qapp.processEvents()
