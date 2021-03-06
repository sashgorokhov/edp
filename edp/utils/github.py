"""Simple gitgub API client"""
from pathlib import Path
from typing import List, Dict, Optional, Union

import requests
from urlpath import URL

from edp import config

BASE_URL = URL('https://api.github.com')


class GithubApi:
    """Simple gitgub API client"""
    def __init__(self, api_token: Optional[str] = None):
        self._token = api_token
        self._session = requests.Session()
        if api_token:
            self._session.headers['Authorization'] = f'token {api_token}'
        self._session.headers['User-Agent'] = config.USERAGENT
        self._session.headers['Accept'] = 'application/vnd.github.v3+json'

    def get_releases(self, owner: str, repo: str) -> List[Dict]:
        """Return repo releases list"""
        response = self._session.get(BASE_URL / 'repos' / owner / repo / 'releases')
        return response.json()

    def get_releases_latest(self, owner: str, repo: str) -> Dict:
        """Return repo latest release"""
        response = self._session.get(BASE_URL / 'repos' / owner / repo / 'releases' / 'latest')
        return response.json()

    # pylint: disable=too-many-arguments
    def create_release(self, owner: str, repo: str, tag_name: str, name: str, body: str, draft: bool = True,
                       prerelease: bool = False) -> Dict:
        """
        Create release
        """
        response = self._session.post(BASE_URL / 'repos' / owner / repo / 'releases', json={
            'tag_name': tag_name,
            'name': name,
            'body': body,
            'draft': draft,
            'prerelease': prerelease
        })
        response.raise_for_status()
        return response.json()

    # pylint: disable=too-many-arguments
    def upload_asset(self, upload_url: Union[URL, str], filename: Path, content_type: str, name: str,
                     label: Optional[str] = None) -> Dict:
        """
        Upload release asset
        """
        params = {'name': name}
        if label is not None:
            params['label'] = label
        with filename.open('rb') as f:
            response = self._session.post(upload_url, params=params, data=f, headers={'Content-Type': content_type})
        response.raise_for_status()
        return response.json()
