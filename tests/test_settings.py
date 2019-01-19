import atexit
from typing import Optional

import pytest

from edp import settings


def test_settings_singleton():
    s = settings.BaseSettings.get_insance('foo')
    s2 = settings.BaseSettings.get_insance('foo')
    assert s2 is s


def test_settings_saved():
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


def test_access_unknown_attr():
    s = settings.SimpleSettings.get_insance('test')
    with pytest.raises(AttributeError):
        getattr(s, 'bar')


def test_set_unknown_attr():
    s = settings.SimpleSettings.get_insance('test')
    s.bar = 'test'

    assert s.bar == 'test'


def test_settings_none_field():
    class SettingsTest(settings.BaseSettings):
        field: Optional[str] = None

    s = SettingsTest.get_insance()
    assert s.field is None

    s.field = '1'

    assert s.field == '1'
