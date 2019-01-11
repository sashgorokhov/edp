import pathlib
import tempfile

import pytest

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
