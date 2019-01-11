import tkinter as tk


class MainWindow(tk.Frame):
    def __init__(self, root: tk.Tk):
        super(MainWindow, self).__init__(root)

        self._root = root
        self.pack()
