"""Multi-drug regimen workspace, redesigned around three visible inputs.

Names alone are enough to review mechanism evidence; dose and interval stay
optional.  Everything else moved into a disclosure that still performs the same
job as before, and the analysis output is read as structured sections instead of
a string wall.  Business calls (simulate / analyze_labels / normalize_context)
are unchanged.
"""
import copy
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog
import webbrowser

from src.simulation import simulate
from src import report_model
from src import ui_theme as ui

PAPER = ui.PAPER
ROUTES = {'口服 / 片剂': 'oral', '经皮': 'transdermal', '舌下': 'sublingual', '注射': 'injection',
          '其他': 'other', '静脉推注 · 假设模型': 'iv_bolus', '输注': 'infusion'}
ROUTE_LABELS = {value: label for label, value in ROUTES.items()}
CATEGORY_LABELS = {'medicine': '药品', 'supplement': '补充剂', 'botanical': '植物制品',
                   'food_beverage': '食品 / 饮料', 'other': '其他'}
CATEGORY_VALUES = {label: code for code, label in CATEGORY_LABELS.items()}
KIND_LABELS = {'catalog': '来源库', 'custom': '自定义', 'synthetic': '合成模型'}
NAME_SUGGESTIONS = ('戊酸雌二醇', '雌二醇', '比卡鲁胺', '氟康唑', '咪达唑仑', '托法替布',
                    'atomoxetine')


def study_lines(evidence):
    return [evidence['source_location'], evidence['context'], evidence['uncertainty'],
            '适用性：' + evidence['applicability'], '来源结构校验：' + evidence['structural_check'],
            f"研究观察 AUC 比率：{evidence['auc_ratio']}；当前方案预测：未准入。",
            (evidence.get('source') or {}).get('url', '来源缺失：拒绝准入')]


def editor_item(values, route, custom=False, advanced=False, category='medicine'):
    from src.drug_library import resolve_name, profile_for
    name = values.get('name', '').strip()
    identity = resolve_name(name) if not custom and not advanced else None
    if identity is None and not custom and not advanced:
        # Curated aliases (e.g. 戊酸雌二醇 → estradiol) resolve to the canonical
        # identity for label/profile lookup; the display name stays user input.
        candidate = report_model.resolve_identity(name)
        if candidate and profile_for(candidate, route):
            identity = candidate
    profile = profile_for(identity, route) if identity else None

    def number(key, integer=False):
        raw = values.get(key, '')
        value = '' if raw is None else str(raw).strip()
        return (int(value) if integer else float(value)) if value else None

    item = dict(name=name, kind='catalog' if identity else 'custom', compound_id=identity or '',
                category=category, route=route, source=values.get('source', '').strip(),
                dose_mg=number('dose_mg'), interval_h=number('interval_h'), count=number('count', True),
                model_mode='evidence', volume_l=None, half_life_h=(profile or {}).get('half_life_h'))
    if advanced:
        item.update(kind='synthetic', model_mode='synthetic', volume_l=number('volume_l'),
                    half_life_h=number('half_life_h'))
    if profile:
        item['parameter_source'] = profile
    simulate([item])
    return item


