import os
import sys
from pathlib import Path

# If running from pycharm python console it will be something in pycharm/helpers/pydev....
EXECUTABLE_PATH: Path = Path(sys.argv[0]).absolute()
BASE_DIR: Path = EXECUTABLE_PATH.parent
LOCALAPPDATA_DIR: Path = Path(os.environ.get('LOCALAPPDATA', BASE_DIR / 'LOCALAPPDATA'))
SETTINGS_DIR: Path = LOCALAPPDATA_DIR / 'Elite Dangerous Platform' / 'Settings'

VERSION_PATH: Path = BASE_DIR / 'VERSION'
VERSION: str = VERSION_PATH.read_text() if VERSION_PATH.exists() else '0.0.1'
