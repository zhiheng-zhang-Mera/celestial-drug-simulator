"""Top-level module switcher rendered as a segmented control.

The old Notebook tabs read as an operating-system widget.  A segmented control
keeps the same interaction (click to switch view) but marks selection with an
accent underline and weight rather than a filled block.
"""
import tkinter as tk

from src import ui_theme


class SegmentedNav(tk.Frame):
    def __init__(self, parent, on_change=None, bg=None, fg=None, accent=None, size=11):
        base = bg if bg is not None else ui_theme.PAPER['bg']
        super().__init__(parent, bg=base)
        self.bg = base
        self.fg = fg or ui_theme.PAPER['ink2']
        self.accent = accent or ui_theme.PAPER['accent']
        self.size = size
        self.on_change = on_change
        self._items = []
        self._current = None

    def add(self, key, text):
        holder = tk.Frame(self, bg=self.bg)
        holder.pack(side='left', padx=(0, 18))
        label = tk.Label(holder, text=text, font=(ui_theme.FONT, self.size),
                         fg=self.fg, bg=self.bg, cursor='hand2', padx=0, pady=4)
        label.pack(anchor='w')
        underline = tk.Frame(holder, height=2, bg=self.bg, bd=0, highlightthickness=0)
        underline.pack(fill='x', pady=(2, 0))
        label.bind('<Button-1>', lambda _event, item_key=key: self.select(item_key))
        label.bind('<Enter>', lambda _event, item=label: item.configure(fg=self.accent))
        label.bind('<Leave>', lambda _event, item=label, item_key=key: item.configure(
            fg=self.accent if item_key == self._current else self.fg))
        self._items.append(dict(key=key, label=label, underline=underline))
        return key

    def select(self, key, notify=True):
        keys = [item['key'] for item in self._items]
        if key not in keys:
            return
        changed = key != self._current
        self._current = key
        for item in self._items:
            selected = item['key'] == key
            item['label'].configure(
                fg=self.accent if selected else self.fg,
                font=(ui_theme.FONT, self.size, 'bold' if selected else 'normal'))
            item['underline'].configure(bg=self.accent if selected else self.bg)
        if notify and changed and self.on_change:
            self.on_change(key)

    def current(self):
        return self._current
