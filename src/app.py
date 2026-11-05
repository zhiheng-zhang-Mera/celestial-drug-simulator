"""Local multi-drug research UI. No networking or telemetry."""
import json
import tkinter as tk
from tkinter import ttk, filedialog


def main():
    from src.simulation import load_catalog, simulate
    catalog = load_catalog()
    root = tk.Tk()
    root.title('Celestial Drug Simulator · 多药研究与证据')
    root.geometry('1080x760')
    root.minsize(800, 600)
    rows = []
    result = None
    context = {}
    ttk.Label(root, text='多药模拟器 · 方案与证据', font=('', 18)).pack(pady=8)
    ttk.Label(root, text='1–32 种物质 · 药品 / 补充剂 / 其他 · 本机离线研究').pack()
    editor = ttk.Frame(root, padding=10)
    editor.pack(fill='x')
    variables = {}
    specs = [('name', '名称', '合成 A'), ('dose_mg', '剂量 mg', '100'),
             ('volume_l', '容积 L', '10'), ('half_life_h', '半衰期 h', '4'),
             ('interval_h', '间隔 h', '8'), ('count', '次数', '3')]
    for col, (key, label, default) in enumerate(specs):
        ttk.Label(editor, text=label).grid(row=0, column=col, sticky='w')
        variables[key] = tk.StringVar(value=default)
        ttk.Entry(editor, textvariable=variables[key], width=15).grid(row=1, column=col, padx=3)
    kind = tk.StringVar(value='synthetic')
    route = tk.StringVar(value='iv_bolus')
    selection = tk.StringVar(value='fluconazole')
    source = tk.StringVar()
    category = tk.StringVar(value='medicine')
    options = ttk.Frame(root, padding=(10, 0))
    options.pack(fill='x')
    for label, variable, values in [('类型', kind, ('synthetic', 'custom', 'catalog')),
                                    ('途径', route, ('iv_bolus', 'oral', 'infusion')),
                                    ('来源条目', selection, tuple(catalog['compounds']))]:
        ttk.Label(options, text=label).pack(side='left', padx=4)
        ttk.Combobox(options, textvariable=variable, values=values, state='readonly', width=14).pack(side='left')
    ttk.Label(options, text='自定义来源/备注').pack(side='left', padx=4)
    ttk.Entry(options, textvariable=source, width=24).pack(side='left', fill='x', expand=True)
    classification = ttk.Frame(root, padding=(10, 4))
    classification.pack(fill='x')
    ttk.Label(classification, text='物质类别').pack(side='left')
    ttk.Combobox(classification, textvariable=category, state='readonly',
                 values=('medicine', 'supplement', 'botanical', 'food_beverage', 'other')).pack(side='left', padx=6)
    ttk.Label(classification, text='复方/补充剂成分未解析时，质量不能代表有效成分剂量。').pack(side='left')
    status = tk.StringVar(value='输入药物，点击添加；catalog 不自动填写或批准 PK 参数。')
    ttk.Label(root, textvariable=status, wraplength=1000).pack(padx=10, pady=6)
    actions = ttk.Frame(root)
    actions.pack(fill='x', padx=10)
    listing = ttk.Treeview(root, columns=('kind', 'route', 'dose', 'half'), height=5)
    listing.heading('#0', text='方案药物')
    for key, label in [('kind', '类型'), ('route', '途径'), ('dose', '剂量 mg'), ('half', '半衰期 h')]:
        listing.heading(key, text=label)
        listing.column(key, width=130)
    listing.pack(fill='x', padx=10, pady=8)
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True, padx=10, pady=8)
    report = tk.Text(notebook, wrap='word', state='disabled')
    notebook.add(report, text='联用与证据校验')
    exposure_frame = ttk.Frame(notebook)
    exposure = ttk.Treeview(exposure_frame, show='headings')
    yscroll = ttk.Scrollbar(exposure_frame, orient='vertical', command=exposure.yview)
    xscroll = ttk.Scrollbar(exposure_frame, orient='horizontal', command=exposure.xview)
    exposure.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
    yscroll.pack(side='right', fill='y'); xscroll.pack(side='bottom', fill='x')
    exposure.pack(fill='both', expand=True)
    notebook.add(exposure_frame, text='假设参数暴露 mg/L · 未含 DDI')

    def show(text):
        report.configure(state='normal'); report.delete('1.0', 'end')
        report.insert('1.0', text); report.configure(state='disabled')

    def invalidate(*_):
        nonlocal result
        result = None
        exposure.delete(*exposure.get_children())
        show('方案或编辑输入已变化，请重新计算。')

    def refresh():
        listing.delete(*listing.get_children())
        for index, item in enumerate(rows):
            listing.insert('', 'end', iid=str(index), text=item['name'],
                           values=(item['kind'], item['route'], item['dose_mg'], item['half_life_h']))
        invalidate()
        status.set(f'已添加 {len(rows)} 种；编辑器修改需点“更新选中”。')

    def read_editor():
        item = {key: (v.get().strip() if key == 'name' else
                      int(v.get()) if key == 'count' else float(v.get())) for key, v in variables.items()}
        item.update(kind=kind.get(), route=route.get(), category=category.get(),
                    compound_id=selection.get() if kind.get() == 'catalog' else '', source=source.get().strip())
        simulate([item])  # identical validation at the public service boundary
        return item

    def save_row(update=False):
        try:
            item = read_editor()
            candidate = list(rows)
            selected = listing.selection()
            if update:
                if not selected: raise ValueError('请先选中待更新药物。')
                candidate[int(selected[0])] = item
            else:
                candidate.append(item)
            simulate(candidate)
            rows[:] = candidate
            refresh()
        except (ValueError, OverflowError) as exc:
            status.set('输入被拒绝：' + str(exc))

    def load_row(_):
        selected = listing.selection()
        if not selected: return
        item = rows[int(selected[0])]
        for key, variable in variables.items(): variable.set(str(item[key]))
        kind.set(item['kind']); route.set(item['route']); source.set(item['source'])
        category.set(item.get('category', 'medicine'))
        if item['compound_id']: selection.set(item['compound_id'])

    def remove():
        for index in sorted((int(i) for i in listing.selection()), reverse=True): rows.pop(index)
        refresh()

    def calculate():
        nonlocal result
        invalidate()
        try:
            result = simulate(rows, context)
            lines = [result['overall'], result['explanation'],
                     '自定义曲线仅使用输入参数作假设计算，不能证明该药物的实际暴露。',
                     result['sampling']['note'],
                     '验证森林 HOLD_FOR_REVIEW；独立科学验证未完成。', '']
            lines.extend([result['context']['note'], '生理/基因模型：' + ', '.join(result['context']['gaps']),
                          '本方案尚未应用来源模型。Mayo / CPIC 实际来源与单药条件估计见“来源与基因机制”独立研究场景。'])
            for entry in result['entries']:
                lines.append(f"{entry['name']} [{entry['category']}] — {entry['status']} — {', '.join(entry['gaps']) or '合成示例'}")
                if entry.get('source_profile'):
                    lines.append(json.dumps(entry['source_profile'], ensure_ascii=False, indent=2))
            for pair in result['pairs']:
                lines.append('\n' + ' + '.join(pair['drugs']) + ' → ' + pair['status'])
                if not pair['evidence']: lines.append('快照中无匹配联用证据；不能解释为无交互。')
                for evidence in pair['evidence']:
                    lines.extend([evidence['source_location'], evidence['context'],
                                  f"研究观察 AUC 比率 {evidence['auc_ratio']}；当前方案预测：未准入",
                                  evidence['uncertainty'], evidence['applicability'], evidence['structural_check'],
                                  (evidence.get('source') or {}).get('url', '来源缺失：拒绝准入')])
            lines.extend(['\n输入 SHA256: ' + result['input_sha256'], '证据 SHA256: ' + result['snapshot_sha256']])
            show('\n'.join(lines))
            curves = result['curves']
            columns = ['time'] + [str(i) for i in range(len(curves))]
            exposure.configure(columns=columns)
            for col, title in zip(columns, ['时间 h'] + [c['name'] for c in curves]):
                exposure.heading(col, text=title); exposure.column(col, width=160, stretch=False)
            if curves:
                for index, time in enumerate(result['times_h']):
                    exposure.insert('', 'end', values=[f'{time:.6g}'] + [f"{c['values'][index]:.6g}" for c in curves])
            status.set(f"{len(rows)} 药 / {len(result['pairs'])} 对；{result['overall']}；曲线为合成或自定义 IV 假设计算，未含联用修正。")
        except (ValueError, OverflowError) as exc:
            status.set('输入被拒绝：' + str(exc))

    def export():
        if result is None:
            status.set('请先计算当前方案。'); return
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')])
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as stream:
                    json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
                status.set('报告已保存到本机：' + path)
            except OSError as exc: status.set('保存失败：' + str(exc))

    def save_context(candidate):
        nonlocal context
        context = candidate
        invalidate()
        status.set('本次生理/基因基线已保存到内存；未应用代谢修正。导出报告会包含这些数据。')

    def open_context():
        from src.context_dialog import edit_context
        edit_context(root, context, save_context)

    def open_sources():
        from src.pgx_dialog import open_pgx
        open_pgx(root)

    for text, command in [('生理与基因', open_context), ('添加药物', save_row), ('更新选中', lambda: save_row(True)),
                          ('删除选中', remove), ('计算与证据校验', calculate), ('导出本机报告', export)]:
        ttk.Button(actions, text=text, command=command).pack(side='left', padx=3)
    listing.bind('<<TreeviewSelect>>', load_row)
    ttk.Button(actions, text='来源与基因机制', command=open_sources).pack(side='left', padx=3)
    for variable in list(variables.values()) + [kind, route, selection, source, category]:
        variable.trace_add('write', invalidate)
    show('添加任意名称的自定义药物；来源未审查时保留缺口。不会自动联网或将研究观察值套用到当前方案。')
    root.mainloop()


if __name__ == '__main__':
    main()
