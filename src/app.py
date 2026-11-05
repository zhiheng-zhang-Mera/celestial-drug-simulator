"""External desktop workspace with online-first public drug labels."""
import tkinter as tk
from tkinter import ttk


def main():
    from src.body_ui import AnatomyWorkspace,apply_theme
    from src.simulation import load_catalog
    from src.regimen_ui import RegimenWorkspace
    from src.navigation import StableNotebook
    window=tk.Tk();window.title('Celestial Drug Simulator · 人体作用与证据')
    window.geometry('1440x940');window.minsize(1160,780);apply_theme(window)
    header=ttk.Frame(window,padding=(16,8));header.pack(fill='x')
    ttk.Label(header,text='CELESTIAL / DRUG',foreground='#5BD8C7',font=('Microsoft YaHei UI',10,'bold')).pack(side='left',padx=(0,18))
    ttk.Label(header,text='人体作用与证据',font=('Microsoft YaHei UI',16,'bold')).pack(side='left')
    tabs=StableNotebook(window);tabs.pack(fill='both',expand=True)
    body_host=ttk.Frame(tabs);tabs.add(body_host,text='人体作用')
    regimen=RegimenWorkspace(tabs,tabs);tabs.add(regimen,text='多药方案 / 联用机制')
    catalog=load_catalog()
    for identity in ('estradiol','bicalutamide'):catalog['compounds'].setdefault(identity,{})
    body=AnatomyWorkspace(body_host,catalog,regimen.selected_item,lambda:regimen.context,
                          regimen.open_context,regimen.open_sources,lambda:tabs.select(regimen))
    regimen.body=body;body.pack(fill='both',expand=True)
    window.mainloop()


if __name__=='__main__':main()
