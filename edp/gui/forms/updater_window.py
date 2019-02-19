"""Window that shows new release information and able to download and install msi package"""
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List

import requests
from PyQt5 import QtWidgets, QtCore
from urlpath import URL

from edp import config
from edp.gui.compiled.updater_window import Ui_Form
from edp.utils import catcherr

logger = logging.getLogger(__name__)


class ReleaseDownloaderThread(QtCore.QThread):
    """Downloads and installs msi github asset"""
    download_progress = QtCore.pyqtSignal(int)
    download_finished = QtCore.pyqtSignal()
    install_finished = QtCore.pyqtSignal()

    def __init__(self, asset_info: dict):
        super(ReleaseDownloaderThread, self).__init__()
        self._asset_info = asset_info

    # pylint: disable=no-self-use
    def run(self):
        """Download and install msi in background thread"""
        url = URL(self._asset_info['browser_download_url'])

        with tempfile.TemporaryDirectory() as tempdir:
            tempdir = Path(tempdir)
            installer_path = tempdir / url.name
            self.download_to(url, installer_path)
            self.download_finished.emit()
            self.install(installer_path.absolute())
            self.install_finished.emit()

    def install(self, path: Path):
        """Install msi package at path"""
        logger.debug(f'Installing {path}')
        status, output = subprocess.getstatusoutput(f'{path} /passive')
        if status != 0:
            logger.error(output)
        elif output.strip():
            logger.debug(output)

    def download_to(self, url: URL, path: Path):
        """Download file from url to path with progress reporting"""
        response = requests.get(url, stream=True)

        with path.open('wb') as f:
            progress = 0
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)
                progress += len(chunk)
                self.download_progress.emit(progress)


def get_default_installer(asset_list: List[dict]) -> dict:
    """Return asset with default msi installer"""
    for asset in asset_list:
        if asset.get('name', '').endswith('.msi'):
            return asset
    raise ValueError('Asset with DEFAULT_INSTALLER label not found')


class UpdaterWindow(Ui_Form, QtWidgets.QWidget):
    """Window that shows new release information"""
    def __init__(self, release_info: dict):
        super(UpdaterWindow, self).__init__()
        self.setupUi(self)

        self.version_label.setText(f'v{config.VERSION}')
        self.release_version_label.setText(f'{release_info["tag_name"]}')
        self.release_name_label.setText(f'<a href=\"{release_info["html_url"]}\">{release_info["name"]}</a>')
        self.download_progess_bar.hide()
        self.install_label.hide()

        self.skip_button.clicked.connect(self.close)
        self.install_button.clicked.connect(self.install_button_clicked)

        asset_info = get_default_installer(release_info.get('assets', []))

        logger.debug(f'Update asset is: {asset_info}')

        self.download_progess_bar.setMaximum(asset_info['size'])
        self.download_progess_bar.setValue(0)

        self._downloader_thread = ReleaseDownloaderThread(asset_info)
        self._downloader_thread.download_progress.connect(self.on_download_progress)
        self._downloader_thread.download_finished.connect(self.on_download_finished)
        self._downloader_thread.install_finished.connect(self.on_install_finished)

    @QtCore.pyqtSlot(int)
    def on_download_progress(self, progress: int):
        """Update download_progess_bar value"""
        self.download_progess_bar.setValue(progress)

    @QtCore.pyqtSlot()
    def on_download_finished(self):
        """Hive download progress bar and show install label"""
        logger.debug('Download finished')
        self.download_progess_bar.hide()
        self.install_label.show()

    # pylint: disable=no-self-use
    @QtCore.pyqtSlot()
    @catcherr
    def on_install_finished(self):
        """Quit qt application when install finished"""
        logger.debug('Install finished')
        app = QtWidgets.QApplication.instance()
        app.quit()

    # pylint: disable=unused-argument
    @catcherr
    def install_button_clicked(self, *args, **kwargs):
        """Start downloader thread, hide install buttons and show download progress bar"""
        logger.debug('Downloading msi')
        self.download_progess_bar.show()
        self.install_button.hide()
        self.skip_button.hide()
        self._downloader_thread.start()
