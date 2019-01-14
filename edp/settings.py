import functools
import pathlib
from typing import Optional

from edp.utils import winpaths


class Settings:
    base_dir = pathlib.Path(__file__).parent.parent

    @property
    def plugin_dir(self) -> pathlib.Path:
        return self.base_dir / 'plugins'

    @property  # type: ignore
    @functools.lru_cache()
    def journal_dir(self) -> pathlib.Path:
        saved_games_dir = winpaths.get_known_folder_path(winpaths.KNOWN_FOLDERS.SavedGames)
        return saved_games_dir / 'Frontier Developments' / 'Elite Dangerous'

    @property
    def edsm_api_key(self) -> Optional[str]:
        return None

    @property
    def edsm_commander_name(self) -> Optional[str]:
        return None
