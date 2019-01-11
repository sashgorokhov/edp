import logging
import os

from edp import signals
from edp.contrib.gamestate import GameStateData
from edp.journal import Event
from edp.plugin import BasePlugin, callback
from edp.contrib import gamestate, edsm


logger = logging.getLogger(__name__)


class _DebugPlugin(BasePlugin):
    @property
    def enabled(self):
        return 'EDP_DEBUG' in os.environ

    @callback(signals.JOURNAL_EVENT)
    def on_journal_event(self, event: Event):
        logger.debug('Journal event:' + event.raw)

    @callback(gamestate.SIGNALS.GAME_STATE_CHANGED)
    def on_gamestate_changed(self, state: GameStateData):
        logger.debug('GameStateData: %s', state)
