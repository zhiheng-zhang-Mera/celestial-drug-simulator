"""Anatomy workspace: a single ink stage, a paper evidence reading pane.

Data still comes from ``src.anatomy`` unchanged; this module only decides how
regions, status codes and provenance are presented to the reader.
"""
import tkinter as tk
from tkinter import ttk
from urllib.parse import urlparse
import webbrowser

from src.anatomy import REGIONS, region_details
from src.web_body import WebBody
from src import ui_theme as ui

PAPER = ui.PAPER
INK = ui.INK
SUPPLEMENT_REGIONS = ('uterus', 'testes', 'biceps', 'triceps', 'quadriceps')
SUPPORTED_SUBSTANCES = (('atomoxetine', '阿托莫西汀 / atomoxetine'),)
SOURCE_NAMES = {'mayoclinic.org': 'Mayo Clinic', 'dailymed.nlm.nih.gov': 'DailyMed / NLM',
                'api.fda.gov': 'openFDA', 'cpicpgx.org': 'CPIC'}


def apply_theme(root):
    return ui.setup(root)


def source_name(url):
    if not url:
        return '来源缺失'
    host = urlparse(url).netloc.lower()
    for domain, name in SOURCE_NAMES.items():
        if domain in host:
            return name
    return host or url


def substance_label(item):
    if not item:
        return '未选择物质'
    return item.get('name') or item.get('compound_id') or '未选择物质'


