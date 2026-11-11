"""Clinical Calm visual foundation for the medical workspace.

Colours and type sizes are a direct implementation of the shared design tokens
(``_evidence/ui-modernization/tokens.json``): a warm paper chrome around one
ink anatomy stage.  Nothing in this module knows about drugs, evidence or
simulation; it only renders.

Widgets stay deliberately small and close to Tk primitives.  The medical UI is
built from five parts: paper surface, hairline, label, button and chip.
"""
import tkinter as tk
from tkinter import ttk

FONT = 'Microsoft YaHei UI'
MONO = 'Cascadia Mono'

PAPER = {
    'bg': '#F5F3EE', 'bgElevated': '#FBFAF7', 'surface': '#FFFFFF', 'surface2': '#EFEDE6',
    'line': '#E3DFD5', 'lineStrong': '#CFC9BC', 'ink': '#17181A', 'ink2': '#555A5E',
    'ink3': '#83878B', 'accent': '#0F6B5A', 'accentInk': '#FFFFFF', 'accentSoft': '#E3F0EB',
    'gain': '#0E7A4A', 'loss': '#B33427', 'warn': '#8A6410', 'info': '#2A6291',
}
INK = {
    'bg': '#0C0D0F', 'bgElevated': '#121316', 'surface': '#16171A', 'surface2': '#1C1D21',
    'line': '#232428', 'lineStrong': '#34363B', 'ink': '#F3F1EB', 'ink2': '#B9B5AC',
    'ink3': '#8A867E', 'accent': '#74E3C8', 'accentInk': '#052A23', 'accentSoft': '#12241F',
    'gain': '#59D9A0', 'loss': '#F08C7F', 'warn': '#E8BE73', 'info': '#8FC5F0',
}

# Presentation-only mapping of internal codes.  The raw code stays available in
# the small "原码" line so provenance is never hidden, but it is not the label.
STATUS = {
    'SOURCE_ASSOCIATION': ('文献关联 · 待审核', 'info'),
    'INSUFFICIENT_EVIDENCE': ('证据不足', 'muted'),
    'HOLD_FOR_REVIEW': ('待人工审核', 'warn'),
    'MECHANISM_INFERENCE': ('机制推断', 'info'),
    'PENDING_REVIEW': ('待人工审核', 'warn'),
    'online': ('在线官方标签', 'gain'),
    'cache': ('本地缓存 · 已校验', 'info'),
    'seed': ('随程序提供的来源事实', 'muted'),
    'unknown': ('自定义 / 未确认身份', 'muted'),
    'unsupported_route': ('该途径无已校验标签', 'muted'),
    'unavailable': ('无独立标签', 'muted'),
    'CONDITIONAL_POPULATION_RESEARCH_ESTIMATE': ('条件化研究估计', 'info'),
    'REFUSED': ('未生成估计', 'loss'),
}
CATEGORY = {'mechanism': '机制', 'metabolism': '代谢与处置', 'excretion': '排泄',
            'label_concern': '标签关注'}
APPLICABILITY = {'CONTEXT_MISMATCH': '情境不一致',
                 'DOSE_TIMELINE_POPULATION_NOT_VERIFIED': '剂量 / 时程 / 人群未核对'}
STRUCTURAL = {'PASS': '来源结构校验通过', 'MISSING_PROVENANCE': '来源信息缺失'}
KIND = {'organ': '器官', 'system': '系统', 'muscle': '肌群'}


def status_text(code):
    return STATUS.get(code, (str(code), 'muted'))[0]


def status_tone(code):
    return STATUS.get(code, (str(code), 'muted'))[1]


def tone_color(tone, palette=PAPER):
    return {'muted': palette['ink3'], 'gain': palette['gain'], 'loss': palette['loss'],
            'warn': palette['warn'], 'info': palette['info'],
            'accent': palette['accent']}.get(tone, palette['ink3'])


