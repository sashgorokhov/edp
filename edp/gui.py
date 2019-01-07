import tkinter as tk

from edp.plugin import PluginManager


class MainWindow:
    def __init__(self, root: tk.Tk, plugin_manager: PluginManager):
        self._root = root