class AnatomyWorkspace(tk.Frame):
    def __init__(self, parent, catalog, get_selected, get_context, open_context, open_pgx,
                 open_regimen, on_state=None):
        super().__init__(parent, bg=PAPER['bg'])
        self.drug = None
        self.selected = 'brain'
        self.get_context = get_context
        self.on_state = on_state
        self._wrap_labels = []
        self._panel_width = 400
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._catalog = catalog
        self._substances = list(SUPPORTED_SUBSTANCES)
        for identity, record in catalog.get('compounds', {}).items():
            if identity == 'atomoxetine':
                continue
            self._substances.append((identity, (record or {}).get('name') or identity))
        self._labels = [label for _identity, label in self._substances]
        self._build_toolbar(get_selected, open_context, open_pgx, open_regimen)
        self._build_split()
        self.bind('<Configure>', self._on_resize)
        self.render()

    # ------------------------------------------------------------------ toolbar
    def _build_toolbar(self, get_selected, open_context, open_pgx, open_regimen):
        toolbar = tk.Frame(self, bg=PAPER['surface'])
        toolbar.grid(row=0, column=0, sticky='ew')
        bar = tk.Frame(toolbar, bg=PAPER['surface'], padx=24, pady=12)
        bar.pack(fill='x')
        ui.text(bar, '当前物质', size=9, fg=PAPER['ink3']).pack(side='left', padx=(0, 8))
        self.choice = tk.StringVar(value='未选择物质')
        self._query = tk.StringVar(value='未选择物质')
        self.combo = ttk.Combobox(bar, textvariable=self._query, values=self._labels,
                                  style='Paper.TCombobox', width=28)
        self.combo.pack(side='left', padx=(0, 8))
        self.combo.bind('<KeyRelease>', self._filter_substances)
        self.combo.bind('<<ComboboxSelected>>', self._choose_substance)
        self.combo.bind('<Return>', self._choose_substance)
        self.combo.bind('<FocusOut>', self._restore_substance)

        def use_regimen():
            item = get_selected()
            self.drug = item
            self.choice.set('方案选中 / ' + item['name'] if item else '未选择物质')
            self._query.set(item['name'] if item else '未选择物质')
            self.render()

        self.load_button = ui.FlatButton(bar, '载入方案选中项', kind='primary', command=use_regimen)
        self.load_button.pack(side='left', padx=(0, 14))
        ui.text(bar, '·', size=10, fg=PAPER['lineStrong']).pack(side='left', padx=(0, 10))
        for label, command in (('编辑多药方案', open_regimen), ('生理 / 基因', open_context),
                               ('来源 / 条件估计', open_pgx)):
            ui.FlatButton(bar, label, kind='quiet', command=command).pack(side='left', padx=(0, 6))
        legend = tk.Frame(bar, bg=PAPER['surface'])
        legend.pack(side='right')
        tk.Label(legend, text='●', font=(ui.FONT, 7), fg=PAPER['accent'],
                 bg=PAPER['surface']).pack(side='left')
        ui.text(legend, '亮色 = 文献关联，非个人反应', size=9,
                fg=PAPER['ink3']).pack(side='left', padx=(4, 0))
        ui.hairline(toolbar).pack(fill='x')

    def _filter_substances(self, event):
        if event.keysym in ('Left', 'Right', 'Up', 'Down', 'Return', 'Escape', 'Tab'):
            return
        typed = self._query.get().strip().casefold()
        values = self._labels if not typed else [
            label for label in self._labels if typed in label.casefold()]
        self.combo.configure(values=values or self._labels)

    def _choose_substance(self, _event=None):
        typed = self._query.get().strip()
        exact = [pair for pair in self._substances if pair[1] == typed]
        matches = exact or [pair for pair in self._substances if typed.casefold() in pair[1].casefold()]
        if len(matches) == 1:
            identity, label = matches[0]
            self.drug = {'kind': 'catalog', 'compound_id': identity, 'name': label}
            self.choice.set(label)
            self._query.set(label)
        else:
            self._query.set(self.choice.get())
        self.combo.configure(values=self._labels)
        self.render()

    def _restore_substance(self, _event=None):
        self._query.set(self.choice.get())
        self.combo.configure(values=self._labels)

    # -------------------------------------------------------------------- split
    def _build_split(self):
        split = tk.Frame(self, bg=PAPER['bg'])
        split.grid(row=1, column=0, sticky='nsew')
        split.columnconfigure(0, weight=1)
        split.rowconfigure(0, weight=1)
        self._split = split

        stage = tk.Frame(split, bg=INK['bg'])
        stage.grid(row=0, column=0, sticky='nsew', padx=(24, 0), pady=(16, 16))
        stage.columnconfigure(0, weight=1)
        stage.rowconfigure(1, weight=1)
        header = tk.Frame(stage, bg=INK['bg'], padx=18, pady=10)
        header.grid(row=0, column=0, sticky='ew')
        self.stage_title = tk.StringVar()
        tk.Label(header, textvariable=self.stage_title, font=(ui.FONT, 9, 'bold'),
                 fg=INK['ink2'], bg=INK['bg']).pack(side='left')
        ui.text(header, '点击器官或系统切换证据', size=9, fg=INK['ink3'],
                bg=INK['bg']).pack(side='right')
        ui.hairline(stage, colour=INK['line']).grid(row=2, column=0, sticky='ew')
        self.canvas = WebBody(stage, self.select_region)
        self.canvas.grid(row=1, column=0, sticky='nsew')
        self.geometry_note = tk.StringVar()
        note = tk.Frame(stage, bg=INK['bg'], padx=18, pady=8)
        note.grid(row=3, column=0, sticky='ew')
        tk.Label(note, textvariable=self.geometry_note, font=(ui.FONT, 8),
                 fg=INK['ink3'], bg=INK['bg'], anchor='w', justify='left',
                 wraplength=620).pack(fill='x')
        self._stage = stage

        panel = tk.Frame(split, bg=PAPER['surface'], width=self._panel_width,
                         highlightthickness=1, highlightbackground=PAPER['line'])
        panel.grid(row=0, column=1, sticky='nsew', padx=(16, 24), pady=(16, 16))
        panel.grid_propagate(False)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(2, weight=1)
        self.panel = panel
        top = tk.Frame(panel, bg=PAPER['surface'], padx=20, pady=16)
        top.grid(row=0, column=0, sticky='ew')
        top.columnconfigure(0, weight=1)
        ui.eyebrow(top, '证据阅读', bg=PAPER['surface']).grid(row=0, column=0, sticky='w')
        self.keys = list(REGIONS)
        self.region_choice = tk.StringVar(value=REGIONS[self.selected][0])
        self.directory = ttk.Combobox(top, textvariable=self.region_choice, width=9,
                                      values=[REGIONS[key][0] for key in self.keys],
                                      state='readonly', style='Paper.TCombobox')
        self.directory.grid(row=0, column=1, sticky='e')
        self.directory.bind('<<ComboboxSelected>>', self._directory_chosen)
        self.heading = tk.StringVar()
        tk.Label(top, textvariable=self.heading, font=(ui.FONT, 19, 'bold'),
                 fg=PAPER['ink'], bg=PAPER['surface'], anchor='w').grid(
            row=1, column=0, columnspan=2, sticky='w', pady=(8, 2))
        self.kind_line = tk.StringVar()
        tk.Label(top, textvariable=self.kind_line, font=(ui.FONT, 9), fg=PAPER['ink3'],
                 bg=PAPER['surface'], anchor='w').grid(
            row=2, column=0, columnspan=2, sticky='w')
        self.badges = tk.Frame(top, bg=PAPER['surface'])
        self.badges.grid(row=3, column=0, columnspan=2, sticky='w', pady=(10, 0))
        ui.hairline(panel).grid(row=1, column=0, sticky='ew')

        self.evidence = ui.ScrollArea(panel, bg=PAPER['surface'])
        self.evidence.grid(row=2, column=0, sticky='nsew', padx=(20, 8), pady=(12, 8))
        footer = tk.Frame(panel, bg=PAPER['surface'], padx=20, pady=12)
        footer.grid(row=3, column=0, sticky='ew')
        ui.hairline(footer).pack(fill='x', pady=(0, 10))
        self.source_btn = ui.FlatButton(footer, '打开当前区域证据原文 ↗', kind='secondary',
                                        command=self.open_source)
        self.source_btn.pack(fill='x')

    def _directory_chosen(self, _event=None):
        index = self.directory.current()
        if 0 <= index < len(self.keys):
            self.select_region(self.keys[index])

    # ------------------------------------------------------------------- state
    def select_region(self, key):
        if key not in REGIONS:
            return
        self.selected = key
        self.region_choice.set(REGIONS[key][0])
        self.render()

    def _on_resize(self, event):
        if event.widget is not self:
            return
        target = max(380, min(420, round(event.width * 0.37)))
        if target != self._panel_width:
            self._panel_width = target
            self.panel.configure(width=target)
        wrap = max(220, target - 56)
        if wrap != getattr(self, '_wrap', None):
            self._wrap = wrap
            for label in self._wrap_labels:
                label.configure(wraplength=wrap)

    def _geometry_text(self):
        if self.canvas.fallback:
            return '几何：BodyParts3D / DBCLS 简化参考网格；子宫为原有示意层。'
        if self.selected in SUPPLEMENT_REGIONS:
            return '几何：补充示意层，用于保留既有区域入口；不是实际组织仿真。'
        return '几何：用户指定 HTML 原稿 / 补充示意；形状和系统配色不构成药效证据。'

    def render(self):
        context = self.get_context() or {}
        data = region_details(self.drug, self.selected)
        self.heading.set(data['name'])
        self.region_choice.set(data['name'])
        self.kind_line.set(' '.join(filter(None, (ui.KIND.get(data['kind'], data['kind']),
                                                  '· 关联结构 ' + str(len(data['members'])) + ' 处'
                                                  if data['members'] else ''))))
        self.stage_title.set('解剖舞台 · ' + data['name'])
        self.geometry_note.set(self._geometry_text())
        self.choice.set(substance_label(self.drug))
        self._query.set(self.choice.get())
        self._render_badges(data)
        self._render_evidence(data)
        self.source_btn.configure(state='normal' if data['evidence'] else 'disabled')
        self.canvas.update_state(self.drug, self.selected)
        self._notify(context, data)

    def _render_badges(self, data):
        for child in self.badges.winfo_children():
            child.destroy()
        ui.status_pill(self.badges, data['status'], bg=PAPER['surface']).pack(side='left')
        tk.Frame(self.badges, bg=PAPER['surface'], width=14).pack(side='left')
        ui.status_pill(self.badges, 'PERSONAL_EFFECT_NOT_COMPUTED', label='个人效应未计算',
                       tone='muted', bg=PAPER['surface']).pack(side='left')

    def _render_evidence(self, data):
        inner = self.evidence.clear()
        self._wrap_labels = []
        wrap = max(220, self._panel_width - 56)
        if data['evidence']:
            for index, record in enumerate(data['evidence'], 1):
                block = tk.Frame(inner, bg=PAPER['surface'])
                block.pack(fill='x', pady=(0, 16))
                row = tk.Frame(block, bg=PAPER['surface'])
                row.pack(fill='x', anchor='w')
                ui.Chip(row, ui.CATEGORY.get(record.get('category'), record.get('category', '证据')),
                        command=None).pack(side='left')
                ui.mono(row, f'证据 {index} · {record.get("section", "")}', size=8).pack(
                    side='left', padx=(8, 0))
                body = ui.text(block, record.get('text', ''), size=10, wraplength=wrap)
                body.pack(fill='x', pady=(8, 6))
                self._wrap_labels.append(body)
                ui.text(block, '来源：' + source_name(record.get('url')) + ' · ' +
                        str(record.get('section', '')), size=9, fg=PAPER['ink3']).pack(
                    fill='x')
                actions = tk.Frame(block, bg=PAPER['surface'])
                actions.pack(fill='x', pady=(4, 0))
                if record.get('url'):
                    ui.FlatButton(actions, '打开原文 ↗', kind='link',
                                  command=lambda url=record['url']: webbrowser.open(url)).pack(side='left')
                ui.mono(actions, '核对 ' + str(record.get('checked_on', '未记录')) + ' · ' +
                        ui.status_text(record.get('review_status')), size=8).pack(
                    side='left', padx=(8, 0))
                ui.hairline(block).pack(fill='x', pady=(12, 0))
            interpretation = data['evidence'][0].get('interpretation')
            if interpretation:
                ui.text(inner, interpretation, size=9, fg=PAPER['ink3'],
                        wraplength=wrap).pack(fill='x', pady=(0, 14))
        else:
            empty = tk.Frame(inner, bg=PAPER['surface'])
            empty.pack(fill='x', pady=(2, 16))
            ui.text(empty, '尚无已收录的区域证据', size=10, fg=PAPER['ink']).pack(fill='x')
            ui.text(empty, '资料缺失不等于没有作用，也不表示安全。可切换物质或区域继续浏览。',
                    size=9, fg=PAPER['ink3'], wraplength=wrap).pack(fill='x', pady=(4, 0))

        section = tk.Frame(inner, bg=PAPER['surface'])
        section.pack(fill='x')
        ui.eyebrow(section, '关联结构').pack(anchor='w')
        chips = tk.Frame(section, bg=PAPER['surface'])
        chips.pack(fill='x', pady=(8, 0))
        for key in data['members']:
            ui.Chip(chips, REGIONS[key][0],
                    command=lambda region=key: self.select_region(region)).pack(
                side='left', padx=(0, 6), pady=(0, 6))
        note = ui.text(section, data['relation_note'], size=9, fg=PAPER['ink3'],
                       wraplength=wrap)
        note.pack(fill='x', pady=(4, 12))
        self._wrap_labels.append(note)

        unknown = tk.Frame(inner, bg=PAPER['surface'])
        unknown.pack(fill='x', pady=(2, 12))
        ui.eyebrow(unknown, '当前未计算').pack(anchor='w')
        ui.text(unknown, '个人效果强度、器官浓度、损伤程度及系统间因果影响。', size=9,
                fg=PAPER['ink3'], wraplength=wrap).pack(fill='x', pady=(4, 0))

    def _notify(self, context, data):
        if not self.on_state:
            return
        physiology = context.get('physiology', {}) or {}
        weight = physiology.get('weight_kg')
        age = physiology.get('age_years')
        genes = len(context.get('genes', []))
        baseline = '基线：' + ' · '.join(filter(None, (
            f'体重 {weight:g} kg' if isinstance(weight, (int, float)) else '体重未填写',
            f'年龄 {age:g}' if isinstance(age, (int, float)) else '年龄未填写',
            f'基因 {genes} 项')))
        self.on_state(dict(substance=substance_label(self.drug), baseline=baseline,
                           region=data['name'], evidence=len(data['evidence'])))

    def open_source(self):
        evidence = region_details(self.drug, self.selected)['evidence']
        if evidence and evidence[0].get('url'):
            webbrowser.open(evidence[0]['url'])
