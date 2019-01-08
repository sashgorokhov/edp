import pathlib
import functools

from edp.utils import winpaths


class Settings:
    base_dir = pathlib.Path(__file__).parent.parent

    @property
    def plugin_dir(self) -> pathlib.Path:
        return self.base_dir / 'plugins'

    @property
    @functools.lru_cache()
    def journal_dir(self) -> pathlib.Path:
        saved_games_dir = winpaths.get_known_folder_path(winpaths.KNOWN_FOLDERS.SavedGames)
        return saved_games_dir / 'Frontier Developments' / 'Elite Dangerous'
