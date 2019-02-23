"""Simple utility functions"""
import datetime
import functools
import logging
import math
from pathlib import Path
from typing import Optional, Dict, Mapping, Sequence, Iterator, TypeVar, Any, Tuple

logger = logging.getLogger(__name__)


def is_dict_subset(source: dict, subset: dict) -> bool:
    """Check if `source` contains all keys from `subset` and those keys values equal"""
    for key in subset.keys():
        if key not in source:
            return False
        if source[key] != subset[key]:
            return False

    return True


def get_default_journal_path() -> Optional[Path]:  # pragma: no cover
    """Return default journal path. On windows it will return saved games directory and ED journal in it."""
    try:
        from edp.utils import winpaths
        saved_games_dir = winpaths.get_known_folder_path(winpaths.KNOWN_FOLDERS.SavedGames)
        journal_dir = saved_games_dir / 'Frontier Developments' / 'Elite Dangerous'
    except:
        logger.exception('Failed to get default journal path')
        return None
    return journal_dir


def catcherr(func):
    """
    Decorator to catch all errors in function. Used to wrap pyqt slots functions
    to avoid application crashes on unexpected exceptions
    """
    def decor(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            logger.exception(f'Error calling: {func}')

    return decor


def dict_subset(d: Mapping, *keys: str, strict=False) -> Dict:
    """
    Get subset dictionary.

    Return new dict with `keys` and their values from `d`

    :param strict: If True then raise KeyError if key not found in `d`
    :raises KeyError: if strict=True and key from `keys` not found in `d`
    """
    result = {}
    for key in keys:
        if key not in d:
            if strict:
                raise KeyError(key)
            else:
                continue
        result[key] = d[key]
    return result


T = TypeVar('T')


def chunked(l: Sequence[T], size: int = 5) -> Iterator[Sequence[T]]:
    """Split `sequence` in `size` parts"""
    indexes = list(range(len(l)))[::size]

    for start in indexes:
        yield l[start: start + size]


def has_keys(d: dict, *keys: str) -> bool:
    """Check if `d` contains all `keys`"""
    return set(keys).issubset(set(d.keys()))


def drop_keys(d: dict, *keys: str) -> dict:
    """Return new dict without `keys`"""
    return {k: v for k, v in d.items() if k not in keys}


def map_keys(d: Dict[str, Any], strict: bool = False, **key_map: str) -> Dict[str, Any]:
    """
    Return new dict where all `d` keys found in `key_map` are renamed to corresponding `key_map` value

    :param strict: If True then raise KeyError if key not found in `d`
    :raises KeyError: if strict=True and key from `keys` not found in `d`
    """
    result = {}
    for key, value in key_map.items():
        if key not in d and strict:
            raise KeyError(key)
        if key in d:
            result[value] = d[key]

    return result


def to_ed_timestamp(dt: datetime.datetime) -> str:
    """
    Convert datetime object to journal format timestamp string
    """
    return dt.isoformat(timespec='seconds') + 'Z'


def from_ed_timestamp(timestamp: str) -> datetime.datetime:
    """
    Convert timestamp string in journal format into datetime object
    """
    return datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')


@functools.lru_cache(200)
def space_distance(point1: Tuple[float, float, float], point2: Tuple[float, float, float]) -> float:
    """
    Calculate distance between two points in three-dimensional space

    :param point1: Tuple[x, y, z]
    :param point2: Tuple[x, y, z]
    """
    return math.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2 + (point2[2] - point1[2])**2)


def version_bits(version: str) -> Tuple[int, int, int]:
    """Return version components (major, minor, patch bits)"""
    major, minor, patch = tuple(map(int, version.lstrip('v').split('.')))
    return major, minor, patch


def is_version_newer(v1: str, v2: str) -> bool:
    """Check if v1 version string is newer than v2 version string"""
    return version_bits(v1) > version_bits(v2)
