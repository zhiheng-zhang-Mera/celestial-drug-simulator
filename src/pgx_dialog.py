"""External module source and conditioned-research workspace."""
import json
import threading
import tkinter as tk
from tkinter import ttk
import webbrowser

from src import ui_theme as ui

try:
    from celestial_help import attach_help
except ModuleNotFoundError:  # direct `python src/...` execution from the repository root
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from celestial_help import attach_help

PAPER = ui.PAPER
DIPLOTYPES = ('*1/*1', '*1/*4', '*4/*4')
HELP_TEXTS = {
    'pgx': (
        '这里展示来源快照与 CYP2D6 条件化研究估计：输入体重、年龄、单次剂量与基因双倍型，'
        '全部在本机计算，不读取主方案、不上传。结果为群体参数下的研究估计，不是个人实测、'
        '剂量推荐或临床结论；「更新来源」会联网抓取公开资料，只用于本机缓存。'
    ),
}


def open_pgx(parent):
    from src.sources import refresh_sources, load_snapshot, MAYO_URL
    from src.pgx import estimate
    window = tk.Toplevel(parent)
    window.title('Celestial Drug · 来源与基因机制')
    window.geometry('880x580')
    window.minsize(720, 520)
    window.configure(background=PAPER['bg'])
    ui.setup(window)
    body = tk.Frame(window, bg=PAPER['bg'], padx=24, pady=18)
    body.pack(fill='both', expand=True)

    ui.eyebrow(body, '独立研究场景').pack(anchor='w')
    title_row = tk.Frame(body, bg=PAPER['bg'])
    title_row.pack(fill='x', pady=(4, 0))
    ui.text(title_row, '阿托莫西汀 · CYP2D6 · 条件化研究估计', size=15, weight='bold').pack(
        side='left')
    attach_help(title_row, 'pgx', HELP_TEXTS['pgx'],
                title='来源与基因估计').pack(side='left', padx=(8, 0))
    ui.text(body, '不读取主方案；群体参数不是个人实测，不提供用药建议。', size=9,
            fg=PAPER['ink3']).pack(anchor='w')

    card = tk.Frame(body, bg=PAPER['surface'], highlightthickness=1,
                    highlightbackground=PAPER['line'])
    card.pack(fill='x', pady=(14, 0))
    inner = tk.Frame(card, bg=PAPER['surface'], padx=18, pady=14)
    inner.pack(fill='x')
    values = {}

    def field(parent_frame, key, label, width, default=''):
        cell = tk.Frame(parent_frame, bg=PAPER['surface'])
        cell.pack(side='left', padx=(0, 18))
        ui.text(cell, label, size=9, fg=PAPER['ink2']).pack(anchor='w')
        values[key] = tk.StringVar(value=default)
        ttk.Entry(cell, textvariable=values[key], width=width, style='Paper.TEntry').pack(
            anchor='w', pady=(4, 0))
        return cell

    scenario = tk.Frame(inner, bg=PAPER['surface'])
    scenario.pack(fill='x')
    field(scenario, 'weight_kg', '体重 kg（40–120）', 10)
    field(scenario, 'age_years', '年龄（18–64）', 10)
    field(scenario, 'dose_mg', '单次口服剂量 mg（0–100）', 14)

    source_row = tk.Frame(inner, bg=PAPER['surface'])
    source_row.pack(fill='x', pady=(12, 0))
    diplo_cell = tk.Frame(source_row, bg=PAPER['surface'])
    diplo_cell.pack(side='left', padx=(0, 18))
    ui.text(diplo_cell, 'CYP2D6 双倍型', size=9, fg=PAPER['ink2']).pack(anchor='w')
    values['diplotype'] = tk.StringVar(value='')
    ttk.Combobox(diplo_cell, textvariable=values['diplotype'], values=DIPLOTYPES,
                 state='readonly', width=12, style='Paper.TCombobox').pack(
        anchor='w', pady=(4, 0))
    field(source_row, 'source', '测量 / 基因检测来源', 38)

    assumption = tk.BooleanVar(value=False)
    ui.checkbox(inner, '研究假设：肝肾功能正常、非妊娠哺乳、无其它药物 / 补充剂 / 烟酒暴露'
                '（不是自动医学判断）', assumption, bg=PAPER['surface']).pack(
        anchor='w', pady=(12, 0))

    actions = tk.Frame(body, bg=PAPER['bg'])
    actions.pack(fill='x', pady=(12, 0))
    status = tk.StringVar(value='未读取来源；可离线检查已有快照或主动刷新公共资料。')

    def show(value):
        output.configure(state='normal')
        output.delete('1.0', 'end')
        output.insert('1.0', json.dumps(value, ensure_ascii=False, indent=2))
        output.configure(state='disabled')

    def invalidate(*_):
        output.configure(state='normal')
        output.delete('1.0', 'end')
        output.configure(state='disabled')
        status.set('输入已变化，请重新计算。')

    for variable in [*values.values(), assumption]:
        variable.trace_add('write', invalidate)

    def calculate():
        invalidate()
        try:
            data = {key: variable.get().strip() for key, variable in values.items()}
            for key in ('weight_kg', 'age_years', 'dose_mg'):
                data[key] = float(data[key])
            data.update(scenario_confirmed=assumption.get(), route='oral',
                        compound_id='atomoxetine', concomitants=[])
            result = estimate(data, load_snapshot())
            show(result)
            status.set('计算完成：条件化人群研究估计，不是个人暴露预测或联用安全结论。')
        except (ValueError, OSError) as exc:
            show({'status': 'REFUSED', 'reason': str(exc)})
            status.set('输入或来源不满足研究条件，未生成估计。')

    def refresh():
        refresh_button.configure(state='disabled')
        invalidate()
        status.set('正在读取固定公共资料；不会上传输入…')
        results = []

        def work():
            try:
                results.append(refresh_sources())
            except Exception as exc:  # reported to the user, never hidden
                results.append({'error': str(exc)})

        threading.Thread(target=work, daemon=True).start()

        def poll():
            if not window.winfo_exists():
                return
            if not results:
                window.after(100, poll)
                return
            refresh_button.configure(state='normal')
            show(results[0])
            status.set('刷新已结束，请核对各来源状态；失败不等于连接成功。')

        window.after(100, poll)

    refresh_button = ui.FlatButton(actions, '刷新 CPIC / Mayo 公共资料', kind='secondary',
                                   command=refresh)
    refresh_button.pack(side='left')
    ui.FlatButton(actions, '计算基因与体重条件估计', kind='primary', command=calculate).pack(
        side='left', padx=(10, 0))
    ui.FlatButton(actions, '阅读 Mayo 原文', kind='quiet',
                  command=lambda: webbrowser.open(MAYO_URL)).pack(side='left', padx=(10, 0))

    status_label = ui.text(body, '', size=9, fg=PAPER['ink3'], wraplength=800)
    status_label.configure(textvariable=status)
    status_label.pack(fill='x', pady=(10, 6))
    output_frame = tk.Frame(body, bg=PAPER['surface2'], highlightthickness=1,
                            highlightbackground=PAPER['line'])
    output_frame.pack(fill='both', expand=True)
    ui.text(output_frame, '研究输出 · JSON', size=8, fg=PAPER['ink3'],
            bg=PAPER['surface2']).pack(anchor='w', padx=12, pady=(8, 0))
    output = tk.Text(output_frame, wrap='word', relief='flat', bd=0, bg=PAPER['surface2'],
                     fg=PAPER['ink2'], font=(ui.MONO, 9), padx=12, pady=8, height=8,
                     state='disabled', highlightthickness=0)
    output.pack(fill='both', expand=True)
    ui.center_on(window, parent.winfo_toplevel())
    return window
