"""Static, keyboard-accessible help bubbles for Celestial Tk applications.

A bubble is a small round ``?`` dot shown next to an input, button group or
output area.  It is collapsed by default; clicking it or pressing Enter/Space
while it is focused opens a short explanation.  Clicking it again, clicking
elsewhere in the window, or pressing Esc closes it.

The explanation text is plain static data supplied by the calling module (the
same module that owns the feature).  This module never calls a model and never
touches the network; it only renders text that already exists in the product.
"""
import tkinter as tk

DEFAULT_COLORS = {
    "bg": "#12161C",
    "fg": "#EDE7D8",
    "accent": "#C9A227",
    "border": "#C9A227",
    "surface": "#1B2028",
    "muted": "#9AA3AE",
}

_BORDER = 1
_SIZE = 20


def _parent_bg(widget, fallback):
    try:
        value = widget.cget("bg")
        if value:
            return value
    except (tk.TclError, AttributeError):
        pass
    try:
        style = widget.cget("style")
        if style:
            return fallback
    except (tk.TclError, AttributeError):
        pass
    return fallback


def _is_descendant(widget, ancestor):
    current = widget
    while current is not None:
        if current == ancestor:
            return True
        try:
            current = current.master
        except AttributeError:
            return False
    return False


class HelpBubble(tk.Frame):
    """One ``?`` dot plus its collapsed popup explanation."""

    def __init__(self, parent, key, text, title="说明", colors=None, manager=None):
        colors = dict(DEFAULT_COLORS, **(colors or {}))
        super().__init__(parent, bg=_parent_bg(parent, colors["bg"]))
        self.key = key
        self.text = str(text).strip()
        self.title = title
        self.colors = colors
        self.manager = manager
        self._popup = None
        self._label = None
        self._open = False

        self.canvas = tk.Canvas(
            self, width=_SIZE, height=_SIZE, highlightthickness=0,
            bg=_parent_bg(parent, colors["bg"]), takefocus=1, cursor="hand2",
        )
        self.canvas.pack()
        self._oval = self.canvas.create_oval(
            1.5, 1.5, _SIZE - 1.5, _SIZE - 1.5,
            fill=colors["bg"], outline=colors["accent"], width=_BORDER,
        )
        self._glyph = self.canvas.create_text(
            _SIZE / 2, _SIZE / 2, text="?", fill=colors["accent"],
            font=("Segoe UI", 9, "bold"),
        )
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Return>", self._on_key)
        self.canvas.bind("<KP_Enter>", self._on_key)
        self.canvas.bind("<space>", self._on_key)
        self.canvas.bind("<FocusIn>", self._on_focus_in)
        self.canvas.bind("<FocusOut>", self._on_focus_out)

    # -- public API -----------------------------------------------------
    @property
    def is_open(self):
        return self._open

    def open(self):
        if self._open:
            return
        self._ensure_popup()
        self._open = True
        self._position()
        self._popup.place(x=self._popup_x, y=self._popup_y,
                          width=self._popup_width, height=self._popup_height)
        self._popup.lift()
        self._paint(active=True)
        if self.manager is not None:
            self.manager._set_active(self)

    def close(self):
        if not self._open:
            return
        self._open = False
        if self._popup is not None:
            try:
                self._popup.place_forget()
            except tk.TclError:
                pass
        self._paint(active=False)
        if self.manager is not None:
            self.manager._set_active(None)
        try:
            self.canvas.focus_set()
        except tk.TclError:
            pass

    def toggle(self):
        if self._open:
            self.close()
        else:
            self.open()

    def invoke(self):
        """Programmatic activation used by keyboard bindings and verification."""
        self.toggle()

    # -- internals ------------------------------------------------------
    def _paint(self, active):
        colors = self.colors
        try:
            self.canvas.itemconfigure(
                self._oval,
                fill=colors["accent"] if active else colors["bg"],
                outline=colors["accent"],
            )
            self.canvas.itemconfigure(
                self._glyph, fill=colors["bg"] if active else colors["accent"],
            )
        except tk.TclError:
            pass

    def _on_click(self, _event):
        self.toggle()
        return "break"

    def _on_key(self, _event):
        self.toggle()
        return "break"

    def _on_focus_in(self, _event):
        try:
            self.canvas.itemconfigure(self._oval, width=2)
        except tk.TclError:
            pass

    def _on_focus_out(self, _event):
        try:
            self.canvas.itemconfigure(self._oval, width=_BORDER)
        except tk.TclError:
            pass

    def _ensure_popup(self):
        if self._popup is not None:
            return
        # An in-window frame is used instead of a Toplevel: it stays above the
        # form controls, keeps keyboard focus in the same window, and is captured
        # reliably by UI screenshot evidence on high-DPI displays.
        self._popup = tk.Frame(
            self.winfo_toplevel(), bg=self.colors["border"], bd=0,
            highlightthickness=0,
        )
        body = tk.Frame(self._popup, bg=self.colors["surface"], padx=12, pady=10)
        body.pack(fill="both", expand=True, padx=_BORDER, pady=_BORDER)
        heading = tk.Label(
            body, text=f"?  {self.title}", anchor="w", justify="left",
            bg=self.colors["surface"], fg=self.colors["accent"],
            font=("Segoe UI", 9, "bold"),
        )
        heading.pack(fill="x")
        self._label = tk.Label(
            body, text=self.text, anchor="w", justify="left",
            wraplength=380, bg=self.colors["surface"], fg=self.colors["fg"],
            font=("Segoe UI", 9), padx=0, pady=4,
        )
        self._label.pack(fill="both", expand=True)
        hint = tk.Label(
            body, text="Esc 或再次点击 ? 收起", anchor="e", justify="right",
            bg=self.colors["surface"], fg=self.colors["muted"],
            font=("Segoe UI", 8),
        )
        hint.pack(fill="x")
        for widget in (self._popup, body, heading, self._label, hint):
            widget.bind("<Button-1>", lambda _event: "break")
            widget.bind("<Escape>", lambda _event: (self.close(), "break")[1])

    def _position(self):
        self._popup.update_idletasks()
        self._popup_width = self._popup.winfo_reqwidth()
        self._popup_height = self._popup.winfo_reqheight()
        root = self.winfo_toplevel()
        root_width = max(root.winfo_width(), 200)
        root_height = max(root.winfo_height(), 200)
        x = self.canvas.winfo_rootx() - root.winfo_rootx()
        y = self.canvas.winfo_rooty() - root.winfo_rooty() + self.canvas.winfo_height() + 4
        self._popup_x = max(4, min(x, root_width - self._popup_width - 4))
        self._popup_y = max(4, min(y, root_height - self._popup_height - 4))


