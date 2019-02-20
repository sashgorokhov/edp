"""
Python style makefile.

Contains various helper shortcuts as well as some deploy and build routines.

- SENTRY_DSN env var must be set to be injected into build secrets file.
- GITHUB_API_TOKEN env var required to create github release.
"""
import json
import os
import re
import shutil
from pathlib import Path
from typing import Optional, List, Sequence

import requests
from invoke import Context, Exit, task
from urlpath import URL

BASE_DIR = Path(__file__).parent
GUI_DIR: Path = BASE_DIR / 'edp' / 'gui'
UI_DIR: Path = GUI_DIR / 'ui'
COMPILED_DIR: Path = GUI_DIR / 'compiled'

UPX_URL = 'https://github.com/upx/upx/releases/download/v3.95/upx-3.95-win64.zip'
LOCAL_TEMP_DIR: Path = BASE_DIR / '.tmp'
UPX_DIR: Path = LOCAL_TEMP_DIR / 'upx'
TARGET: Path = BASE_DIR / 'elite_dangerous_platform.py'
DIST_DIR: Path = BASE_DIR / 'dist' / TARGET.stem
BUILD_DIR: Path = BASE_DIR / 'build'
BUILD_TARGET_DIR: Path = BUILD_DIR / TARGET.stem
DIST_ZIP: Path = DIST_DIR.with_suffix('.zip')
EXE_FILE: Path = DIST_DIR / TARGET.with_suffix('.exe').name
DIST_DATA_FILE: Path = DIST_DIR / 'dist.json'
ASSETS_DIR: Path = BASE_DIR / 'assets'

WIX_URL = URL('https://github.com/wixtoolset/wix3/releases/download/wix3111rtm/wix311-binaries.zip')
WIX_DIR: Path = LOCAL_TEMP_DIR / WIX_URL.stem

WIX_MSI: Path = BASE_DIR / 'dist' / 'elite_dangerous_platform.msi'

LOCAL_TEMP_DIR.mkdir(parents=True, exist_ok=True)

GITHUB_API_TOKEN: Optional[str] = os.environ.get('GITHUB_API_TOKEN')
SENTRY_DSN: Optional[str] = os.environ.get('SENTRY_DSN')

COPY_TO_DIST_FILES: Sequence[Path] = (
    BASE_DIR / 'VERSION',
    BASE_DIR / 'LICENSE',
    BASE_DIR / 'LICENSE.rtf',
)


def fetch_wix(c):
    """Download and extrax wix toolset binaries"""
    WIX_ZIP = LOCAL_TEMP_DIR / WIX_URL.name
    if WIX_ZIP.exists():
        WIX_ZIP.unlink()
    print(f'Fetching WIX form {WIX_URL}')
    response = requests.get(WIX_URL, stream=True)
    with WIX_ZIP.open('wb') as f:
        for chunk in response.iter_content(chunk_size=None):
            f.write(chunk)
    c.run(f'powershell Expand-Archive -Force -Path {WIX_ZIP} -DestinationPath {WIX_DIR}')
    print(f'WIX now is in {WIX_DIR}')


@task
def pyuic(c):  # pylint: disable=unused-argument
    """
    Run UI compiler

    Compiles *.ui files found in :py:data:UI_DIR into .py files in :py:data:COMPILED_DIR
    """
    from PyQt5.uic import compileUi

    for path in UI_DIR.glob('*.ui'):
        target_path: Path = COMPILED_DIR / path.with_suffix('.py').name
        print(f'Compiling {path.name} to {target_path}')
        compileUi(str(path), target_path.open('w'), import_from='edp.gui.compiled', from_imports=True,
                  resource_suffix='')


@task()
def pyrcc(c):
    """Compiles *.qrc files found in ASSETS_DIR into .py files in COMPILED_DIR"""
    from PyQt5.pyrcc_main import processResourceFile

    for path in ASSETS_DIR.glob('*.qrc'):
        target_path = COMPILED_DIR / path.with_suffix('.py').name
        print(f'Compiling {path.name} to {target_path}')
        processResourceFile([str(path)], str(target_path), False)


