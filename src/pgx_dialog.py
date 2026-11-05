"""External module source and conditioned-research workspace."""
import json
import threading
import tkinter as tk
from tkinter import ttk
import webbrowser


def open_pgx(parent):
    from src.sources import refresh_sources, load_snapshot, MAYO_URL
    from src.pgx import estimate
    window = tk.Toplevel(parent)
    window.title('Celestial Drug · 来源与基因机制')
    window.geometry('960x680')
    body = ttk.Frame(window, padding=12); body.pack(fill='both', expand=True)
    ttk.Label(body, text='Atomoxetine · CYP2D6 · 条件化研究估计', font=('', 16)).pack(anchor='w')
    ttk.Label(body, text='独立研究场景；不读取主方案。群体参数不是个人实测，不提供用药建议。').pack(anchor='w')
    values = {}
    for key, label, default in [('weight_kg', '体重 kg', ''), ('age_years', '年龄', ''),
                                ('dose_mg', '单次口服剂量 mg', ''), ('diplotype', 'CYP2D6 双倍型', ''),
                                ('source', '测量/基因检测来源', '')]:
        line = ttk.Frame(body); line.pack(fill='x', pady=2)
        ttk.Label(line, text=label, width=26).pack(side='left')
        values[key] = tk.StringVar(value=default)
        ttk.Entry(line, textvariable=values[key]).pack(side='left', fill='x', expand=True)
    assumption = tk.BooleanVar(value=False)
    ttk.Checkbutton(body, text='研究假设：正常肝肾功能、非妊娠哺乳、无其它药物/补充剂/烟酒暴露（不是自动医学判断）', variable=assumption).pack(anchor='w')
    status = tk.StringVar(value='未读取来源；可离线检查已有快照或主动刷新公共资料。')
    ttk.Label(body, textvariable=status, wraplength=900).pack(anchor='w', pady=4)
    buttons = ttk.Frame(body); buttons.pack(fill='x')
    output = tk.Text(body, wrap='word'); output.pack(fill='both', expand=True)
    def show(value):
        output.delete('1.0', 'end'); output.insert('1.0', json.dumps(value, ensure_ascii=False, indent=2))
    def invalidate(*_):
        output.delete('1.0', 'end'); status.set('输入已变化，请重新计算。')
    for variable in [*values.values(), assumption]: variable.trace_add('write', invalidate)
    def calculate():
        invalidate()
        try:
            data = {key: variable.get().strip() for key, variable in values.items()}
            for key in ('weight_kg', 'age_years', 'dose_mg'): data[key] = float(data[key])
            data.update(scenario_confirmed=assumption.get(), route='oral', compound_id='atomoxetine', concomitants=[])
            show(estimate(data, load_snapshot()))
            status.set('计算完成：条件化研究估计；不是个人暴露预测或联用安全结论。')
        except (ValueError, OSError) as exc:
            show({'status': 'REFUSED', 'reason': str(exc)}); status.set('缺少有效来源或适用条件；未生成估计。')
    def refresh():
        refresh_button.configure(state='disabled'); invalidate(); status.set('正在读取固定公共资料；不会上传输入…')
        results = []
        def work():
            try: results.append(refresh_sources())
            except Exception as exc: results.append({'error': str(exc)})
        threading.Thread(target=work, daemon=True).start()
        def poll():
            if not window.winfo_exists(): return
            if not results: window.after(100, poll); return
            refresh_button.configure(state='normal'); show(results[0]); status.set('刷新已结束，请核对各来源状态；失败不等于连接成功。')
        window.after(100, poll)
    refresh_button = ttk.Button(buttons, text='刷新 CPIC / Mayo 公共资料', command=refresh); refresh_button.pack(side='left')
    ttk.Button(buttons, text='计算基因与体重条件估计', command=calculate).pack(side='left', padx=6)
    ttk.Button(buttons, text='阅读 Mayo 原文', command=lambda: webbrowser.open(MAYO_URL)).pack(side='left')
