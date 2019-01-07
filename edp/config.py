import pathlib

BASE_DIR = pathlib.Path(__file__).parent.parent

PLUGIN_DIR = BASE_DIR / 'plugins'

JOURNAL_DIR: pathlib.Path = None


def init():
    global JOURNAL_DIR
    from edp.utils import winpaths

    JOURNAL_DIR = winpaths.get_known_folder_path(winpaths.KNOWN_FOLDERS.SavedGames) / 'Frontier Developments' / 'Elite Dangerous'
