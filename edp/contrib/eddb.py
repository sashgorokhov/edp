"""EDDB integration plugin"""
import functools
import re
from typing import Union, Sequence, List, Tuple

import requests
from urlpath import URL

from edp import config


class EDDBApi:
    """
    EDDB api interface.

    Since EDDB has no http api this is just html parser with nice interface.
    """
    def __init__(self):
        self._session = requests.Session()
        self._session.headers['User-Agent'] = config.USERAGENT

    @functools.lru_cache(120)
    def search_station(self, facility: Union[Sequence[str], str], ref_system_id: int) -> List[Tuple[str, str]]:
        """
        Return list of stations with given facilities

        :returns: List[Tuple[station name, system name]]
        """
        if not isinstance(facility, str):
            facility = ','.join(facility)

        url = URL('https://eddb.io/station').with_query(
            h=facility,
            r=ref_system_id,
        )
        response = self._session.get(str(url))
        text = response.text
        results = re.findall(
            r'<a href="/station/\d+">(?P<station>.*?)</a>.*? <a href="/system/\d+">(?P<system>.*?)</a>', text
        )
        return results