class HelpManager:
    """Per-window registry: one Esc/click-away handler for all bubbles."""

    def __init__(self, root, colors=None):
        self.root = root
        self.colors = dict(DEFAULT_COLORS, **(colors or {}))
        self.bubbles = []
        self.active = None
        setattr(root, "_celestial_help_manager", self)
        root.bind_all("<Escape>", self._on_escape, add="+")
        root.bind_all("<Button-1>", self._on_global_click, add="+")

    def attach(self, parent, key, text, title="说明", colors=None, **layout):
        bubble = HelpBubble(
            parent, key, text, title=title,
            colors=dict(self.colors, **(colors or {})), manager=self,
        )
        self.bubbles.append(bubble)
        if layout:
            bubble.pack(**{k: v for k, v in layout.items() if k in {
                "side", "padx", "pady", "anchor", "fill", "expand", "ipadx", "ipady",
            }})
        return bubble

    def open_first(self):
        if not self.bubbles:
            return None
        self.bubbles[0].open()
        return self.bubbles[0]

    def first_open(self):
        return next((bubble for bubble in self.bubbles if bubble.is_open), None)

    def close_all(self):
        for bubble in list(self.bubbles):
            bubble.close()

    def _set_active(self, bubble):
        if bubble is self.active:
            return
        if self.active is not None and self.active is not bubble:
            self.active.close()
        self.active = bubble

    def _on_escape(self, _event=None):
        if self.active is not None:
            self.active.close()
            return "break"
        return None

    def _on_global_click(self, event):
        if self.active is None:
            return None
        widget = getattr(event, "widget", None)
        popup = self.active._popup
        if popup is not None and widget is not None:
            if _is_descendant(widget, popup) or _is_descendant(widget, self.active):
                return None
        self.active.close()
        return None


def attach_help(parent, key, text, title="说明", colors=None):
    """Attach a collapsed ``?`` bubble to ``parent`` and return it.

    The caller decides the layout (``bubble.pack(side="left")``), so bubbles can
    sit next to any existing input, button group or output area.
    """
    root = parent.winfo_toplevel()
    manager = getattr(root, "_celestial_help_manager", None)
    if manager is None:
        manager = HelpManager(root, colors=colors)
    return manager.attach(parent, key, text, title=title, colors=colors)
