"""
Static configuration.

Should be simple and typed as much as possible, should not import anything from project sources.
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional

EXECUTABLE_PATH: Path = Path(sys.argv[0]).absolute()

FROZEN: bool = getattr(sys, 'frozen', False)

if FROZEN:
    BASE_DIR: Path = EXECUTABLE_PATH.parent
else:
    BASE_DIR = Path(__file__).parents[1]

LOCALAPPDATA_DIR: Path = Path(os.environ.get('LOCALAPPDATA', BASE_DIR / 'LOCALAPPDATA'))
APP_DATA_DIR: Path = LOCALAPPDATA_DIR / 'Elite Dangerous Platform'
PERSONAL_DATA_DIR = LOCALAPPDATA_DIR / 'Elite Dangerous Platform - User Data'
SETTINGS_DIR: Path = PERSONAL_DATA_DIR / 'Settings'
LOGS_DIR: Path = PERSONAL_DATA_DIR / 'Logs'
DIST_FILE: Path = BASE_DIR / 'dist.json'

VERSION_PATH: Path = BASE_DIR / 'VERSION'
VERSION: str = VERSION_PATH.read_text().strip() if VERSION_PATH.exists() else '0.0.0'
APPNAME_SHORT: str = 'EDP'
APPNAME_LONG: str = 'EliteDangerousPlatform'
APPNAME_FRIENDLY: str = 'Elite Dangerous Platform'

USERAGENT: str = f'{APPNAME_LONG}-v{VERSION}'

SENTRY_DSN: Optional[str] = None
DISCORD_CLIENT_ID: str = '537322842291961857'
CAPI_CLIENT_ID: str = '9ff21d7b-c502-45f3-be70-580674751c90'

# Some simple secret data injection
if FROZEN and DIST_FILE.exists():
    with DIST_FILE.open('r') as f:
        try:
            data = json.load(f)

            SENTRY_DSN = data.get('SENTRY_DSN')
        except Exception as e:
            print(f'Error reading dist file: {e}')