class RegimenWorkspace(tk.Frame):
    def __init__(self, parent, tabs=None, on_data_state=None):
        super().__init__(parent, bg=PAPER['bg'])
        self.rows = []
        self.result = None
        self.context = {}
        self.body = None
        self.generation = 0
        self.busy = False
        self.mail = queue.Queue()
        self.tabs = tabs
        self.on_data_state = on_data_state
        self._report_labels = []
        self._build()
        self.after(100, self.poll)

    # ------------------------------------------------------------------ build
    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = tk.Frame(self, bg=PAPER['bg'], padx=24, pady=12)
        header.grid(row=0, column=0, sticky='ew')
        title = tk.Frame(header, bg=PAPER['bg'])
        title.pack(side='left')
        ui.text(title, '多药方案', size=15, weight='bold').pack(anchor='w')
        ui.text(title, '输入药名即可分析联用机制；剂量与间隔选填，默认参数按药物和途径匹配。',
                size=9, fg=PAPER['ink3']).pack(anchor='w', pady=(2, 0))
        actions = tk.Frame(header, bg=PAPER['bg'])
        actions.pack(side='right')
        ui.FlatButton(actions, '导出报告', kind='quiet', command=self.export).pack(
            side='left', padx=(0, 10))
        ui.FlatButton(actions, '分析联用机制', kind='primary', command=self.calculate).pack(
            side='left')

        # editor ------------------------------------------------------------
        card = tk.Frame(self, bg=PAPER['surface'], highlightthickness=1,
                        highlightbackground=PAPER['line'])
        card.grid(row=1, column=0, sticky='ew', padx=24)
        inner = tk.Frame(card, bg=PAPER['surface'], padx=16, pady=14)
        inner.pack(fill='x')
        fields = tk.Frame(inner, bg=PAPER['surface'])
        fields.pack(fill='x')
        self.variables = {key: tk.StringVar() for key in
                          ('name', 'dose_mg', 'interval_h', 'count', 'source', 'volume_l', 'half_life_h')}
        specs = (('name', '药物名称', 26), ('dose_mg', '剂量 mg · 可选', 12),
                 ('interval_h', '用药间隔 h · 可选', 12))
        for column, (key, label, width) in enumerate(specs):
            cell = tk.Frame(fields, bg=PAPER['surface'])
            cell.grid(row=0, column=column, sticky='ew', padx=(0, 12))
            ui.text(cell, label, size=9, fg=PAPER['ink2'], bg=PAPER['surface']).pack(anchor='w')
            if key == 'name':
                widget = ttk.Combobox(cell, textvariable=self.variables[key],
                                      values=NAME_SUGGESTIONS, width=width,
                                      style='Paper.TCombobox')
                widget.bind('<KeyRelease>', self._filter_names)
                self.name_combo = widget
            else:
                widget = ttk.Entry(cell, textvariable=self.variables[key], width=width,
                                   style='Paper.TEntry')
            widget.pack(fill='x', pady=(4, 0))
        add_cell = tk.Frame(fields, bg=PAPER['surface'])
        add_cell.grid(row=0, column=3, sticky='s')
        ui.FlatButton(add_cell, '添加到方案', kind='primary', command=self.add).pack(
            anchor='e', pady=(0, 1))
        fields.columnconfigure(0, weight=1)

        self.defaults = tk.StringVar()
        defaults = ui.text(inner, '', size=8, fg=PAPER['ink3'], wraplength=980)
        defaults.configure(textvariable=self.defaults)
        defaults.pack(fill='x', pady=(12, 0))
        self._defaults_label = defaults

        self.more = ui.Disclosure(inner, '更多选项 · 途径 / 次数 / 类别 / 在线 / 合成参数',
                                  bg=PAPER['surface'])
        self.more.pack(fill='x', pady=(6, 0))
        more = self.more.body
        options = tk.Frame(more, bg=PAPER['surface'])
        options.pack(fill='x')
        self.route = tk.StringVar(value='口服 / 片剂')
        self.category = tk.StringVar(value='药品')
        route_cell = tk.Frame(options, bg=PAPER['surface'])
        route_cell.pack(side='left', padx=(0, 16))
        ui.text(route_cell, '给药途径 / 剂型', size=9, fg=PAPER['ink2']).pack(anchor='w')
        ttk.Combobox(route_cell, textvariable=self.route, values=tuple(ROUTES), width=18,
                     state='readonly', style='Paper.TCombobox').pack(anchor='w', pady=(4, 0))
        count_cell = tk.Frame(options, bg=PAPER['surface'])
        count_cell.pack(side='left', padx=(0, 16))
        ui.text(count_cell, '用药次数 · 可选', size=9, fg=PAPER['ink2']).pack(anchor='w')
        ttk.Entry(count_cell, textvariable=self.variables['count'], width=10,
                  style='Paper.TEntry').pack(anchor='w', pady=(4, 0))
        category_cell = tk.Frame(options, bg=PAPER['surface'])
        category_cell.pack(side='left')
        ui.text(category_cell, '物质类别', size=9, fg=PAPER['ink2']).pack(anchor='w')
        ttk.Combobox(category_cell, textvariable=self.category, values=tuple(CATEGORY_LABELS.values()),
                     width=12, state='readonly', style='Paper.TCombobox').pack(
            anchor='w', pady=(4, 0))

        switches = tk.Frame(more, bg=PAPER['surface'])
        switches.pack(fill='x', pady=(10, 0))
        self.custom = tk.BooleanVar()
        self.advanced = tk.BooleanVar()
        self.online = tk.BooleanVar(value=True)
        self.online.trace_add('write', self._online_changed)
        ui.checkbox(switches, '按自定义物质处理', self.custom).pack(side='left')
        ui.checkbox(switches, '优先在线查询（失败时使用离线资料）', self.online).pack(
            side='left', padx=(18, 0))
        ui.checkbox(switches, '高级：合成 IV 假设曲线', self.advanced,
                    command=self.toggle_advanced).pack(side='left', padx=(18, 0))

        self.advanced_box = tk.Frame(more, bg=PAPER['surface2'], padx=12, pady=10)
        ui.text(self.advanced_box, '合成模型参数 · 仅用于假设曲线，不代表所填药物的真实暴露。',
                size=8, fg=PAPER['ink3'], bg=PAPER['surface2']).pack(anchor='w', pady=(0, 6))
        advanced_fields = tk.Frame(self.advanced_box, bg=PAPER['surface2'])
        advanced_fields.pack(fill='x')
        for key, label, width in (('volume_l', '表观容积 L', 10), ('half_life_h', '半衰期 h', 10),
                                  ('source', '来源 / 备注', 26)):
            cell = tk.Frame(advanced_fields, bg=PAPER['surface2'])
            cell.pack(side='left', padx=(0, 12))
            ui.text(cell, label, size=9, fg=PAPER['ink2'], bg=PAPER['surface2']).pack(anchor='w')
            ttk.Entry(cell, textvariable=self.variables[key], width=width,
                      style='Paper.TEntry').pack(anchor='w', pady=(4, 0))

        # work area: scheme on the left, evidence workspace on the right ------
        workspace = tk.Frame(self, bg=PAPER['bg'], padx=24, pady=10)
        workspace.grid(row=2, column=0, sticky='nsew')
        workspace.rowconfigure(0, weight=1)
        workspace.columnconfigure(0, minsize=420)
        workspace.columnconfigure(1, weight=1)
        self._workspace = workspace

        left = tk.Frame(workspace, bg=PAPER['bg'])
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 16))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        plan_head = tk.Frame(left, bg=PAPER['bg'])
        plan_head.grid(row=0, column=0, sticky='ew', pady=(0, 6))
        ui.eyebrow(plan_head, '方案').pack(side='left')
        self.count = tk.StringVar(value='尚未添加')
        tk.Label(plan_head, textvariable=self.count, font=(ui.FONT, 9), fg=PAPER['ink3'],
                 bg=PAPER['bg']).pack(side='left', padx=(8, 0))
        buttons = tk.Frame(plan_head, bg=PAPER['bg'])
        buttons.pack(side='right')
        ui.FlatButton(buttons, '更新选中', kind='quiet',
                      command=lambda: self.add(True)).pack(side='left', padx=(0, 6))
        ui.FlatButton(buttons, '删除选中', kind='quiet', command=self.remove).pack(side='left')

        listing_frame = tk.Frame(left, bg=PAPER['surface'], highlightthickness=1,
                                 highlightbackground=PAPER['line'])
        listing_frame.grid(row=1, column=0, sticky='nsew')
        listing_frame.rowconfigure(0, weight=1)
        listing_frame.columnconfigure(0, weight=1)
        self.listing = ttk.Treeview(listing_frame, columns=('route', 'dose', 'half'),
                                    selectmode='browse', style='Paper.Treeview')
        self.listing.heading('#0', text='药物 / 身份', anchor='w')
        self.listing.column('#0', width=150, anchor='w')
        for key, label, width in (('route', '途径', 88), ('dose', '剂量 mg', 72),
                                  ('half', '半衰期 h', 96)):
            self.listing.heading(key, text=label, anchor='w')
            self.listing.column(key, width=width, anchor='w')
        scroll = ttk.Scrollbar(listing_frame, orient='vertical', command=self.listing.yview,
                               style='Paper.Vertical.TScrollbar')
        scroll.grid(row=0, column=1, sticky='ns')
        self.listing.configure(yscrollcommand=scroll.set)
        self.listing.grid(row=0, column=0, sticky='nsew')
        self.listing.bind('<<TreeviewSelect>>', self.load_row)
        self._listing_hint = ui.text(left, '选中一行后可更新或删除；在「人体作用」中可载入该行。',
                                     size=8, fg=PAPER['ink3'], wraplength=350)
        self._listing_hint.grid(row=2, column=0, sticky='w', pady=(6, 0))

        right = tk.Frame(workspace, bg=PAPER['bg'])
        right.grid(row=0, column=1, sticky='nsew')
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        results_head = tk.Frame(right, bg=PAPER['bg'])
        results_head.grid(row=0, column=0, sticky='ew', pady=(0, 6))
        from src.navigation import SegmentedNav
        self.results = SegmentedNav(results_head, size=10, on_change=self._show_result)
        self.results.pack(side='left')
        self.results.add('report', '联用机制与证据')
        self.results.add('exposure', '假设曲线数据')

        stack = tk.Frame(right, bg=PAPER['bg'])
        stack.grid(row=1, column=0, sticky='nsew')
        stack.rowconfigure(0, weight=1)
        stack.columnconfigure(0, weight=1)
        self.report_host = tk.Frame(stack, bg=PAPER['surface'], highlightthickness=1,
                                    highlightbackground=PAPER['line'])
        self.exposure_host = tk.Frame(stack, bg=PAPER['surface'], highlightthickness=1,
                                      highlightbackground=PAPER['line'])
        for frame in (self.report_host, self.exposure_host):
            frame.grid(row=0, column=0, sticky='nsew')
        self.report = ui.ScrollArea(self.report_host, bg=PAPER['surface'])
        self.report.pack(fill='both', expand=True, padx=(18, 6), pady=12)
        self.report.canvas.bind('<Configure>', self._report_canvas_resized, add='+')
        exposure_head = tk.Frame(self.exposure_host, bg=PAPER['surface'], padx=14, pady=10)
        exposure_head.pack(fill='x')
        ui.text(exposure_head, '假设曲线数据', size=9, fg=PAPER['ink2']).pack(side='left')
        ui.text(exposure_head, '仅在高级合成模式下生成，不代表真实暴露。', size=8,
                fg=PAPER['ink3']).pack(side='left', padx=(10, 0))
        self.exposure = ttk.Treeview(self.exposure_host, show='headings', style='Paper.Treeview')
        self.exposure.pack(fill='both', expand=True, padx=14, pady=(0, 12))
        self._show_result('report')

        status_row = tk.Frame(self, bg=PAPER['bg'], padx=24, pady=6)
        status_row.grid(row=3, column=0, sticky='ew')
        self.status = tk.StringVar(value='等待添加药物。')
        tk.Label(status_row, textvariable=self.status, font=(ui.FONT, 8), fg=PAPER['ink3'],
                 bg=PAPER['bg'], anchor='w').pack(side='left')
        self.bind('<Configure>', self._resized)

        for value in list(self.variables.values()) + [self.route, self.custom, self.category,
                                                      self.online, self.advanced]:
            value.trace_add('write', self.invalidate)
        self.invalidate()
        if self.on_data_state:
            self.on_data_state(self.online.get())

    # ------------------------------------------------------------------ input
    def _filter_names(self, event):
        if event.keysym in ('Left', 'Right', 'Up', 'Down', 'Return', 'Escape', 'Tab'):
            return
        typed = self.variables['name'].get().strip().casefold()
        values = NAME_SUGGESTIONS if not typed else [
            name for name in NAME_SUGGESTIONS if typed in name.casefold()]
        self.name_combo.configure(values=values or NAME_SUGGESTIONS)

    def _report_wrap(self):
        width = self.report.canvas.winfo_width()
        if width <= 1:
            width = self.report.winfo_width()
        if width <= 1:
            # The report pane may not be mapped yet when an async result lands.
            # Derive the reading width from the window geometry (left column +
            # gutters are fixed) so the first render already wraps correctly.
            width = self.winfo_width() - 517
        return max(260, max(340, width) - 50)

    def _apply_report_wrap(self):
        wrap = self._report_wrap()
        for label in self._report_labels:
            try:
                if label.winfo_exists():
                    label.configure(wraplength=wrap)
            except tk.TclError:
                pass

    def _report_canvas_resized(self, event):
        if event.widget is self.report.canvas and event.width > 1:
            self._apply_report_wrap()

    def _resized(self, event):
        if event.widget is not self:
            return
        minsize = 400 if event.width < 1150 else 420
        try:
            self._workspace.columnconfigure(0, minsize=minsize)
        except (AttributeError, tk.TclError):
            pass
        self._apply_report_wrap()

    def _online_changed(self, *_):
        if self.on_data_state:
            self.on_data_state(self.online.get())

    def _show_result(self, key):
        (self.report_host if key == 'report' else self.exposure_host).tkraise()

    def toggle_advanced(self):
        if self.advanced.get():
            self.advanced_box.pack(fill='x', pady=(10, 0))
        else:
            self.advanced_box.pack_forget()

    # --------------------------------------------------------------- render
    def show(self, message):
        inner = self.report.clear()
        self._report_labels = []
        label = ui.text(inner, message, size=9, fg=PAPER['ink3'], wraplength=self._report_wrap())
        label.pack(fill='x')
        self._report_labels.append(label)

    def invalidate(self, *_):
        self.generation += 1
        self.result = None
        self.exposure.delete(*self.exposure.get_children())
        self.show('输入或方案已变化，点击“分析联用机制”更新结果。')
        from src.drug_library import resolve_name, profile_for
        identity = resolve_name(self.variables['name'].get()) if not self.custom.get() else None
        p = profile_for(identity, ROUTES[self.route.get()]) if identity else None
        if self.advanced.get():
            self.defaults.set('高级模式需要手动假设参数，结果仅用于合成 IV 模型。')
        elif p:
            half = p.get('half_life_h')
            self.defaults.set(
                f"资料默认：{p.get('name', identity)} · {p.get('formulation', '')} · "
                f"半衰期 {str(half) + ' h' if half else '未提供匹配值'}。{p.get('parameter_note', '')}")
        else:
            self.defaults.set('自定义 / 未识别物质：可添加并查看证据缺口；不会按同名药物继承参数。')

    def add(self, update=False):
        try:
            item = editor_item({k: v.get() for k, v in self.variables.items()},
                               ROUTES[self.route.get()], self.custom.get(), self.advanced.get(),
                               CATEGORY_VALUES.get(self.category.get(), 'medicine'))
            candidate = list(self.rows)
            selected = self.listing.selection()
            if update:
                if not selected:
                    raise ValueError('请先选择要更新的药物。')
                candidate[int(selected[0])] = item
            else:
                candidate.append(item)
            simulate(candidate, self.context)
            self.rows = candidate
            self.refresh()
        except (ValueError, OverflowError) as exc:
            self.status.set('无法添加：' + str(exc))

    def refresh(self):
        self.listing.delete(*self.listing.get_children())
        for i, item in enumerate(self.rows):
            self.listing.insert('', 'end', iid=str(i), text=item['name'] + ' · ' +
                                KIND_LABELS.get(item['kind'], item['kind']),
                                values=(ROUTE_LABELS.get(item['route'], item['route']),
                                        item.get('dose_mg') or '未填写',
                                        item.get('half_life_h') or '无匹配值'))
        self.count.set(f'{len(self.rows)} 种物质' if self.rows else '尚未添加')
        self.invalidate()
        self.status.set(f'已添加 {len(self.rows)} 种。可直接分析，缺少药代参数不会阻止机制查询。')
        if self.body:
            self.body.drug = None
            self.body.choice.set('未选择物质')
            self.body.render()

    def selected_item(self):
        selected = self.listing.selection()
        return dict(self.rows[int(selected[0])]) if selected else None

    def load_row(self, _):
        item = self.selected_item()
        if not item:
            return
        for key, var in self.variables.items():
            var.set('' if item.get(key) is None else str(item[key]))
        self.route.set(next(label for label, code in ROUTES.items() if code == item['route']))
        self.category.set(CATEGORY_LABELS.get(item.get('category', 'medicine'), '药品'))
        self.custom.set(item['kind'] == 'custom')
        self.advanced.set(item.get('model_mode') == 'synthetic')
        self.toggle_advanced()
        if self.body:
            self.body.drug = item
            self.body.choice.set('方案选中 / ' + item['name'])
            self.body.render()

    def remove(self):
        for i in sorted((int(i) for i in self.listing.selection()), reverse=True):
            self.rows.pop(i)
        self.refresh()

    # --------------------------------------------------------------- actions
    def calculate(self):
        if self.busy:
            self.status.set('查询正在进行；输入变化后旧结果会自动作废。')
            return
        self.invalidate()
        self.results.select('report')
        try:
            result = simulate(copy.deepcopy(self.rows), copy.deepcopy(self.context))
        except (ValueError, OverflowError) as exc:
            self.status.set(str(exc))
            return
        self.busy = True
        generation = self.generation
        items = copy.deepcopy(self.rows)
        online = self.online.get()
        self.status.set('查询公开药物说明书中…仅发送药物成分名称，不发送剂量、生理或基因信息。'
                        if online else '正在校验离线资料…')

        def work():
            try:
                from src.drug_library import analyze_labels
                result['label_analysis'] = analyze_labels(items, online=online)
                self.mail.put((generation, result, None))
            except Exception as exc:  # the worker must always answer the UI
                self.mail.put((generation, None, str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        try:
            generation, result, error = self.mail.get_nowait()
            self.busy = False
            if generation != self.generation:
                self.status.set('查询结束，但输入已变化；旧结果已丢弃，请重新分析。')
            elif error:
                self.status.set('查询失败：' + error)
            else:
                self.result = result
                self.display_result(result)
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def display_result(self, result):
        labels = result.get('label_analysis') or {}
        inner = self.report.clear()
        self._report_labels = []
        wrap = self._report_wrap()
        overview = report_model.overview_view(result, labels)
        individuals = report_model.individual_view(result, labels)
        interactions = report_model.interaction_view(result, labels)

        # 1. 方案总览 --------------------------------------------------------
        self._section(inner, '方案总览', index='01')
        self._overview_block(inner, overview, wrap)

        # 2. 个体作用（每种物质） -------------------------------------------
        self._section(inner, '个体作用', index='02',
                      note=f'{len(individuals)} 种物质')
        if individuals:
            for person in individuals:
                self._individual_block(inner, person, wrap)
        else:
            self._place(new=inner, text='当前方案没有可展示的物质记录。', wrap=wrap)

        # 3. 交叉作用（每对物质） -------------------------------------------
        self._section(inner, '交叉作用', index='03',
                      note=f'{len(interactions)} 对物质')
        if interactions:
            for pair in interactions:
                self._interaction_block(inner, pair, wrap)
        else:
            self._place(new=inner, text='当前只有一种物质，没有可展示的交叉作用。',
                        wrap=wrap)

        # 4. 证据与边界 ------------------------------------------------------
        self._section(inner, '证据与边界', index='04')
        self._boundary_block(inner, result, overview, wrap)

        self.status.set(
            f"已分析 {len(self.rows)} 种 / {len(result['pairs'])} 对；"
            '个体作用与交叉作用见报告，机制线索不等同于临床配伍结论。')
        self.after_idle(self._apply_report_wrap)

        curves = result['curves']
        columns = ['time'] + [str(i) for i in range(len(curves))]
        self.exposure.configure(columns=columns)
        for col, title in zip(columns, ['时间 h'] + [c['name'] for c in curves]):
            self.exposure.heading(col, text=title)
            self.exposure.column(col, width=150, anchor='e')
        for i, t in enumerate(result['times_h']):
            self.exposure.insert('', 'end', values=[f'{t:.6g}'] + [
                f"{c['values'][i]:.6g}" for c in curves])

    # ------------------------------------------------------- report sections
    def _place(self, new, text, wrap):
        label = ui.text(new, text, size=9, fg=PAPER['ink3'], wraplength=wrap)
        label.pack(fill='x', pady=(0, 8))
        self._report_labels.append(label)

    def _overview_block(self, parent, overview, wrap):
        counts = overview['counts']
        ui.metric_row(parent, [
            (counts['substances'], '物质数'),
            (counts['pairs'], '交叉对数'),
            (counts['mechanism_pairs'], '有机制线索的对数'),
            (counts['data_gaps'], '数据缺口数'),
        ], bg=PAPER['surface']).pack(fill='x', pady=(0, 10))
        note = tk.Frame(parent, bg=PAPER['bgElevated'], padx=12, pady=10)
        note.pack(fill='x')
        tk.Frame(note, bg=PAPER['accent'], width=2).pack(side='left', fill='y')
        body = tk.Frame(note, bg=PAPER['bgElevated'], padx=10)
        body.pack(side='left', fill='x', expand=True)
        label = ui.text(body, overview['disclaimer'], size=9, fg=PAPER['ink2'],
                        bg=PAPER['bgElevated'], wraplength=max(220, wrap - 34))
        label.pack(fill='x')
        self._report_labels.append(label)
        ui.text(body, '数据缺口数 = 所有物质缺口标记之和。', size=8, fg=PAPER['ink3'],
                bg=PAPER['bgElevated'], wraplength=max(220, wrap - 34)).pack(
            fill='x', pady=(4, 0))

    def _individual_block(self, parent, person, wrap):
        base = PAPER['bgElevated']
        card = ui.card(parent, bg=base)
        card.outer.pack(fill='x', pady=(0, 10))

        head = tk.Frame(card, bg=base)
        head.pack(fill='x')
        ui.text(head, person['name'], size=11, weight='bold', bg=base).pack(side='left')
        ui.Chip(head, KIND_LABELS.get(person['kind'], person['kind']),
                bg=PAPER['surface2'], fg=PAPER['ink2']).pack(side='left', padx=(8, 0))
        ui.status_pill(head, person['status'], bg=base).pack(side='left', padx=(8, 0))
        ui.status_pill(head, person['record_status'], bg=base).pack(side='right')

        meta = tk.Frame(card, bg=base)
        meta.pack(fill='x', pady=(3, 0))
        if person['source_url']:
            ui.FlatButton(meta, '打开来源原文 ↗', kind='link',
                          command=lambda url=person['source_url']: webbrowser.open(url)).pack(
                side='left')
        retrieved = str(person.get('retrieved_at') or '')
        if retrieved:
            ui.mono(meta, '获取 ' + retrieved[:10], size=8).pack(side='left', padx=(8, 0))

        kv = tk.Frame(card, bg=base)
        kv.pack(fill='x', pady=(8, 0))
        for label, value in (
                ('途径', ROUTE_LABELS.get(person['route'], person['route'] or '未填写')),
                ('剂量', self._number_text(person.get('dose_mg'), 'mg')),
                ('间隔', self._number_text(person.get('interval_h'), 'h'))):
            ui.kv_row(kv, label, value, bg=base).pack(side='left', padx=(0, 16))
        if person.get('category') not in (None, '', 'medicine'):
            ui.kv_row(card, '类别', CATEGORY_LABELS.get(person['category'], '未填写'),
                      bg=base).pack(fill='x', pady=(4, 0))

        self._card_heading(card, '个体机制摘要', base)
        mechanism = person['mechanism']
        body = ui.text(card, mechanism['text'], size=10, fg=PAPER['ink'], bg=base,
                       wraplength=max(220, wrap - 32))
        body.pack(fill='x', pady=(3, 0))
        self._report_labels.append(body)
        source_note = {
            'record_facts': '来源：标签记录中的机制段落摘要',
            'profile_facts': '来自 profile 的机制事实摘要',
            'record_summary': '来源：标签记录摘要（非机制段落）',
        }.get(mechanism['source'])
        if source_note:
            ui.mono(card, source_note, size=7).pack(anchor='w', pady=(2, 0))

        pd = person.get('pd')
        if pd:
            self._card_heading(card, '性激素表达作用（PD）', base)
            summary = ui.text(card, pd['summary'], size=10, fg=PAPER['ink'], bg=base,
                              wraplength=max(220, wrap - 32))
            summary.pack(fill='x', pady=(3, 0))
            self._report_labels.append(summary)
            target = ' · '.join(part for part in (
                '靶点：' + pd['target'] if pd.get('target') else '',
                '类别：' + pd['drug_class'] if pd.get('drug_class') else '') if part)
            if target:
                ui.text(card, target, size=8, fg=PAPER['ink3'], bg=base).pack(
                    fill='x', pady=(2, 0))
            for effect in (pd.get('effects') or [])[:3]:
                bullet = ui.text(card, '· ' + effect, size=9, fg=PAPER['ink2'], bg=base,
                                 wraplength=max(220, wrap - 40))
                bullet.pack(fill='x', pady=(2, 0))
                self._report_labels.append(bullet)
            grade = f"证据等级：{pd.get('evidence_grade_label') or pd.get('evidence_grade') or '未记录'}"
            ui.text(card, grade, size=8, fg=PAPER['ink3'], bg=base).pack(anchor='w', pady=(4, 0))
            if pd.get('evidence_grade'):
                ui.mono(card, pd['evidence_grade'], size=7).pack(anchor='w', pady=(1, 0))
            if pd.get('alias_note'):
                alias = ui.text(card, pd['alias_note'], size=8, fg=PAPER['ink3'], bg=base,
                                wraplength=max(220, wrap - 32))
                alias.pack(fill='x', pady=(2, 0))
                self._report_labels.append(alias)
            if pd.get('uncertainty'):
                uncertainty = ui.text(card, '不确定性：' + pd['uncertainty'], size=8,
                                      fg=PAPER['ink3'], bg=base,
                                      wraplength=max(220, wrap - 32))
                uncertainty.pack(fill='x', pady=(2, 0))
                self._report_labels.append(uncertainty)
            if pd.get('sources'):
                links = tk.Frame(card, bg=base)
                links.pack(fill='x', pady=(3, 0))
                ui.eyebrow(links, 'PD 来源', bg=base).pack(anchor='w')
                for source_index, source in enumerate(pd['sources'], 1):
                    if source.get('url'):
                        label = source.get('label') or f'来源 {source_index}'
                        ui.FlatButton(links, f'{label} ↗', kind='link',
                                      command=lambda url=source['url']: webbrowser.open(url)).pack(
                            anchor='w', pady=(1, 0))
                    elif source.get('label'):
                        ui.text(links, source['label'], size=8, fg=PAPER['ink3'],
                                bg=base, wraplength=max(220, wrap - 32)).pack(
                            anchor='w', pady=(1, 0))

        self._card_heading(card, '影响部位', base)
        if person['regions']:
            for region in person['regions']:
                chip = ui.Chip(
                    card,
                    f"{region['name']} · {ui.CATEGORY.get(region['category'], region['category'] or '证据')}",
                    command=lambda region=region, view=person: self._open_region(
                        view['index'], region['id']),
                    bg=PAPER['accentSoft'], fg=PAPER['accent'])
                chip.pack(anchor='w', pady=(4, 0))
                region_text = ui.text(card, region['text'], size=9, fg=PAPER['ink2'],
                                      bg=base, wraplength=max(220, wrap - 48))
                region_text.pack(fill='x', pady=(2, 0), padx=(2, 0))
                self._report_labels.append(region_text)
        else:
            ui.text(card, report_model.MISSING_REGIONS, size=9, fg=PAPER['ink3'],
                    bg=base, wraplength=max(220, wrap - 32)).pack(fill='x', pady=(3, 0))

        self._card_heading(card, '证据缺口', base)
        if person['gaps']:
            for gap in person['gaps']:
                row = tk.Frame(card, bg=base)
                row.pack(fill='x', pady=(2, 0))
                ui.text(row, gap['label'], size=9, fg=PAPER['ink2'], bg=base).pack(side='left')
                ui.mono(row, gap['code'], size=7).pack(side='left', padx=(8, 0))
        else:
            ui.text(card, '未记录缺口代码。', size=9, fg=PAPER['ink3'], bg=base).pack(
                anchor='w', pady=(3, 0))

        if person['record_error']:
            error = ui.text(card, '在线查询说明：' + person['record_error'], size=8,
                            fg=PAPER['ink3'], bg=base, wraplength=max(220, wrap - 32))
            error.pack(fill='x', pady=(6, 0))
            self._report_labels.append(error)

    def _interaction_block(self, parent, pair, wrap):
        base = PAPER['bgElevated']
        card = ui.card(parent, bg=base)
        card.outer.pack(fill='x', pady=(0, 10))

        head = tk.Frame(card, bg=base)
        head.pack(fill='x')
        ui.text(head, ' × '.join(pair['names']), size=11, weight='bold',
                bg=base).pack(side='left')
        ui.status_pill(head, pair['status'], bg=base).pack(side='left', padx=(8, 0))

        raw = tk.Frame(card, bg=base)
        raw.pack(fill='x', pady=(2, 0))
        ui.mono(raw, '目录状态 ' + (pair['result_status'] or '未记录'), size=7).pack(side='left')
        ui.mono(raw, '标签状态 ' + (pair['label_status'] or '未记录'), size=7).pack(
            side='left', padx=(12, 0))
        if pair.get('evidence_grade_label') or pair.get('evidence_grade'):
            grade = tk.Frame(card, bg=base)
            grade.pack(fill='x', pady=(2, 0))
            ui.text(grade, '证据等级：' + (pair.get('evidence_grade_label') or '未记录'),
                    size=8, fg=PAPER['ink2'], bg=base).pack(anchor='w')
            if pair.get('evidence_grade'):
                ui.mono(grade, pair['evidence_grade'], size=7).pack(anchor='w', pady=(1, 0))

        lines = tk.Frame(card, bg=base)
        lines.pack(fill='x', pady=(8, 0))
        ui.eyebrow(lines, '个体作用 · 交叉作用的两端', bg=base).pack(anchor='w')
        for caption, person, pd in (
                ('A · ' + pair['a']['name'], pair['a'], pair.get('pd_individual_a')),
                ('B · ' + pair['b']['name'], pair['b'], pair.get('pd_individual_b'))):
            row = tk.Frame(lines, bg=base)
            row.pack(fill='x', pady=(4, 0))
            ui.text(row, caption, size=9, weight='bold', fg=PAPER['ink'], bg=base).pack(anchor='w')
            if pd:
                pd_line = ui.text(row, 'PD：' + pd['summary'], size=9, fg=PAPER['ink'],
                                  bg=base, wraplength=max(220, wrap - 40))
                pd_line.pack(fill='x')
                self._report_labels.append(pd_line)
            line = ui.text(
                row, f"机制线索：{person['summary']} · 主要影响部位：{person['region_text']}",
                size=9, fg=PAPER['ink2'], bg=base, wraplength=max(220, wrap - 40))
            line.pack(fill='x')
            self._report_labels.append(line)

        self._card_heading(card, '交叉作用', base)
        cross = ui.text(card, pair['summary'], size=10, fg=PAPER['ink'], bg=base,
                        wraplength=max(220, wrap - 32))
        cross.pack(fill='x', pady=(3, 0))
        self._report_labels.append(cross)

        combined = pair.get('combined_effect')
        if combined:
            self._card_heading(card, '综合作用', base)
            if combined.get('headline'):
                headline = ui.text(card, combined['headline'], size=11, weight='bold',
                                   fg=PAPER['ink'], bg=base,
                                   wraplength=max(220, wrap - 32))
                headline.pack(fill='x', pady=(2, 0))
                self._report_labels.append(headline)
            for item in combined.get('items') or []:
                bullet = ui.text(card, '· ' + item, size=9, fg=PAPER['ink2'], bg=base,
                                 wraplength=max(220, wrap - 40))
                bullet.pack(fill='x', pady=(2, 0))
                self._report_labels.append(bullet)
            if combined.get('note'):
                note = ui.text(card, combined['note'], size=8, fg=PAPER['ink3'], bg=base,
                               wraplength=max(220, wrap - 32))
                note.pack(fill='x', pady=(3, 0))
                self._report_labels.append(note)

        if pair.get('not_computed'):
            boundary = ui.text(card, pair['not_computed'], size=8, fg=PAPER['ink3'],
                               bg=base, wraplength=max(220, wrap - 32))
            boundary.pack(fill='x', pady=(3, 0))
            self._report_labels.append(boundary)

        if pair['studies']:
            self._card_heading(card, '研究观察（仅展示，不预测）', base)
            for study in pair['studies']:
                self._study_row(card, study, wrap)
        else:
            ui.text(card, '本资料库未收录该组合的研究观察。', size=9, fg=PAPER['ink3'],
                    bg=base, wraplength=max(220, wrap - 32)).pack(fill='x', pady=(3, 0))

        sections = [section for section in (pair.get('disclosure_sections') or [])
                    if section.get('id') != 'combined_effect']
        if sections:
            self._card_heading(card, '详细披露（可展开）', base)
            for section in sections:
                disclosure = ui.Disclosure(card, section['title'], bg=base)
                disclosure.pack(fill='x', pady=(2, 0))
                body = disclosure.body
                if section.get('body'):
                    label = ui.text(body, section['body'], size=9, fg=PAPER['ink2'],
                                    bg=base, wraplength=max(210, wrap - 56))
                    label.pack(fill='x', pady=(2, 0))
                    self._report_labels.append(label)
                for item in section.get('items') or []:
                    line = tk.Frame(body, bg=base)
                    line.pack(fill='x', pady=(2, 0))
                    text = ui.text(line, '· ' + item['text'], size=9, fg=PAPER['ink2'],
                                   bg=base, wraplength=max(200, wrap - 70))
                    text.pack(fill='x')
                    self._report_labels.append(text)
                    source = str(item.get('source') or '')
                    if source.startswith('http'):
                        ui.FlatButton(line, '打开来源 ↗', kind='link',
                                      command=lambda url=source: webbrowser.open(url)).pack(
                            anchor='w')
                    elif source:
                        source_label = ui.mono(line, '来源：' + source, size=7,
                                               wraplength=max(200, wrap - 70))
                        source_label.pack(anchor='w')
                        self._report_labels.append(source_label)

        if pair['sources']:
            sources = tk.Frame(card, bg=base)
            sources.pack(fill='x', pady=(8, 0))
            ui.eyebrow(sources, '来源链接', bg=base).pack(anchor='w')
            for index, url in enumerate(pair['sources'], 1):
                ui.FlatButton(sources, f'来源 {index} ↗', kind='link',
                              command=lambda target=url: webbrowser.open(target)).pack(
                    anchor='w', pady=(1, 0))
        else:
            ui.text(card, '来源链接：未记录。', size=8, fg=PAPER['ink3'],
                    bg=base).pack(anchor='w', pady=(8, 0))

    def _study_row(self, parent, study, wrap):
        base = PAPER['surface2']
        block = tk.Frame(parent, bg=base, padx=10, pady=8)
        block.pack(fill='x', pady=(6, 0))
        ui.text(block, study['source_location'], size=9, weight='bold', bg=base).pack(fill='x')
        conditions = '；'.join(part for part in (study['population'], study['context']) if part)
        self._study_line(block, '研究人群与条件', conditions or '未记录', wrap)
        self._study_line(block, '不确定性', study['uncertainty'] or '未记录', wrap)
        applicability = ui.APPLICABILITY.get(study['applicability'],
                                             study['applicability'] or '未记录')
        structure = ui.STRUCTURAL.get(study['structural_check'],
                                      study['structural_check'] or '未记录')
        self._study_line(block, '适用性 / 结构校验', f'{applicability} · {structure}', wrap)
        ui.mono(block, f"{study['applicability'] or '未记录'} / "
                       f"{study['structural_check'] or '未记录'}", size=7).pack(
            anchor='w', pady=(1, 0))
        ratio = study['auc_ratio']
        observed = ui.text(
            block, f"研究观察 AUC 比率：{ratio if ratio is not None else '未记录'}；"
                   f"{study['prediction_text']}", size=8, fg=PAPER['ink2'], bg=base,
            wraplength=max(220, wrap - 54))
        observed.pack(fill='x', pady=(3, 0))
        self._report_labels.append(observed)
        if study['source_url']:
            ui.FlatButton(block, '打开来源原文 ↗', kind='link',
                          command=lambda url=study['source_url']: webbrowser.open(url)).pack(
                anchor='w')

    def _study_line(self, parent, label, value, wrap):
        base = PAPER['surface2']
        row = tk.Frame(parent, bg=base)
        row.pack(fill='x', pady=(2, 0))
        ui.text(row, label, size=8, fg=PAPER['ink3'], bg=base).pack(side='left', anchor='n')
        text = ui.text(row, value if value else '未记录', size=8, fg=PAPER['ink2'],
                       bg=base, wraplength=max(180, wrap - 90))
        text.pack(side='left', fill='x', expand=True, padx=(8, 0))
        self._report_labels.append(text)

    def _boundary_block(self, parent, result, overview, wrap):
        base = PAPER['surface']
        definitions = (
            ('标签事实', '来自官方标签记录与来源 profile 的可核对段落；保留在线 / 缓存 / 种子状态。'),
            ('机制推断', '由两条个体机制线索组合出的定性提示，不是该组合的临床试验结论。'),
            ('研究观察', '目录研究库收录的外部研究结果；仅展示，不进入本方案预测。'),
            ('边界', '不相乘、不生成数值风险、不输出个体暴露或效应预测。'),
        )
        block = tk.Frame(parent, bg=PAPER['bgElevated'], padx=12, pady=10)
        block.pack(fill='x', pady=(0, 10))
        for label, value in definitions:
            row = tk.Frame(block, bg=PAPER['bgElevated'])
            row.pack(fill='x', pady=(2, 0))
            ui.text(row, label, size=9, weight='bold', fg=PAPER['ink'],
                    bg=PAPER['bgElevated'], width=4).pack(side='left', anchor='n')
            text = ui.text(row, value, size=9, fg=PAPER['ink2'], bg=PAPER['bgElevated'],
                           wraplength=max(180, wrap - 130))
            text.pack(side='left', fill='x', expand=True, padx=(8, 0))
            self._report_labels.append(text)

        for line in (result.get('explanation', ''), overview['label_note'],
                     result['context'].get('note', '')):
            if not line:
                continue
            label = ui.text(parent, str(line), size=8, fg=PAPER['ink3'], wraplength=wrap)
            label.pack(fill='x', pady=(0, 2))
            self._report_labels.append(label)

        sampling = result.get('sampling') or {}
        if sampling.get('note'):
            label = ui.text(
                parent,
                f"采样：显示 {sampling.get('displayed_points', 0)} / "
                f"{sampling.get('original_points', 0)} 点；{sampling['note']}",
                size=8, fg=PAPER['ink3'], wraplength=wrap)
            label.pack(fill='x', pady=(0, 2))
            self._report_labels.append(label)

        label = ui.text(parent, overview['export_note'], size=8, fg=PAPER['ink3'],
                        wraplength=wrap)
        label.pack(fill='x', pady=(0, 2))
        self._report_labels.append(label)
        ui.mono(parent, '输入 SHA256：' + (overview['input_sha256'] or '未记录'),
                size=8).pack(fill='x', pady=(6, 0))
        if overview['snapshot_id']:
            ui.mono(parent, '来源快照：' + overview['snapshot_id'], size=8).pack(
                fill='x', pady=(1, 0))

    def _number_text(self, value, unit):
        if value is None or value == '':
            return '未填写'
        try:
            return f'{value:g} {unit}'
        except (TypeError, ValueError):
            return f'{value} {unit}'

    def _card_heading(self, parent, title, bg):
        ui.eyebrow(parent, title, bg=bg).pack(anchor='w', pady=(10, 0))

    def _open_region(self, index, region):
        """Select the region on the anatomy stage; never invents an effect."""
        if not self.body:
            return
        entries = (self.result or {}).get('entries') or []
        if not 0 <= index < len(entries):
            return
        self.body.drug = entries[index]
        self.body.select_region(region)
        if self.tabs:
            self.tabs.select('body')

    # ------------------------------------------------------------ result view
    def _section(self, parent, title, index=None, note=None):
        frame = tk.Frame(parent, bg=PAPER['surface'])
        frame.pack(fill='x', pady=(12, 6))
        row = tk.Frame(frame, bg=PAPER['surface'])
        row.pack(fill='x')
        if index:
            ui.mono(row, index, size=8, fg=PAPER['accent']).pack(side='left', padx=(0, 8))
        tk.Label(row, text=title, font=(ui.FONT, 12, 'bold'), fg=PAPER['ink'],
                 bg=PAPER['surface']).pack(side='left')
        if note:
            ui.text(row, note, size=8, fg=PAPER['ink3']).pack(side='right')
        ui.hairline(frame).pack(fill='x', pady=(7, 0))

    def export(self):
        if self.result is None:
            self.status.set('请先分析当前方案。')
            return
        path = filedialog.asksaveasfilename(defaultextension='.json',
                                            filetypes=[('JSON', '*.json')])
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as stream:
                    json.dump(self.result, stream, ensure_ascii=False, indent=2, allow_nan=False)
                self.status.set('已保存报告：' + path)
            except OSError as exc:
                self.status.set(str(exc))

    def open_context(self):
        from src.context_dialog import edit_context

        def save(context):
            self.context = context
            self.invalidate()
            if self.body:
                self.body.render()

        edit_context(self, self.context, save)

    def open_sources(self):
        from src.pgx_dialog import open_pgx
        open_pgx(self)
