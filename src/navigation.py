"""Notebook selection follows clicks; selected tabs keep the same geometry."""
from tkinter import ttk,TclError


class StableNotebook(ttk.Notebook):
    def __init__(self,parent,**kwargs):
        super().__init__(parent,**kwargs)
        self.bind('<Button-1>',self.clicked)

    def clicked(self,event):
        try:
            index=self.index(f'@{event.x},{event.y}')
            self.select(index)
            self.focus_set()
            return 'break'
        except TclError:return None
