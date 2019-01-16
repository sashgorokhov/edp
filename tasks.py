import shutil
from pathlib import Path

import invoke
import requests
from invoke import Context

BASE_DIR: Path = Path(__file__).parent
GUI_DIR: Path = BASE_DIR / 'edp' / 'gui'
UI_DIR: Path = GUI_DIR / 'ui'
COMPILED_DIR: Path = GUI_DIR / 'compiled'

UPX_URL = 'https://github.com/upx/upx/releases/download/v3.95/upx-3.95-win64.zip'
LOCAL_TEMP_DIR: Path = BASE_DIR / '.tmp'
UPX_DIR: Path = LOCAL_TEMP_DIR / 'upx'
TARGET: Path = BASE_DIR / 'elite_dangerous_platform.py'
DIST_DIR: Path = BASE_DIR / 'dist' / TARGET.stem
DIST_ZIP: Path = DIST_DIR.with_suffix('.zip')
EXE_FILE: Path = DIST_DIR / TARGET.with_suffix('.exe').name

LOCAL_TEMP_DIR.mkdir(parents=True, exist_ok=True)


@invoke.task
def pyuic(c):
    from PyQt5.uic import compileUi

    for path in UI_DIR.glob('*.ui'):
        target_path = COMPILED_DIR / path.with_suffix('.py').name
        print(f'Compiling {path.name} to {target_path}')
        compileUi(str(path), target_path.open('w'))


def gethashsum(path, md5=False, sha1=False):
    import hashlib

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_dir():
        raise IsADirectoryError(path)

    if md5:
        hashobj = hashlib.md5()
    elif sha1:
        hashobj = hashlib.sha1()
    else:
        return

    with path.open('rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            hashobj.update(data)

    hashsum = hashobj.hexdigest()
    return hashsum


def fetch_upx(c: Context):
    global UPX_DIR

    UPX_ZIP = UPX_DIR.with_suffix('.zip')
    if UPX_ZIP.exists():
        UPX_ZIP.unlink()
    print(f'Fetching UPX form {UPX_URL}')
    response = requests.get(UPX_URL, stream=True)
    with UPX_ZIP.open('wb') as f:
        for chunk in response.iter_content(chunk_size=None):
            f.write(chunk)
    c.run(f'powershell Expand-Archive -Force -Path {UPX_ZIP} -DestinationPath {UPX_DIR}')
    UPX_DIR = next(UPX_DIR.iterdir())
    print(f'UPX now is in {UPX_DIR}')


@invoke.task()
def mypy(c):
    c.run('mypy edp')


@invoke.task()
def pylint(c):
    c.run('pylint edp', warn=True)


@invoke.task()
def unittests(c):
    c.run('pytest -sv tests')


@invoke.task(mypy, pylint, unittests)
def test(c):
    pass


@invoke.task
def build(c):
    if not UPX_DIR.exists():
        fetch_upx(c)

    c.run(f'pyinstaller -w -y --clean --log-level WARN --upx-dir {UPX_DIR} {TARGET}')
    shutil.copy(str(BASE_DIR / 'VERSION'), str(DIST_DIR / 'VERSION'))


@invoke.task(test, build)
def dist(c):
    print(f'Create dist zip in {DIST_ZIP}')
    c.run(f'powershell Compress-Archive -Force -Path {DIST_DIR} -DestinationPath {DIST_ZIP}')

    md5_exe = gethashsum(EXE_FILE, md5=True)
    md5_zip = gethashsum(DIST_ZIP, md5=True)
    sha1_exe = gethashsum(EXE_FILE, sha1=True)
    sha1_zip = gethashsum(DIST_ZIP, sha1=True)

    print('MD5 exe:', md5_exe)
    print('MD5 zip:', md5_zip)
    print('SHA1 exe:', sha1_exe)
    print('SHA1 zip:', sha1_zip)


@invoke.task()
def freeze(c):
    VENV_DIR: Path = LOCAL_TEMP_DIR / 'env'
    PIP: Path = VENV_DIR / 'Scripts' / 'pip.exe'
    c.run(f'virtualenv {VENV_DIR}')
    c.run(f"{PIP} install -r requirements-dev.txt")
    c.run(f"{PIP} freeze > constraints.txt")
    shutil.rmtree(VENV_DIR)
