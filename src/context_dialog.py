"""Optional local research context editor."""
import tkinter as tk
from tkinter import ttk
from src.context import normalize_context


def edit_context(parent, current, on_save):
    dialog = tk.Toplevel(parent)
    dialog.title('生理基线与基因 · 仅本机')
    dialog.geometry('720x620')
    dialog.transient(parent)
    dialog.grab_set()
    body = ttk.Frame(dialog, padding=14)
    body.pack(fill='both', expand=True)
    ttk.Label(body, text='可留空；数据尚未用于修正代谢。保存后旧报告失效。').pack(anchor='w')
    profile = current.get('physiology', {})
    fields = {}
    for key, label in [('height_cm', '身高 cm'), ('weight_kg', '体重 kg'),
                       ('body_fat_percent', '体脂 %'), ('age_years', '年龄 岁'),
                       ('measurement_source', '测量日期 / 方法 / 来源')]:
        line = ttk.Frame(body); line.pack(fill='x', pady=4)
        ttk.Label(line, text=label, width=25).pack(side='left')
        fields[key] = tk.StringVar(value='' if profile.get(key) is None else str(profile[key]))
        ttk.Entry(line, textvariable=fields[key]).pack(side='left', fill='x', expand=True)
    sex = tk.StringVar(value=profile.get('physiological_sex', 'unknown'))
    ttk.Label(body, text='生理性别（不会据此推断激素、妊娠或器官功能）').pack(anchor='w')
    ttk.Combobox(body, textvariable=sex, values=('unknown', 'female', 'male', 'intersex'), state='readonly').pack(anchor='w')
    ttk.Label(body, text='基因记录：每行 基因 | 检测结果 | 来源（不填写姓名等身份信息）').pack(anchor='w', pady=(12, 4))
    genes = tk.Text(body, height=6, wrap='word')
    genes.pack(fill='both', expand=True)
    genes.insert('1.0', '\n'.join(' | '.join(g[k] for k in ('gene', 'result', 'source')) for g in current.get('genes', [])))
    status = tk.StringVar(value='不自动推断代谢表型，不向 Mayo/CPIC 或其他服务传送输入。')
    ttk.Label(body, textvariable=status, wraplength=660).pack(pady=8)

    def save():
        try:
            values = {key: (variable.get().strip() if key == 'measurement_source' else
                           float(variable.get()) if variable.get().strip() else None)
                      for key, variable in fields.items()}
            values['physiological_sex'] = sex.get()
            records = []
            for line in genes.get('1.0', 'end').splitlines():
                if not line.strip(): continue
                parts = [part.strip() for part in line.split('|')]
                if len(parts) != 3: raise ValueError('每行必须有三项，以 | 分隔。')
                records.append(dict(zip(('gene', 'result', 'source'), parts)))
            candidate = dict(physiology=values, genes=records)
            normalize_context(candidate)
            on_save(candidate)
            dialog.destroy()
        except (ValueError, OverflowError) as exc:
            status.set('输入被拒绝：' + str(exc))

    buttons = ttk.Frame(body); buttons.pack(fill='x')
    ttk.Button(buttons, text='保存本次基线', command=save).pack(side='left')
    ttk.Button(buttons, text='取消', command=dialog.destroy).pack(side='right')
