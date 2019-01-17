import atexit
from unittest import mock

import pytest

from edp import settings


@pytest.fixture(autouse=True)
def atexit_clear():
    yield
    atexit._clear()


@pytest.fixture(autouse=True)
def patch_settings_dir(tempdir):
    with mock.patch('edp.config.SETTINGS_DIR', new=tempdir):
        yield


def test_settings_singleton(tempdir):
    s = settings.BaseSettings.get_insance('foo')
    s2 = settings.BaseSettings.get_insance('foo')
    assert s2 is s


def test_settings_saved(tempdir):
    class SettingsTest(settings.BaseSettings):
        foo: str = '1'

    s = SettingsTest.get_insance('test')

    assert s.foo == '1'
    s.foo = '2'
    assert s.foo == '2'

    atexit._run_exitfuncs()
    settings.BaseSettings.__setting_per_name__.pop('test')

    s = SettingsTest.get_insance('test')
    assert s.foo == '2'


def test_access_unknown_attr(tempdir):
    s = settings.SimpleSettings.get_insance('test')
    with pytest.raises(AttributeError):
        getattr(s, 'bar')


def test_set_unknown_attr(tempdir):
    s = settings.SimpleSettings.get_insance('test')
    s.bar = 'test'

    assert s.bar == 'test'