def gethashsum(path, md5=False, sha1=False):
    """
    Return file md5/sha1 hashsum
    """
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
        raise ValueError('No hash is used')

    with path.open('rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            hashobj.update(data)

    hashsum = hashobj.hexdigest()
    return hashsum


def fetch_upx(c: Context):
    """
    Download UPX binary and store it in temporary directory
    """
    global UPX_DIR  # pylint: disable=global-statement

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


@task()
def mypy(c):
    """Run mypy type checker on whole project"""
    c.run('mypy edp')


@task()
def pylint(c):
    """Run pylint style checker on whole project"""
    c.run('pylint -j 0 edp')


@task()
def unittests(c):
    """Run all unittests"""
    c.run('pytest -sv tests')


@task(mypy, pylint, unittests)
def test(c):  # pylint: disable=unused-argument
    """
    Task to group all project checks into one task
    """


@task()
def build(c):
    """
    Build executable file
    """
    if not SENTRY_DSN:
        print('SENTRY_DSN is not set!')
    if not UPX_DIR.exists():
        fetch_upx(c)

    c.run(f'pyinstaller -w -y --clean --log-level WARN '
          f'--upx-dir {UPX_DIR} '
          f'-i {ASSETS_DIR / "app_icon.ico"} '
          f'{TARGET}')
    for path in COPY_TO_DIST_FILES:
        shutil.copy(str(path), str(DIST_DIR / path.relative_to(BASE_DIR)))

    DIST_DATA_FILE.write_text(json.dumps({
        'SENTRY_DSN': SENTRY_DSN
    }))


@task(build)
def dist(c):
    """
    Build executable file and create distributable zip
    """
    print(f'Create dist zip in {DIST_ZIP}')
    c.run(f'powershell Compress-Archive -Force -Path {DIST_DIR} -DestinationPath {DIST_ZIP}')


# noinspection PyPep8Naming
@task()
def build_msi(c):
    """Build msi installer with wix"""
    if not WIX_DIR.exists():
        fetch_wix(c)

    CANDLE = WIX_DIR / 'candle.exe'
    LIGHT = WIX_DIR / 'light.exe'
    HEAT = WIX_DIR / 'heat.exe'

    MAIN_WXS = BASE_DIR / 'elite_dangerous_platform.wxs'
    MAIN_OBJ = (BUILD_DIR / TARGET.stem).with_suffix('.wixobj')
    DIST_DIR_FILES_WXS = BUILD_DIR / 'dist_files.wxs'
    DIST_DIR_FILES_OBJ = (BUILD_DIR / DIST_DIR_FILES_WXS.stem).with_suffix('.wixobj')

    version_bits = read_version()

    print(f'Create msi installer in {WIX_MSI}')

    print('\t Lint wix xml')
    c.run(f'{WIX_DIR / "wixcop.exe"} -nologo {MAIN_WXS}')

    print('\t Extract dist dir files into xml')
    c.run(f'{HEAT} dir {DIST_DIR} -var var.DistDir -dr InstallDir -nologo '
          f'-gg -g1 -suid -srd -sfrag -sw5150 -template fragment -cg DIST_DIR_FILES -out {DIST_DIR_FILES_WXS}')

    print(f'\t Compile main wix xml into obj')
    c.run(f'{CANDLE} -nologo -arch x64 -dVersion={".".join(map(str, version_bits))} -dDistDir={DIST_DIR} '
          f'-dAssetsDir={ASSETS_DIR} '
          f'-ext WixUIExtension -ext WixUtilExtension -o {MAIN_OBJ} {MAIN_WXS}', hide='out')

    print(f'\t Compile dist files wix xml into obj')
    c.run(f'{CANDLE} -nologo -arch x64 -dDistDir={DIST_DIR} -o {DIST_DIR_FILES_OBJ} {DIST_DIR_FILES_WXS}', hide='out')

    print(f'\t Compile wix objects into {WIX_MSI}')
    c.run(f'{LIGHT} -nologo -cultures:en-us -pdbout {str(BUILD_DIR / WIX_MSI.stem) + ".wixpdb"} -sw1076 '
          f'-ext WixUIExtension -ext WixUtilExtension -o {WIX_MSI} -reusecab -cc {BUILD_DIR / "cabcache"} '
          f'{MAIN_OBJ} {DIST_DIR_FILES_OBJ}', warn=True)


@task(test, build, dist, build_msi)
def release(c):
    """
    Create gitgub release.

    This creates github release with dist zip uploaded as asset,
    simple template with changelog of commits from last release.
    Also calculates hashsums of zip and exe files.
    """
    from edp.utils import github
    if not GITHUB_API_TOKEN:
        raise Exit('GITHUB_API_TOKEN is not set')

    md5_exe = gethashsum(EXE_FILE, md5=True)
    md5_zip = gethashsum(DIST_ZIP, md5=True)
    sha1_exe = gethashsum(EXE_FILE, sha1=True)
    sha1_zip = gethashsum(DIST_ZIP, sha1=True)

    commits_lines: List[str] = commits_before_tag(c)
    commits_info = [cl.split(' ', 1) for cl in commits_lines]
    changelog = '\n'.join(f'- {sha} {message}' for sha, message in commits_info)

    body = f"""
### Changelog:

{changelog}

### Hashsums:

MD5 exe: `{md5_exe}`

MD5 zip: `{md5_zip}`

SHA1 exe: `{sha1_exe}`

SHA1 zip: `{sha1_zip}`

---
Generated by 🤖
    """

    version = '%s.%s.%s' % read_version()

    api = github.GithubApi(GITHUB_API_TOKEN)
    data = api.create_release('sashgorokhov', 'edp',
                              f'v{version}',
                              f'Elite Dangerous Platform v{version}',
                              body, draft=True)
    upload_url = re.sub('{.*?}', '', data['upload_url'])
    print('Uploading assets')
    api.upload_asset(upload_url, DIST_ZIP, 'application/zip', f'EDP-{version}-win64.zip')
    api.upload_asset(upload_url, WIX_MSI, 'application/x-msi', f'EDP-{version}-win64.msi')
    print(data['html_url'])


@task()
def freeze(c):
    """
    Write all project requirements versions into constraints file

    This will create a temporary clean virtualenv, install there ALL requirements (requierements-dev)
    and store pip freeze results in constraints.txt file
    """
    VENV_DIR: Path = LOCAL_TEMP_DIR / 'env'
    PIP: Path = VENV_DIR / 'Scripts' / 'pip.exe'
    c.run(f'virtualenv {VENV_DIR}')
    c.run(f"{PIP} install -Ur requirements-dev.txt")
    c.run(f"{PIP} freeze > constraints.txt")
    shutil.rmtree(VENV_DIR)


def read_version():
    """Read and parse VERSION file"""
    version = (BASE_DIR / 'VERSION').read_text()
    major, minor, patch = tuple(map(int, version.split('.')))
    return major, minor, patch


def commit_version(c):
    """Commit and push changed version"""
    version = '%s.%s.%s' % read_version()
    c.run(f'git commit -m "Update VERSION to {version}" {BASE_DIR / "VERSION"}', hide='stdout')
    c.run(f'git tag -a -m "v{version}" "v{version}"', hide='stdout')
    c.run(f'git push --all', hide='stdout')


@task()
def bump_major(c):
    """Bump major version part"""
    major, _, _ = read_version()
    (BASE_DIR / 'VERSION').write_text('.'.join(map(str, (major + 1, 0, 0))))
    commit_version(c)


@task()
def bump_minor(c):
    """Bump minor version part"""
    major, minor, _ = read_version()
    (BASE_DIR / 'VERSION').write_text('.'.join(map(str, (major, minor + 1, 0))))
    commit_version(c)


@task()
def bump_patch(c):
    """Bump patch version part"""
    major, minor, patch = read_version()
    (BASE_DIR / 'VERSION').write_text('.'.join(map(str, (major, minor, patch + 1))))
    commit_version(c)


@task()
def commits_before_tag(c):
    """
    Return list of commits between last and one before last tags.
    """
    all_tags = list(filter(None, (t.strip() for t in c.run('git tag', hide=True).stdout.split('\n'))))
    previous_tag = all_tags[-2]
    last_tag = all_tags[-1]
    result = c.run(f'git log --pretty=oneline {previous_tag}..{last_tag}', hide='stdout').stdout
    return list(filter(None, result.split('\n')))


@task()
def docs(c):
    """Build sphinx docs"""
    c.run('sphinx-build -v docs/src/ docs/')


@task(docs)
def update_docs(c):
    """Build sphinx docs and commit and push"""
    c.run(f'git commit -m "Update docs" .')
    c.run(f'git push --all')
