from pathlib import Path

import invoke

BASE_DIR: Path = Path(__file__).parent
GUI_DIR: Path = BASE_DIR / 'edp' / 'gui'
UI_DIR: Path = GUI_DIR / 'ui'
COMPILED_DIR: Path = GUI_DIR / 'compiled'


@invoke.task
def pyuic(c):
    from PyQt5.uic import compileUi

    for path in UI_DIR.glob('*.ui'):
        target_path = COMPILED_DIR / path.with_suffix('.py').name
        print(f'Compiling {path.name} to {target_path}')
        compileUi(str(path), target_path.open('w'))
