import base64
import datetime
import hashlib
import json
import logging
import os
import threading
from typing import Union, Optional, NamedTuple

import requests
from PyQt5 import QtWebEngineWidgets, QtCore, QtWidgets
from urlpath import URL

from edp import config, plugins, signalslib, signals, journal
from edp.gui.forms import main_window
from edp.gui.forms.settings_window import VLayoutTab
from edp.settings import BaseSettings
from edp.utils import catcherr

AUTH_URL = URL('https://auth.frontierstore.net')
API_URL = URL('https://companion.orerve.net')

base64url = lambda b: base64.urlsafe_b64encode(b).decode().replace('=', '')
generate_verifier = lambda: base64url(os.urandom(35))
generate_challenge = lambda verifier: base64url(hashlib.sha256(verifier.encode()).digest())
generate_state = lambda: base64url(os.urandom(8))

logger = logging.getLogger(__name__)

access_token_set_signal = signalslib.Signal('capi access token set', access_token=str)
login_required_signal = signalslib.Signal('capi login required')
refresh_required_signal = signalslib.Signal('capi token refresh required')
market_info_signal = signalslib.Signal('capi market info signal', data=dict)
profile_info_signal = signalslib.Signal('capi profile info signal', data=dict)
shipyard_info_signal = signalslib.Signal('capi shipyard info signal', data=dict)


class CapiException(Exception):
    pass


class LoginRequired(CapiException):
    pass


class RefreshRequired(CapiException):
    pass


class TokenInfo(NamedTuple):
    access_token: str
    refresh_token: str
    expires_in: datetime.datetime

    @classmethod
    def from_data(cls, data: dict) -> 'TokenInfo':
        return cls(
            access_token=data['access_token'],
            refresh_token=data['refresh_token'],
            expires_in=datetime.datetime.now() + datetime.timedelta(seconds=data['expires_in'])
        )


def build_authorization_url(client_id: str, redirect_url: Union[str, URL], state: str, challenge: str) -> URL:
    return (AUTH_URL / 'auth').with_query(
        response_type='code',
        audience='frontier',
        scope='capi',
        client_id=client_id,
        code_challenge=challenge,
        code_challenge_method='S256',
        state=state,
        redirect_uri=str(redirect_url)
    )


class CapiSettings(BaseSettings):
    enabled: bool = True
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[datetime.datetime] = None


class CapiAuthWindow(QtWebEngineWidgets.QWebEngineView):
    REDIRECT_URL: str = 'http://local/redirect_url'

    on_redirect_url = QtCore.pyqtSignal(URL)

    def __init__(self):
        super(CapiAuthWindow, self).__init__()
        self.setWindowTitle(config.APPNAME_FRIENDLY + 'companion API login window')
        self.urlChanged.connect(self.on_url_changed)

    def show(self, auth_url: URL):
        logger.info(f'Loading auth url: {auth_url}')
        self.load(QtCore.QUrl(str(auth_url)))
        super(CapiAuthWindow, self).show()

    @catcherr
    def on_url_changed(self, url: QtCore.QUrl):
        logger.debug(f'on_url_changed({url.toString()})')
        if url.toString().startswith(self.REDIRECT_URL):
            self.on_redirect_url.emit(URL(url.toString()))
            self.close()


class CapiSettingsTabWidget(VLayoutTab):
    friendly_name = 'Companion API'

    def __init__(self, manager: 'CapiManager'):
        self._manager = manager
        self._status_label = QtWidgets.QLabel('Status: unknown')

        super(CapiSettingsTabWidget, self).__init__()

        access_token_set_signal.bind_nonstrict(self.update_status_label)
        login_required_signal.bind_nonstrict(self.update_status_label)
        refresh_required_signal.bind_nonstrict(self.update_status_label)

    def update_status_label(self, *args, **kwargs):
        if self._manager.state.is_has_access_token:
            self._status_label.setText('Status: OK')
            self._status_label.setStyleSheet('background-color: rgb(85, 170, 0);')  # green
        elif self._manager.state.is_refresh_required:
            self._status_label.setText('Status: token refresh required')
            self._status_label.setStyleSheet('background-color: rgb(255, 255, 127);')  # yellow
        elif self._manager.state.is_login_required:
            self._status_label.setText('Status: login required')
            self._status_label.setStyleSheet('background-color: rgb(255, 0, 0);')  # red

    def get_settings_links(self):
        settings = CapiSettings.get_insance()

        yield self.link_checkbox(settings, 'enabled', 'Enabled')

        layout = QtWidgets.QHBoxLayout()
        button = QtWidgets.QPushButton('Login')
        button.clicked.connect(lambda *args, **kwargs: catcherr(self._manager.show_login_window)())
        layout.addWidget(button)
        self.update_status_label()
        layout.addWidget(self._status_label)
        layout.addStretch(1)
        yield layout


