"""Run with python -m src.app. All parameters are synthetic research inputs."""
import tkinter as tk
from tkinter import ttk
from src.exposure import Regimen, concentration

root = tk.Tk()
root.title("Drug Simulator · 合成研究模型")
root.geometry("920x650")
ttk.Label(root, text="药物模拟器 · 合成 IV bolus 暴露", font=("", 18)).pack(pady=12)
ttk.Label(root, text="一室线性消除模型 · 单位 mg / L / h · 研究演示参数").pack()
fields = []
form = ttk.Frame(root, padding=12)
form.pack(fill="x")
headers = ("方案", "剂量 mg", "分布容积 L", "半衰期 h", "间隔 h", "次数")
for col, heading in enumerate(headers):
    ttk.Label(form, text=heading).grid(row=0, column=col, padx=8)
for row, name in enumerate(("合成 A", "合成 B"), 1):
    ttk.Label(form, text=name).grid(row=row, column=0)
    inputs = []
    for col, value in enumerate(("100", "10", str(row * 4), "8", "3"), 1):
        entry = ttk.Entry(form, width=14)
        entry.insert(0, value)
        entry.grid(row=row, column=col, padx=8, pady=5)
        inputs.append(entry)
    fields.append(inputs)
status = tk.StringVar(value="等待计算")
ttk.Label(root, textvariable=status, wraplength=880).pack(pady=8)
table = ttk.Treeview(root, columns=("time", "a", "b"), show="headings", height=18)
for column, label in zip(("time", "a", "b"), ("时间 h", "合成 A 浓度 mg/L", "合成 B 浓度 mg/L")):
    table.heading(column, text=label)

def calculate():
    table.delete(*table.get_children())
    try:
        regimens = []
        for entries in fields:
            values = [entry.get() for entry in entries]
            regimens.append(Regimen(*(float(v) for v in values[:4]), int(values[4])))
        horizon = max((r.count - 1) * r.interval_h + 5 * r.half_life_h for r in regimens)
        if not 0 < horizon <= 8760:
            raise ValueError("此演示的观察时长须在 0 到 8760 小时之间。")
        times = {horizon * i / 100 for i in range(101)}
        for regimen in regimens:
            times.update(index * regimen.interval_h for index in range(regimen.count))
        rows = [(time, *(concentration(r, time) for r in regimens)) for time in sorted(times)]
        for time, a, b in rows:
            table.insert("", "end", values=(f"{time:.6g}", f"{a:.6g}", f"{b:.6g}"))
        status.set("HOLD_FOR_REVIEW · 合成参数、确定性点估计，三层独立验证待完成。"
                   "两列分别计算各自暴露。联用综合效果 INSUFFICIENT_EVIDENCE，尚缺 PK-DDI 与 PD 证据。"
                   "给药时刻显示给药后浓度。")
    except (ValueError, OverflowError) as error:
        status.set("输入被拒绝：" + str(error))

ttk.Button(root, text="计算合成暴露时间轴", command=calculate).pack(pady=8)
table.pack(fill="both", expand=True, padx=16, pady=12)
root.mainloop()
