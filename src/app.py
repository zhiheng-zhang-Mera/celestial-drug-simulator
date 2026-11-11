"""Celestial Drug Simulator desktop workspace with a clinical reading shell."""
import os
import tkinter as tk

DEFAULT_TITLE = 'Celestial Drug Simulator · 人体作用与证据'


def window_title():
    """Production title, with a development-only override for parallel UI checks."""
    return os.environ.get('CELESTIAL_DRUG_TITLE') or DEFAULT_TITLE


def build(window):
    """Construct the full window and return its main parts (used by app and tools)."""
    from src import ui_theme as ui
    from src.body_ui import AnatomyWorkspace, apply_theme
    from src.regimen_ui import RegimenWorkspace
    from src.navigation import SegmentedNav
    from src.simulation import load_catalog

    window.title(window_title())
    window.geometry('1440x900')
    window.minsize(1024, 720)
    apply_theme(window)
    palette = ui.PAPER

    # ------------------------------------------------------------- top bar
    top = tk.Frame(window, bg=palette['bgElevated'], height=56)
    top.pack(fill='x')
    top.pack_propagate(False)
    brand_box = tk.Frame(top, bg=palette['bgElevated'])
    brand_box.pack(side='left', padx=(24, 0))
    tk.Label(brand_box, text='CELESTIAL / DRUG', font=(ui.MONO, 9, 'bold'),
             fg=palette['accent'], bg=palette['bgElevated']).pack(side='left', padx=(0, 14))
    tk.Label(brand_box, text='人体作用与证据', font=(ui.FONT, 15, 'bold'),
             fg=palette['ink'], bg=palette['bgElevated']).pack(side='left')
    tk.Label(brand_box, text='医疗模块', font=(ui.FONT, 9), fg=palette['ink3'],
             bg=palette['bgElevated']).pack(side='left', padx=(10, 0))

    center = tk.Frame(top, bg=palette['bgElevated'])
    center.pack(side='left', padx=(32, 0))
    ui.text(center, '当前物质', size=8, fg=palette['ink3'],
            bg=palette['bgElevated']).pack(side='left', padx=(0, 8))
    substance_var = tk.StringVar(value='未选择物质')
    tk.Label(center, textvariable=substance_var, font=(ui.FONT, 10, 'bold'),
             fg=palette['ink'], bg=palette['bgElevated']).pack(side='left')

    right = tk.Frame(top, bg=palette['bgElevated'])
    right.pack(side='right', padx=(0, 24))
    data_var = tk.StringVar(value='在线查询就绪 · 仅发送药名')
    tk.Label(right, text='●', font=(ui.FONT, 7), fg=palette['gain'],
             bg=palette['bgElevated']).pack(side='left')
    tk.Label(right, textvariable=data_var, font=(ui.FONT, 9), fg=palette['ink2'],
             bg=palette['bgElevated']).pack(side='left', padx=(4, 0))
    ui.hairline(window).pack(fill='x')

    # ------------------------------------------------------------ navigation
    nav_row = tk.Frame(window, bg=palette['bg'], padx=24, pady=14)
    nav_row.pack(fill='x')
    nav = SegmentedNav(nav_row, size=11, bg=palette['bg'])
    nav.pack(side='left')
    nav.add('body', '人体作用')
    nav.add('regimen', '多药方案 / 联用机制')
    ui.text(nav_row, '本机数据 · 研究记录，不构成医学建议', size=8,
            fg=palette['ink3']).pack(side='right', pady=6)

    # ------------------------------------------------------------ status line
    # The status line is packed before the expanding view stack so it keeps its
    # height at small window sizes (pack allocates in call order).
    bottom = tk.Frame(window, bg=palette['bg'], height=30)
    bottom.pack(side='bottom', fill='x')
    bottom.pack_propagate(False)
    ui.hairline(bottom).pack(fill='x')
    baseline_var = tk.StringVar(value='基线：体重未填写 · 年龄未填写 · 基因 0 项')
    tk.Label(bottom, textvariable=baseline_var, font=(ui.FONT, 8), fg=palette['ink3'],
             bg=palette['bg'], anchor='w').pack(side='left', padx=24)
    tk.Label(bottom, text='未上传 · 不提供个人用药建议', font=(ui.FONT, 8),
             fg=palette['ink3'], bg=palette['bg']).pack(side='right', padx=24)

    # --------------------------------------------------------------- views
    stack = tk.Frame(window, bg=palette['bg'])
    stack.pack(fill='both', expand=True)
    stack.rowconfigure(0, weight=1)
    stack.columnconfigure(0, weight=1)
    body_host = tk.Frame(stack, bg=palette['bg'])
    regimen_host = tk.Frame(stack, bg=palette['bg'])
    for frame in (body_host, regimen_host):
        frame.grid(row=0, column=0, sticky='nsew')

    def show(key):
        (body_host if key == 'body' else regimen_host).tkraise()

    nav.on_change = show

    def body_state(info):
        substance_var.set(info.get('substance') or '未选择物质')
        baseline_var.set(info.get('baseline') or baseline_var.get())

    def data_state(online):
        data_var.set('在线查询就绪 · 仅发送药名' if online else '离线资料 · 使用本地缓存与来源事实')

    catalog = load_catalog()
    for identity in ('estradiol', 'bicalutamide'):
        catalog['compounds'].setdefault(identity, {})
    regimen = RegimenWorkspace(regimen_host, nav, on_data_state=data_state)
    body = AnatomyWorkspace(body_host, catalog, regimen.selected_item, lambda: regimen.context,
                            regimen.open_context, regimen.open_sources,
                            lambda: nav.select('regimen'), on_state=body_state)
    regimen.body = body
    body.pack(fill='both', expand=True)
    regimen.pack(fill='both', expand=True)
    nav.select('body')
    return dict(window=window, nav=nav, body=body, regimen=regimen,
                substance=substance_var, baseline=baseline_var, data=data_var)


def main():
    window = tk.Tk()
    build(window)
    window.mainloop()


if __name__ == '__main__':
    main()