class CapiState:
    class STATES:
        LOGIN_REQUIRED = 0
        HAS_ACCESS_TOKEN = 1
        REFRESH_REQUIRED = 2

    STATE_FLOW = {
        STATES.LOGIN_REQUIRED: (STATES.HAS_ACCESS_TOKEN,),
        STATES.HAS_ACCESS_TOKEN: (STATES.REFRESH_REQUIRED,),
        STATES.REFRESH_REQUIRED: (STATES.LOGIN_REQUIRED, STATES.HAS_ACCESS_TOKEN)
    }

    def __init__(self):
        self._settings = CapiSettings.get_insance()

        if self._settings.access_token:
            self._state = self.STATES.HAS_ACCESS_TOKEN
        elif self._settings.refresh_token:
            self._state = self.STATES.REFRESH_REQUIRED
        else:
            self._state = self.STATES.LOGIN_REQUIRED

    def set_state(self, state):
        if state not in self.STATE_FLOW[self._state] and state != self._state:
            raise ValueError(f'Invalid state transition: {self._state} -> {state}')
        self._state = state

    @property
    def is_login_required(self):
        return self._state == self.STATES.LOGIN_REQUIRED

    @property
    def is_refresh_required(self):
        return self._state == self.STATES.REFRESH_REQUIRED

    @property
    def is_has_access_token(self):
        return self._state == self.STATES.HAS_ACCESS_TOKEN


class CapiManager:
    MAX_RETRIES = 2

    def __init__(self):
        self._settings = CapiSettings.get_insance()
        if self._settings.expires_in and self._settings.access_token \
                and self._settings.expires_in < datetime.datetime.now():
            self._settings.access_token = None

        self.state = CapiState()

        self._window = None

        self._session = requests.Session()
        self._session.headers['User-Agent'] = config.USERAGENT

        self._refresh_token_lock = threading.Lock()

    def _generate_oauth_creds(self):
        self._cred_state = generate_state()
        self._cred_verifier = generate_verifier()
        self._cred_challenge = generate_challenge(self._cred_verifier)

    @catcherr
    def _on_redirect_url(self, url: URL):
        code: str = url.form.get_one('code')
        if not code:
            logger.error(f'Got empty code in redirect url: {url}')
            return

        token_info = self._exchange_code(code)
        if not token_info:
            logger.error('Failed to exchange code')
            return

        self._set_token(token_info)

    def _set_token(self, token: TokenInfo):
        self._settings.access_token = token.access_token
        self._settings.refresh_token = token.refresh_token
        self._settings.expires_in = token.expires_in
        self._set_has_access_token()

    def _set_has_access_token(self):
        self.state.set_state(CapiState.STATES.HAS_ACCESS_TOKEN)
        access_token_set_signal.emit(access_token=self._settings.access_token)
        self._session.headers['Authorization'] = f'Bearer {self._settings.access_token}'

    def _set_refresh_required(self):
        self.state.set_state(CapiState.STATES.REFRESH_REQUIRED)
        refresh_required_signal.emit()

    def _set_login_required(self):
        self.state.set_state(CapiState.STATES.LOGIN_REQUIRED)
        login_required_signal.emit()
        self._session.headers.pop('Authorization', None)

    def _exchange_code(self, code: str) -> Optional[TokenInfo]:
        try:
            response = self._session.post(AUTH_URL / 'token', timeout=10, json={
                "grant_type": "authorization_code",
                "client_id": config.CAPI_CLIENT_ID,
                "code_verifier": self._cred_verifier,
                "code": code,
                "redirect_uri": self._window.REDIRECT_URL,
            })
            response.raise_for_status()
            data = response.json()
            return TokenInfo.from_data(data)
        except:
            logger.exception(f'Error exchanging code for token: '
                             f'{locals()["response"].text if "response" in locals() else "<no response>"}')
            return None

    def _refresh_token(self, refresh_token: str) -> Optional[TokenInfo]:
        try:
            response = self._session.post(AUTH_URL / 'token', timeout=10, json={
                'grant_type': 'refresh_token',
                'client_id': config.CAPI_CLIENT_ID,
                'refresh_token': refresh_token,
            })
            response.raise_for_status()
            data = response.json()
            return TokenInfo.from_data(data)
        except:
            logger.exception(f'Error refreshing token: '
                             f'{locals()["response"].text if "response" in locals() else "<no response>"}')
            return None

    def show_login_window(self):
        if not self._window:
            self._window = CapiAuthWindow()
            self._window.on_redirect_url.connect(self._on_redirect_url)

        self._generate_oauth_creds()
        auth_url = build_authorization_url(
            client_id=config.CAPI_CLIENT_ID,
            redirect_url=self._window.REDIRECT_URL,
            state=self._cred_state,
            challenge=self._cred_challenge
        )
        self._window.show(auth_url)

    def do_refresh(self):
        if not self._settings.refresh_token:
            raise ValueError('Refresh token not set')

        logger.debug('Refreshing access token')

        with self._refresh_token_lock:
            token_info = self._refresh_token(self._settings.refresh_token)

        if not token_info:
            logger.error('Failed to refresh token')
            logger.warning('Login required')
            self._settings.access_token = None
            self._set_login_required()
            return

        self._set_token(token_info)
        return True

    def do_query(self, endpoint: str) -> dict:
        exc: Optional[Exception] = None
        for retry_number in range(self.MAX_RETRIES):
            try:
                return self._do_query(endpoint)
            except json.JSONDecodeError as e:
                exc = e
                logger.warning(f'JSONDecodeError while requesting {endpoint}')
                logger.debug('Retrying')
                continue
            except requests.HTTPError as e:
                exc = e
                logger.warning(f'HTTPError while requesting {endpoint}')
                if e.response.status_code == 401:
                    logger.debug('Unauthorized, refreshing token')
                    if self.do_refresh():
                        logger.info('Refreshed token, retrying request')
                        continue
                    else:
                        logger.warning('Failed to refresh token, require login')
                        self._set_login_required()
                        raise LoginRequired('Failed to refresh access token, login required')
                if e.response.status_code >= 500:
                    logger.warning('ServerError from capi')
                    raise
            except Exception as e:
                exc = e
                logger.exception(f'Unhandled exception while requesting {endpoint}')
                logger.debug('Retrying')
                continue

        if exc:
            raise exc
        else:
            raise ValueError('No response and no exception')

    def _do_query(self, endpoint: str) -> dict:
        response = self._session.get(str(API_URL / endpoint))
        try:
            response.raise_for_status()
        except requests.HTTPError:
            logger.warning(f'HTTPError while calling capi "{endpoint}": {response.text}', exc_info=True)
            raise
        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.warning(f'JSONDecodeError while calling capi "{endpoint}": {response.text}', exc_info=True)
            raise
        return data

    def get_profile(self) -> dict:
        return self.do_query('profile')

    def get_market(self) -> dict:
        return self.do_query('market')

    def get_shipyard(self) -> dict:
        return self.do_query('shipyard')

    def get_communitygoals(self) -> dict:
        return self.do_query('communitygoals')


