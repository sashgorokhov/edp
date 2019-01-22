import json
import os
import sys
from pathlib import Path

# If running from pycharm python console it will be something in pycharm/helpers/pydev....
from typing import Optional

EXECUTABLE_PATH: Path = Path(sys.argv[0]).absolute()

FROZEN: bool = getattr(sys, 'frozen', False)

if FROZEN:
    BASE_DIR: Path = EXECUTABLE_PATH.parent
else:
    BASE_DIR = Path(__file__).parents[1]

LOCALAPPDATA_DIR: Path = Path(os.environ.get('LOCALAPPDATA', BASE_DIR / 'LOCALAPPDATA'))
APP_DATA_DIR: Path = LOCALAPPDATA_DIR / 'Elite Dangerous Platform'
SETTINGS_DIR: Path = APP_DATA_DIR / 'Settings'
LOGS_DIR: Path = APP_DATA_DIR / 'Logs'
DIST_FILE: Path = BASE_DIR / 'dist.json'

VERSION_PATH: Path = BASE_DIR / 'VERSION'
VERSION: str = VERSION_PATH.read_text().strip() if VERSION_PATH.exists() else '0.0.0'
APPNAME_SHORT: str = 'EDP'
APPNAME_LONG: str = 'EliteDangerousPlatform'
APPNAME_FRIENDLY: str = 'Elite Dangerous Platform'

USERAGENT: str = f'{APPNAME_LONG}-v{VERSION}'

SENTRY_DSN: Optional[str] = None

# Some simple secret data injection
if FROZEN and DIST_FILE.exists():
    with DIST_FILE.open('r') as f:
        try:
            data = json.load(f)

            SENTRY_DSN = data.get('SENTRY_DSN')
        except Exception as e:
            print(f'Error reading dist file: {e}')