def setup(window):
    """Register the ttk styles used by every medical surface."""
    window.configure(background=PAPER['bg'])
    style = ttk.Style(window)
    try:
        style.theme_use('clam')
    except tk.TclError:
        pass
    style.configure('.', background=PAPER['bg'], foreground=PAPER['ink'], font=(FONT, 10))
    for name, colour in (('Paper.TFrame', PAPER['bg']), ('Surface.TFrame', PAPER['surface']),
                         ('Raised.TFrame', PAPER['bgElevated']), ('Ink.TFrame', INK['bg'])):
        style.configure(name, background=colour)
    style.configure('Paper.TLabel', background=PAPER['bg'], foreground=PAPER['ink'])
    style.configure('Surface.TLabel', background=PAPER['surface'], foreground=PAPER['ink'])
    style.configure('Ink.TLabel', background=INK['bg'], foreground=INK['ink2'])
    shared = dict(fieldbackground=PAPER['surface'], foreground=PAPER['ink'],
                  insertcolor=PAPER['ink'], bordercolor=PAPER['lineStrong'],
                  lightcolor=PAPER['surface'], darkcolor=PAPER['surface'], padding=(8, 6))
    style.configure('Paper.TEntry', **shared)
    style.map('Paper.TEntry', bordercolor=[('focus', PAPER['accent'])])
    style.configure('Paper.TCombobox', background=PAPER['surface'], arrowcolor=PAPER['ink2'],
                    **shared)
    style.map('Paper.TCombobox',
              fieldbackground=[('readonly', PAPER['surface']), ('disabled', PAPER['surface2'])],
              foreground=[('readonly', PAPER['ink']), ('disabled', PAPER['ink3'])],
              bordercolor=[('focus', PAPER['accent'])], selectbackground=[('readonly', PAPER['surface'])],
              selectforeground=[('readonly', PAPER['ink'])])
    style.configure('Paper.TCheckbutton', background=PAPER['bg'], foreground=PAPER['ink2'],
                    focuscolor=PAPER['bg'])
    style.map('Paper.TCheckbutton', background=[('active', PAPER['bg'])],
              foreground=[('active', PAPER['ink'])])
    style.configure('Paper.Treeview', background=PAPER['surface'], fieldbackground=PAPER['surface'],
                    foreground=PAPER['ink'], bordercolor=PAPER['line'],
                    rowheight=28, font=(FONT, 10))
    style.map('Paper.Treeview', background=[('selected', PAPER['accentSoft'])],
              foreground=[('selected', PAPER['ink'])])
    style.configure('Paper.Treeview.Heading', background=PAPER['bgElevated'],
                    foreground=PAPER['ink2'], relief='flat', font=(FONT, 9, 'bold'),
                    padding=(8, 4))
    style.map('Paper.Treeview.Heading', background=[('active', PAPER['surface2'])])
    for name, palette in (('Paper.Vertical.TScrollbar', PAPER), ('Ink.Vertical.TScrollbar', INK)):
        style.configure(name, background=palette['surface2'], troughcolor=palette['bg'],
                        bordercolor=palette['bg'], arrowcolor=palette['ink3'], relief='flat',
                        width=10)
        style.map(name, background=[('active', palette['lineStrong'])])
    for name, palette in (('Paper.TNotebook', PAPER), ('Ink.TNotebook', INK)):
        style.configure(name, background=palette['bg'], borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure(name + '.Tab', background=palette['bg'], foreground=palette['ink2'],
                        padding=(14, 8), font=(FONT, 10))
        style.map(name + '.Tab', background=[('selected', palette['surface'])],
                  foreground=[('selected', palette['ink'])])
    window.option_add('*TCombobox*Listbox.background', PAPER['surface'])
    window.option_add('*TCombobox*Listbox.foreground', PAPER['ink'])
    window.option_add('*TCombobox*Listbox.selectBackground', PAPER['accentSoft'])
    window.option_add('*TCombobox*Listbox.selectForeground', PAPER['ink'])
    window.option_add('*TCombobox*Listbox.font', (FONT, 10))
    return style


def apply_theme(root):
    """Backwards-compatible alias used by the application entry point."""
    return setup(root)


def bg_of(widget, fallback=None):
    try:
        return widget.cget('background') or fallback or PAPER['bg']
    except (tk.TclError, TypeError):
        return fallback or PAPER['bg']


def center_on(window, parent):
    """Place a dialog near the centre of its parent once it is mapped."""
    def place():
        try:
            width = max(window.winfo_width(), window.winfo_reqwidth())
            height = max(window.winfo_height(), window.winfo_reqheight())
            x = parent.winfo_rootx() + max(0, (parent.winfo_width() - width) // 2)
            y = parent.winfo_rooty() + max(0, (parent.winfo_height() - height) // 2)
            window.geometry(f'+{max(0, x)}+{max(0, y)}')
        except tk.TclError:
            pass
    window.after(60, place)


def text(parent, value='', size=10, weight='normal', fg=None, bg=None, wraplength=0,
         anchor='w', **kw):
    return tk.Label(parent, text=value, font=(FONT, size, weight),
                    fg=fg or PAPER['ink'], bg=bg if bg is not None else bg_of(parent),
                    anchor=anchor, justify='left', wraplength=wraplength, **kw)


def mono(parent, value='', size=9, fg=None, bg=None, **kw):
    return tk.Label(parent, text=value, font=(MONO, size), fg=fg or PAPER['ink3'],
                    bg=bg if bg is not None else bg_of(parent), anchor='w', justify='left', **kw)


def eyebrow(parent, value, fg=None, bg=None):
    return tk.Label(parent, text=value, font=(FONT, 9, 'bold'),
                    fg=fg or PAPER['ink3'], bg=bg if bg is not None else bg_of(parent),
                    anchor='w')


def checkbox(parent, value, variable, command=None, bg=None, fg=None):
    """Native check button with paper colours (ttk focus highlight avoided)."""
    base = bg if bg is not None else bg_of(parent)
    return tk.Checkbutton(parent, text=value, variable=variable, command=command,
                          font=(FONT, 9), fg=fg or PAPER['ink2'], bg=base,
                          activebackground=base, activeforeground=PAPER['ink'],
                          selectcolor=PAPER['surface2'], bd=0, highlightthickness=0,
                          anchor='w', cursor='hand2')


def hairline(parent, colour=None, bg=None):
    return tk.Frame(parent, height=1, bg=colour or PAPER['line'],
                    bd=0, highlightthickness=0)


class FlatButton(tk.Button):
    """Flat paper/ink button with an explicit hover colour (no gradients)."""

    KINDS = {
        'primary': dict(fg=PAPER['accentInk'], bg=PAPER['accent'], hover='#0B5749',
                        size=10, weight='bold', padx=14, pady=7, border=0),
        'secondary': dict(fg=PAPER['ink'], bg=PAPER['surface'], hover=PAPER['surface2'],
                          size=10, weight='normal', padx=12, pady=6, border=1),
        'quiet': dict(fg=PAPER['ink2'], bg=None, hover=PAPER['surface2'],
                      size=9, weight='normal', padx=4, pady=3, border=0),
        'link': dict(fg=PAPER['accent'], bg=None, hover=PAPER['accentSoft'],
                     size=9, weight='normal', padx=3, pady=2, border=0),
        'ink': dict(fg=INK['ink'], bg=INK['surface'], hover=INK['surface2'],
                    size=9, weight='normal', padx=10, pady=5, border=1),
        'inkQuiet': dict(fg=INK['ink2'], bg=INK['bg'], hover=INK['surface2'],
                         size=9, weight='normal', padx=4, pady=3, border=0),
    }

    def __init__(self, parent, value, command=None, kind='quiet', **kw):
        spec = dict(self.KINDS[kind])
        border = spec.pop('border')
        size = spec.pop('size')
        weight = spec.pop('weight')
        padx = spec.pop('padx')
        pady = spec.pop('pady')
        hover = spec.pop('hover')
        base = spec.pop('bg') or bg_of(parent)
        fg = spec.pop('fg')
        palette = INK if kind in ('ink', 'inkQuiet') else PAPER
        super().__init__(parent, text=value, command=command, font=(FONT, size, weight),
                         fg=fg, bg=base, activebackground=hover, activeforeground=fg,
                         relief='flat', bd=0, highlightthickness=border,
                         highlightbackground=palette['line'], highlightcolor=palette['line'],
                         cursor='hand2', padx=padx, pady=pady, **kw)
        if border:
            self.bind('<Enter>', lambda _: self.configure(highlightbackground=palette['lineStrong']))
            self.bind('<Leave>', lambda _: self.configure(highlightbackground=palette['line']))
        else:
            self.bind('<Enter>', lambda _: self.configure(bg=hover))
            self.bind('<Leave>', lambda _: self.configure(bg=base))


class Chip(tk.Label):
    def __init__(self, parent, value, command=None, bg=None, fg=None, **kw):
        base = bg or PAPER['accentSoft']
        super().__init__(parent, text=value, font=(FONT, 9), fg=fg or PAPER['accent'],
                         bg=base, padx=8, pady=3, anchor='w', **kw)
        self.configure(highlightthickness=1, highlightbackground=PAPER['line'])
        self._command = command
        if command:
            self.configure(cursor='hand2')
            self.bind('<Button-1>', lambda _: command())
            self.bind('<Enter>', lambda _: self.configure(bg=PAPER['surface2']))
            self.bind('<Leave>', lambda _: self.configure(bg=base))


def status_pill(parent, code, label=None, tone=None, bg=None, size=9):
    """Dot + word; colour only reinforces the word (design system §5)."""
    base = bg if bg is not None else bg_of(parent)
    frame = tk.Frame(parent, bg=base)
    resolved = tone or status_tone(code)
    colour = tone_color(resolved)
    tk.Label(frame, text='●', font=(FONT, size - 2), fg=colour, bg=base).pack(side='left')
    tk.Label(frame, text=label or status_text(code), font=(FONT, size),
             fg=colour if resolved in ('loss', 'warn', 'gain') else PAPER['ink2'],
             bg=base).pack(side='left', padx=(4, 0))
    return frame


class ScrollArea(tk.Frame):
    """Canvas-backed scrolling column; the mouse wheel works inside the area."""

    def __init__(self, parent, bg=None, palette=PAPER):
        base = bg if bg is not None else bg_of(parent)
        super().__init__(parent, bg=base)
        self.canvas = tk.Canvas(self, bg=base, highlightthickness=0, bd=0, takefocus=0)
        self.bar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview,
                                 style=('Ink' if palette is INK else 'Paper') + '.Vertical.TScrollbar')
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.bar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.inner = tk.Frame(self.canvas, bg=base)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor='nw')
        self.inner.bind('<Configure>', self._region)
        self.canvas.bind('<Configure>', self._width)
        self.canvas.bind('<Enter>', self._grab_wheel)
        self.canvas.bind('<Leave>', self._release_wheel)

    def _region(self, _=None):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _width(self, event):
        self.canvas.itemconfigure(self._window, width=max(1, event.width))
        self._region()

    def _grab_wheel(self, _=None):
        self.canvas.bind_all('<MouseWheel>', self._wheel)

    def _release_wheel(self, _=None):
        self.canvas.unbind_all('<MouseWheel>')

    def _wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), 'units')

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()
        self.canvas.yview_moveto(0)
        return self.inner


class Disclosure(tk.Frame):
    """Progressive disclosure: secondary inputs stay reachable but out of the way."""

    def __init__(self, parent, label='更多选项', bg=None, on_toggle=None):
        base = bg if bg is not None else bg_of(parent)
        super().__init__(parent, bg=base)
        self._label = label
        self._on_toggle = on_toggle
        self.open = False
        self.button = FlatButton(self, label + '  ▾', command=self.toggle, kind='link')
        self.button.pack(anchor='w')
        self.body = tk.Frame(self, bg=base)

    def toggle(self):
        self.set_open(not self.open)

    def set_open(self, value):
        self.open = bool(value)
        if self.open:
            self.body.pack(fill='x', pady=(8, 0))
            self.button.configure(text=self._label + '  ▴')
        else:
            self.body.pack_forget()
            self.button.configure(text=self._label + '  ▾')
        if self._on_toggle:
            self._on_toggle(self.open)