class CapiPlugin(plugins.BasePlugin):
    friendly_name = 'Companion API'

    def __init__(self):
        super(CapiPlugin, self).__init__()

        self._manager = CapiManager()
        self.settings = CapiSettings.get_insance()

    def is_enalbed(self):
        return self.settings.enabled

    def get_settings_widget(self):
        return CapiSettingsTabWidget(self._manager)

    @plugins.scheduled(120)
    def do_refresh_token(self):
        if self._manager.state.is_refresh_required:
            self._manager.do_refresh()

    @plugins.bind_signal(journal.journal_event_signal)
    def on_journal_event(self, event: journal.Event):
        if not self._manager.state.is_has_access_token:
            return

        try:
            if event.name == 'Docked':
                services = event.data.get('StationServices', [])
                if 'Commodities' in services:
                    data = self._manager.get_market()
                    if event.data.get('MarketID', None) == data.get('id', None):
                        market_info_signal.emit(data=data)
                    else:
                        logger.warning('MarketID of docked event and capi does not match')
                if 'Shipyard' in services:
                    data = self._manager.get_shipyard()
                    if event.data.get('MarketID', object()) == data.get('id', object()):
                        shipyard_info_signal.emit(data=data)
                    else:
                        logger.warning('MarketID of docked event and capi does not match')
        except:
            logger.exception('Failed to get CAPI data')

    @plugins.bind_signal(signals.init_complete)
    def on_init_complete(self):
        if self._manager.state.is_refresh_required:
            self._manager.do_refresh()

    @plugins.bind_signal(main_window.main_window_created_signal)
    def on_window_created(self, window: main_window.MainWindow):
        if self._manager.state.is_login_required:
            window.on_showed.connect(lambda *args, **kwargs: catcherr(self._manager.show_login_window)())
