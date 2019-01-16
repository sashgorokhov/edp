import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

BASE_DIR: Path = Path(__file__).parents[1]
DIST_DIR = BASE_DIR / 'dist'
UPX_DIR: Optional[Path] = None

for path in Path(__file__).parent.glob('upx*'):  # type: Path
    if path.is_dir():
        UPX_DIR = path
        break
    elif path.suffix == '.exe':
        UPX_DIR = path.parent
        break
else:
    print('Cant find UPX dir')

# Do some silly optimisations
os.environ['PYTHONOPTIMIZE'] = '1'

command = [
    'pyinstaller',
    '-w',  # windowed
    '-y',  # remove output directory without confirmation
    '--clean',
    *((f'--upx-dir', str(UPX_DIR)) if UPX_DIR else tuple()),
    str(BASE_DIR / 'elite_dangerous_platform.py')
]

print(' '.join(command))
subprocess.call(command, stdout=sys.stdout, stderr=sys.stderr)
