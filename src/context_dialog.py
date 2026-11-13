"""Local research context editor: three first-screen fields, detail on demand."""
import tkinter as tk
from tkinter import ttk

from src.context import normalize_context
from src import ui_theme as ui

try:
    from celestial_help import attach_help
except ModuleNotFoundError:  # direct `python src/...` execution from the repository root
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from celestial_help import attach_help

PAPER = ui.PAPER
SEX_CHOICES = (('unknown', '未填写 / 未知'), ('female', '女性'), ('male', '男性'),
               ('intersex', '间性'))
HELP_TEXTS = {
    'context': (
        '这里填写可选的生理基线与基因记录，用于报告上下文，不用于自动诊断或剂量推荐。'
        '数据只保存在本机内存与本机报告文件，不上传；留空保持未知，不会推断。保存后旧报告失效，'
        '需要重新分析才能包含新上下文。'
    ),
}


def edit_context(parent, current, on_save):
    dialog = tk.Toplevel(parent)
    dialog.title('生理基线与基因 · 仅本机')
    dialog.geometry('680x340')
    dialog.minsize(640, 320)
    dialog.transient(parent.winfo_toplevel())
    dialog.grab_set()
    dialog.configure(background=PAPER['bg'])
    ui.setup(dialog)
    body = tk.Frame(dialog, bg=PAPER['bg'], padx=24, pady=18)
    body.pack(fill='both', expand=True)

    head = tk.Frame(body, bg=PAPER['bg'])
    head.pack(fill='x')
    ui.text(head, '生理基线与基因', size=15, weight='bold').pack(side='left')
    attach_help(head, 'context', HELP_TEXTS['context'],
                title='生理与基因').pack(side='left', padx=(8, 0))
    ui.text(body, '可留空；保存后旧报告失效。数据只保存在本机，不上传。', size=9,
            fg=PAPER['ink3']).pack(anchor='w', pady=(2, 14))

    card = tk.Frame(body, bg=PAPER['surface'], highlightthickness=1,
                   highlightbackground=PAPER['line'])
    card.pack(fill='x')
    inner = tk.Frame(card, bg=PAPER['surface'], padx=18, pady=16)
    inner.pack(fill='x')

    profile = current.get('physiology', {}) or {}
    fields = {}

    def field(parent_frame, key, label, width=14):
        cell = tk.Frame(parent_frame, bg=PAPER['surface'])
        cell.pack(side='left', padx=(0, 18))
        ui.text(cell, label, size=9, fg=PAPER['ink2']).pack(anchor='w')
        value = '' if profile.get(key) is None else str(profile[key])
        variable = tk.StringVar(value=value)
        ttk.Entry(cell, textvariable=variable, width=width, style='Paper.TEntry').pack(
            anchor='w', pady=(4, 0))
        fields[key] = variable
        return cell

    basics = tk.Frame(inner, bg=PAPER['surface'])
    basics.pack(fill='x')
    field(basics, 'weight_kg', '体重 kg')
    field(basics, 'age_years', '年龄 岁')
    sex_cell = tk.Frame(basics, bg=PAPER['surface'])
    sex_cell.pack(side='left')
    ui.text(sex_cell, '生理性别', size=9, fg=PAPER['ink2']).pack(anchor='w')
    sex_label = {code: label for code, label in SEX_CHOICES}
    sex = tk.StringVar(value=sex_label.get(profile.get('physiological_sex', 'unknown'),
                                          sex_label['unknown']))
    ttk.Combobox(sex_cell, textvariable=sex, values=[label for _code, label in SEX_CHOICES],
                 state='readonly', width=12, style='Paper.TCombobox').pack(
        anchor='w', pady=(4, 0))
    ui.text(inner, '生理性别不会据此推断激素、妊娠或器官功能。', size=8,
            fg=PAPER['ink3']).pack(anchor='w', pady=(10, 0))

    advanced_count = sum(1 for key in ('height_cm', 'body_fat_percent', 'measurement_source')
                         if profile.get(key) not in (None, '')) + len(current.get('genes', []))
    label = '更多选项 · 身高 / 体脂 / 测量来源 / 基因记录'
    if advanced_count:
        label += f'（已保存 {advanced_count} 项）'

    def fit(open_):
        dialog.update_idletasks()
        height = max(340, body.winfo_reqheight() + 10)
        dialog.geometry(f'680x{height}')
        dialog.after(30, lambda: ui.center_on(dialog, parent.winfo_toplevel()))

    more = ui.Disclosure(inner, label, bg=PAPER['surface'], on_toggle=fit)
    more.pack(fill='x', pady=(10, 0))
    more_body = more.body

    detail = tk.Frame(more_body, bg=PAPER['surface'])
    detail.pack(fill='x')
    for key, label, width in (('height_cm', '身高 cm', 12), ('body_fat_percent', '体脂 %', 10),
                              ('measurement_source', '测量日期 / 方法 / 来源', 34)):
        cell = tk.Frame(detail, bg=PAPER['surface'])
        cell.pack(side='left', padx=(0, 18))
        ui.text(cell, label, size=9, fg=PAPER['ink2']).pack(anchor='w')
        value = '' if profile.get(key) is None else str(profile[key])
        variable = tk.StringVar(value=value)
        ttk.Entry(cell, textvariable=variable, width=width, style='Paper.TEntry').pack(
            anchor='w', pady=(4, 0))
        fields[key] = variable

    ui.hairline(more_body).pack(fill='x', pady=(14, 10))
    genes_head = tk.Frame(more_body, bg=PAPER['surface'])
    genes_head.pack(fill='x')
    ui.text(genes_head, '基因记录', size=10, weight='bold').pack(side='left')
    ui.text(genes_head, '只记录检测报告原文；不推断代谢表型，不向外部服务发送。', size=8,
            fg=PAPER['ink3']).pack(side='left', padx=(10, 0))

    gene_rows = []
    rows_host = tk.Frame(more_body, bg=PAPER['surface'])
    rows_host.pack(fill='x', pady=(6, 0))
    for column, (label, minsize) in enumerate((('基因', 132), ('检测结果', 168),
                                               ('来源', 224))):
        rows_host.columnconfigure(column, minsize=minsize)
        tk.Label(rows_host, text=label, font=(ui.FONT, 8, 'bold'), fg=PAPER['ink3'],
                 bg=PAPER['surface'], anchor='w').grid(
            row=0, column=column, sticky='w', padx=(0, 8), pady=(0, 2))
    rows_host.columnconfigure(3, minsize=46)
    next_row = [0]

    def remove_row(record):
        if record in gene_rows:
            gene_rows.remove(record)
        for widget in record['widgets']:
            widget.destroy()
        dialog.after_idle(lambda: fit(more.open))

    def add_row(gene='', result='', source=''):
        next_row[0] += 1
        row = next_row[0]
        record = dict(widgets=[])
        for column, (key, value) in enumerate((('gene', gene), ('result', result),
                                               ('source', source))):
            variable = tk.StringVar(value=value)
            record[key] = variable
            entry = ttk.Entry(rows_host, textvariable=variable, width=10, style='Paper.TEntry')
            entry.grid(row=row, column=column, sticky='ew', padx=(0, 8), pady=2)
            record['widgets'].append(entry)
        remove = ui.FlatButton(rows_host, '移除', kind='quiet',
                               command=lambda: remove_row(record))
        remove.grid(row=row, column=3, sticky='w', pady=2)
        record['widgets'].append(remove)
        gene_rows.append(record)
        dialog.after_idle(lambda: fit(more.open))
        return record

    for record in current.get('genes', []):
        add_row(record.get('gene', ''), record.get('result', ''), record.get('source', ''))
    if not current.get('genes'):
        add_row()
    ui.FlatButton(more_body, '＋ 添加一行基因记录', kind='link', command=add_row).pack(
        anchor='w', pady=(6, 0))

    status = tk.StringVar(value='不自动推断代谢表型；不会向 Mayo / CPIC 或其他服务传送输入。')
    status_label = ui.text(body, '', size=9, fg=PAPER['ink3'], wraplength=600)
    status_label.configure(textvariable=status)
    status_label.pack(fill='x', pady=(12, 0))

    def save():
        try:
            values = {}
            for key, variable in fields.items():
                raw = variable.get().strip()
                if key == 'measurement_source':
                    values[key] = raw
                else:
                    values[key] = float(raw) if raw else None
            values['physiological_sex'] = next(
                code for code, label in SEX_CHOICES if label == sex.get())
            records = []
            for record in gene_rows:
                parts = [record[key].get().strip() for key in ('gene', 'result', 'source')]
                if not any(parts):
                    continue
                if not all(parts):
                    raise ValueError('每一行基因记录都需要填写基因、结果与来源。')
                records.append(dict(zip(('gene', 'result', 'source'), parts)))
            candidate = dict(physiology=values, genes=records)
            normalize_context(candidate)
            on_save(candidate)
            dialog.destroy()
        except (ValueError, OverflowError) as exc:
            status.set('输入被拒绝：' + str(exc))

    buttons = tk.Frame(body, bg=PAPER['bg'])
    buttons.pack(fill='x', side='bottom', pady=(14, 0))
    ui.FlatButton(buttons, '保存本次基线', kind='primary', command=save).pack(side='right')
    ui.FlatButton(buttons, '取消', kind='quiet', command=dialog.destroy).pack(
        side='right', padx=(0, 10))
    ui.text(buttons, '体重与年龄用于显示基线，不会自动修正暴露曲线。', size=8,
            fg=PAPER['ink3']).pack(side='left')
    ui.center_on(dialog, parent.winfo_toplevel())
    return dialog
