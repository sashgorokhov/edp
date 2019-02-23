from datetime import datetime, timedelta
from unittest import mock

import pytest
from PyQt5 import QtWebEngineWidgets, QtCore, QtWidgets
from urlpath import URL

from edp.contrib import capi


@pytest.fixture()
@mock.patch('PyQt5.QtWebEngineWidgets.QWebEngineView', autospec=True)
def auth_window(class_mock):
    browser = mock.MagicMock(spec=QtWebEngineWidgets.QWebEngineView)
    class_mock.return_value = browser
    return capi.CapiAuthWindow()


@pytest.mark.parametrize('url', [
    'http://foo.bar',
    URL('http://foo.bar'),
])
def test_auth_window_show(auth_window, url):
    auth_window.show(url)

    auth_window._browser.load.assert_called_once()
    auth_window._browser.show.assert_called_once()


def test_auth_window_on_url_changed(auth_window, process_events):
    m = mock.MagicMock()
    auth_window.on_redirect_url.connect(m)

    url = QtCore.QUrl('http://foo.bar')

    auth_window.on_url_changed(url)
    process_events()

    m.assert_not_called()
    auth_window._browser.close.assert_not_called()


@pytest.mark.parametrize('url', [
    capi.CapiAuthWindow.REDIRECT_URL + '/foo',
    capi.CapiAuthWindow.REDIRECT_URL,
    capi.CapiAuthWindow.REDIRECT_URL + '?code=bar',
])
def test_auth_window_on_url_changed_is_redirect(auth_window, url):
    m = mock.MagicMock()
    auth_window.on_redirect_url.connect(m)

    qurl = QtCore.QUrl(url)

    auth_window.on_url_changed(qurl)

    m.assert_called_once_with(URL(url))
    auth_window._browser.close.assert_called_once()


@pytest.fixture()
def capi_plugin():
    with mock.patch('requests.Session'), \
         mock.patch('PyQt5.QtWebEngineWidgets.QWebEngineView', autospec=True) as class_mock:
        browser = mock.MagicMock(spec=QtWebEngineWidgets.QWebEngineView)
        class_mock.return_value = browser
        yield capi.CapiPlugin()


@pytest.fixture()
def settings_widget(capi_plugin):
    return capi_plugin.get_settings_widget()


@pytest.fixture()
def capi_manager(capi_plugin):
    return capi_plugin._manager


def test_settings_widget_settings_linked(settings_widget):
    assert settings_widget.findChild(QtWidgets.QCheckBox, 'enabled_checkbox') is not None
    assert settings_widget.findChild(QtWidgets.QPushButton, 'login_button') is not None


def test_settings_widget_login_button_shows_login_window(capi_plugin, settings_widget, process_events):
    login_button: QtWidgets.QPushButton = settings_widget.findChild(QtWidgets.QPushButton, 'login_button')
    login_button.click()

    process_events()

    capi_plugin._manager._window._browser.load.assert_called_once()
    capi_plugin._manager._window._browser.show.assert_called_once()


@pytest.mark.parametrize(('state', 'text'), [
    (capi.CapiState.STATES.HAS_ACCESS_TOKEN, 'Status: OK'),
    (capi.CapiState.STATES.REFRESH_REQUIRED, 'Status: token refresh required'),
    (capi.CapiState.STATES.LOGIN_REQUIRED, 'Status: login required')
])
def test_update_status_label(state, text, settings_widget, capi_plugin):
    capi_plugin._manager.state._state = state

    settings_widget.update_status_label()

    assert settings_widget._status_label.text() == text


STATES = capi.CapiState.STATES


@pytest.mark.parametrize(('at', 'rt', 'expected_state'), [
    (None, None, STATES.LOGIN_REQUIRED),
    ('foo', None, STATES.HAS_ACCESS_TOKEN),
    ('foo', 'bar', STATES.HAS_ACCESS_TOKEN),
    (None, 'bar', STATES.REFRESH_REQUIRED),
])
def test_initial_capi_state(at, rt, expected_state):
    settings = capi.CapiSettings.get_insance()
    settings.access_token = at
    settings.refresh_token = rt

    state = capi.CapiState()

    assert state._state == expected_state


@pytest.mark.parametrize(('ac', 'exires_in', 'expired'), [
    ('foo', None, False),
    (None, None, True),
    ('foo', datetime.now() - timedelta(days=1), True),
    ('foo', datetime.now() + timedelta(days=1), False),
])
def test_manager_access_token_expired(ac, exires_in, expired, request):
    settings = capi.CapiSettings.get_insance()
    settings.access_token = ac
    settings.expires_in = exires_in

    capi_plugin = request.getfixturevalue('capi_plugin')

    if expired:
        assert settings.access_token is None
    else:
        assert settings.access_token is not None
