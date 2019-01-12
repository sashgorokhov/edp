from PyQt5.uic import compileUi

import pathlib

GUI_DIR = pathlib.Path(__file__).parent.parent / 'edp' / 'gui'
UI_DIR: pathlib.Path = GUI_DIR / 'ui'
COMPILED_DIR: pathlib.Path = GUI_DIR / 'compiled'
print(GUI_DIR)

for path in UI_DIR.glob('*.ui'):
    target_path = COMPILED_DIR / path.with_suffix('.py').name
    print(f'Compiling {path.name} to {target_path}')
    compileUi(str(path), target_path.open('w'))
