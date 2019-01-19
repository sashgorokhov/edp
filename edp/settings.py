import atexit
import logging
import shelve
from collections import UserDict
from pathlib import Path
from typing import Union, Optional, Dict, TypeVar

from edp import config
from edp.utils import get_default_journal_path

logger = logging.getLogger(__name__)

T = TypeVar('T')


def get_settings_path(name: str) -> Path:
    path = (config.SETTINGS_DIR / name)
    return path.with_name(path.name + '.shelve')


class BaseSettings(UserDict):
    __setting_per_name__: Dict[str, 'BaseSettings'] = {}
    __attributes__ = {}

    def __init__(self, path: Path):
        super(BaseSettings, self).__init__()

        path.parent.mkdir(parents=True, exist_ok=True)

        self._shelve = shelve.open(str(path), writeback=True)
        self.data = self._shelve  # type: ignore

        for key in self.__class__.__annotations__:
            if hasattr(self.__class__, key) and key not in BaseSettings.__dict__:
                value = getattr(self, key)
                self.__class__.__attributes__[key] = value
                self.data.setdefault(key, value)
                delattr(self.__class__, key)
            elif key in self.__class__.__attributes__:
                self.data.setdefault(key, self.__class__.__attributes__[key])

        atexit.register(lambda: self._shelve.close())

    @classmethod
    def get_insance(cls, name: Optional[str] = None):
        name = name or f'{cls.__module__}.{cls.__name__}'
        if name not in cls.__setting_per_name__:
            path = get_settings_path(name)
            cls.__setting_per_name__[name] = cls(path)
        return cls.__setting_per_name__[name]

    def __setattr__(self, key, value):
        if key in self.__annotations__ and 'data' in self.__dict__:
            self.__setitem__(key, value)
        else:
            return super(BaseSettings, self).__setattr__(key, value)

    def __getattr__(self, item):  # type: ignore
        if item in self.__annotations__ and 'data' in self.__dict__:
            return self.data[item]
        else:
            return object.__getattribute__(self, item)


class EDPSettings(BaseSettings):
    plugin_dir: Path = config.BASE_DIR / 'plugins'

    @property
    def journal_dir(self) -> Path:
        if 'journal_dir' not in self:
            self['journal_dir'] = get_default_journal_path() or config.LOCALAPPDATA_DIR / 'journal'
        return self['journal_dir']

    @journal_dir.setter
    def journal_dir(self, value: Union[str, Path]):
        self['journal_dir'] = value


class SimpleSettings(BaseSettings):
    pass
