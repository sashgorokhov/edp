"""
Application settings implementation

This adds simple, declarative and persistant settings.

Example:

    class MySettings(BaseSettings):
        name: str = 'Alex'
        age: Optional[int] = None


    settings = MySettings.get_instance()

Settings class implements singleton pattern in get_instance() method. Usually you want to get your settings this way.
It also implements dict interface so all data can be accessed as dict:

    settings['age'] = 1

Data will be automatically flushed on disk upon program termination. Inernally this class uses shelve library to store
data.
"""
import atexit
import logging
import shelve
import uuid
from collections import UserDict
from pathlib import Path
from typing import Union, Optional, Dict, Any

from edp import config
from edp.utils import get_default_journal_path

logger = logging.getLogger(__name__)


def get_settings_path(name: str) -> Path:
    """Return absolute path to settings with given name"""
    path = (config.SETTINGS_DIR / name)
    return path.with_name(path.name + '.shelve')


# pylint: disable=too-many-ancestors
class BaseSettings(UserDict):
    """
    Base class for settings

    Settings should be defined as typed class attributes with defaults.
    """
    __setting_per_name__: Dict[str, 'BaseSettings'] = {}
    __attributes__: Dict[str, Any] = {}

    def __init__(self, path: Path):
        super(BaseSettings, self).__init__()

        path.parent.mkdir(parents=True, exist_ok=True)

        self._shelve = shelve.open(str(path), writeback=True)
        self.data = self._shelve  # type: ignore

        for key in self.__class__.__annotations__:
            if hasattr(self.__class__, key) and key not in BaseSettings.__dict__:
                value = getattr(self, key)
                self.__class__.__attributes__[key] = value
                # cant use setdefault here
                if key not in self.data:
                    self.data[key] = value
                delattr(self.__class__, key)
            elif key in self.__class__.__attributes__:
                self.data.setdefault(key, self.__class__.__attributes__[key])

        atexit.register(self._shelve.close)

    @classmethod
    def get_insance(cls, name: Optional[str] = None):
        """Return singleton instance of class. Use this instead of direct instantiation of settings"""
        name = name or f'{cls.__module__}.{cls.__name__}'
        if name not in cls.__setting_per_name__:
            path = get_settings_path(name)
            cls.__setting_per_name__[name] = cls(path)
        return cls.__setting_per_name__[name]

    def __setattr__(self, key, value):
        if key in self.__annotations__ and 'data' in self.__dict__:
            self.__setitem__(key, value)
        return super(BaseSettings, self).__setattr__(key, value)

    def __getattr__(self, item):  # type: ignore
        if item in self.__annotations__ and 'data' in self.__dict__:
            return self.data[item]
        return object.__getattribute__(self, item)


class EDPSettings(BaseSettings):
    """Elite Dangerous Platform application settings"""
    user_id: str = str(uuid.uuid4())
    plugin_dir: Path = config.BASE_DIR / 'plugins'
    enable_error_reports: bool = True

    @property
    def journal_dir(self) -> Path:
        """
        Journal dir path. If not set, gets default journal path on windows from app data.

        If not available or not on windows, dir inside edp.config.LOCALAPPDATA_DIR will be created.
        """
        if 'journal_dir' not in self:
            self['journal_dir'] = get_default_journal_path() or config.LOCALAPPDATA_DIR / 'journal'
        return self['journal_dir']

    @journal_dir.setter
    def journal_dir(self, value: Union[str, Path]):
        self['journal_dir'] = value


class SimpleSettings(BaseSettings):
    """Utility class to be used as persistent dict object"""
