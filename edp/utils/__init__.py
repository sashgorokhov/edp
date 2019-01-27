import logging
from pathlib import Path
from typing import Optional, Dict, Mapping, Sequence, Iterator, TypeVar

logger = logging.getLogger(__name__)


def is_dict_subset(source: dict, subset: dict) -> bool:
    for key, value in subset.items():
        if key not in source:
            return False
        if source[key] != subset[key]:
            return False

    return True


def get_default_journal_path() -> Optional[Path]:  # pragma: no cover
    try:
        from edp.utils import winpaths
        saved_games_dir = winpaths.get_known_folder_path(winpaths.KNOWN_FOLDERS.SavedGames)
        journal_dir = saved_games_dir / 'Frontier Developments' / 'Elite Dangerous'
    except:
        logger.exception('Failed to get default journal path')
        return None
    return journal_dir


def catcherr(func):
    def decor(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            logger.exception(f'Error calling: {func}')

    return decor


def subset(d: Mapping, *keys: str, strict=False) -> Dict:
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
    indexes = list(range(len(l)))[::5]

    for start in indexes:
        yield l[start: start + size]


def has_keys(d: dict, *keys: str) -> bool:
    return set(keys).issubset(set(d.keys()))
