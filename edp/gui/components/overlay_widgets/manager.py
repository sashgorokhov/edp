"""
Overlay widgets registration
"""
import logging
from typing import Dict, Type, Iterator

from edp.gui.components.overlay_widgets.base import BaseOverlayWidget

WIDGET_REGISTRY: Dict[str, Type[BaseOverlayWidget]] = {}

logger = logging.getLogger(__name__)


def register(widget_cls: Type[BaseOverlayWidget]):
    """Add widget class to registry"""
    WIDGET_REGISTRY[widget_cls.friendly_name] = widget_cls
    return widget_cls


def get_registered_widgets() -> Iterator[BaseOverlayWidget]:
    """Return registered widget instances"""
    for name, widget_cls in WIDGET_REGISTRY.items():
        try:
            yield get_widget_instance(widget_cls)
        except:
            logger.exception(f'Failed to create widget instance: {name}')


def get_widget_instance(widget_cls: Type[BaseOverlayWidget]) -> BaseOverlayWidget:
    """Instantiate widget class"""
    return widget_cls()
