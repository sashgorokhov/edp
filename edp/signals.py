"""Define core signals for generic app events"""
from edp.signalslib import Signal

init_complete = Signal('init complete')
exiting = Signal('exiting')
app_created = Signal('app created')
