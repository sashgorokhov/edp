import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def is_dict_subset(source: dict, subset: dict) -> bool:
    for key, value in subset.items():
        if key not in source:
            return False
        if source[key] != subset[key]:
            return False

    return True


def get_default_journal_path() -> Optional[Path]:
    try:
        from edp.utils import winpaths
        saved_games_dir = winpaths.get_known_folder_path(winpaths.KNOWN_FOLDERS.SavedGames)
        journal_dir = saved_games_dir / 'Frontier Developments' / 'Elite Dangerous'
    except:
        logger.exception('Failed to get default journal path')
        return None
    return journal_dir
