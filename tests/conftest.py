import atexit
import pathlib
import tempfile
from unittest import mock

import pytest
from PyQt5 import QtWidgets

from edp import settings

FIXTURES_DIR = pathlib.Path(__file__).parent / 'fixtures'
FIXTURE_RANDOM_JOURNAL_DIR = FIXTURES_DIR / 'random_journal'


@pytest.fixture(scope='session')
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture(scope='session')
def random_journal_dir():
    return FIXTURE_RANDOM_JOURNAL_DIR


@pytest.fixture()
def tempdir():
    with tempfile.TemporaryDirectory() as tempdir:
        yield pathlib.Path(tempdir)


@pytest.fixture(autouse=True)
def atexit_clear(tempdir):
    yield
    atexit._clear()


@pytest.fixture(autouse=True)
def patch_settings_dir(tempdir):
    with mock.patch('edp.config.SETTINGS_DIR', new=tempdir):
        yield


@pytest.fixture(autouse=True)
def clear_settings_instances(patch_settings_dir, tempdir):
    yield
    for key, value in settings.BaseSettings.__setting_per_name__.items():
        value._shelve.close()

    settings.BaseSettings.__setting_per_name__.clear()


@pytest.fixture('session', autouse=True)
def qapp():
    app = QtWidgets.QApplication([])
    yield app
    app.quit()


@pytest.fixture()
def process_events(qapp):
    return lambda: qapp.processEvents()
