"""Figma-derived desktop anatomy workspace, using existing external module services."""
import tkinter as tk
from tkinter import ttk
import webbrowser
from src.anatomy import REGIONS, region_details, highlighted_regions, EVIDENCE
from src.web_body import WebBody

BG='#0E141C'; PANEL='#17222E'; TEXT='#E8EFF5'; MUTED='#A9BAC8'; ACCENT='#5BD8C7'

def apply_theme(root):
    root.configure(background=BG)
    style=ttk.Style(root); style.theme_use('clam')
    style.configure('.',background=PANEL,foreground=TEXT,font=('Microsoft YaHei UI',10))
    style.configure('TFrame',background=BG)
    style.configure('Card.TFrame',background=PANEL)
    style.configure('TLabel',background=PANEL,foreground=TEXT)
    style.configure('TButton',background='#23423F',foreground=TEXT,padding=(12,8))
    style.map('TButton',background=[('active','#315853')])
    style.configure('TEntry',fieldbackground='#1D2A38',foreground=TEXT,insertcolor=TEXT)
    style.configure('TCombobox',fieldbackground='#1D2A38',background='#26333F',foreground=TEXT)
    style.map('TCombobox',fieldbackground=[('readonly','#1D2A38')],foreground=[('readonly',TEXT)])
    style.configure('Treeview',background='#17222E',fieldbackground='#17222E',foreground=TEXT,rowheight=30)
    style.configure('Treeview.Heading',background='#26333F',foreground=TEXT)
    style.configure('TNotebook',background=BG,borderwidth=0)
    style.configure('TNotebook.Tab',padding=(22,10),background=PANEL,foreground=MUTED)
    style.map('TNotebook.Tab',background=[('selected','#16413E')],foreground=[('selected',ACCENT)])
    root.option_add('*TCombobox*Listbox.background','#1D2A38')
    root.option_add('*TCombobox*Listbox.foreground',TEXT)

class AnatomyWorkspace(ttk.Frame):
    def __init__(self,parent,catalog,get_selected,get_context,open_context,open_pgx,open_regimen):
        super().__init__(parent,padding=10)
        self.drug=None;self.selected='brain';self.get_context=get_context
        self.columnconfigure(0,weight=1);self.columnconfigure(2,weight=0)
        self.rowconfigure(2,weight=1)
        toolbar=ttk.Frame(self,style='Card.TFrame',padding=10)
        toolbar.grid(row=0,column=0,columnspan=3,sticky='ew',pady=(0,6))
        ttk.Label(toolbar,text='当前物质').grid(row=0,column=0,padx=(0,8))
        names=['未选择物质','来源库 / atomoxetine']+['来源库 / '+key for key in catalog['compounds']]
        self.choice=tk.StringVar(value=names[0]);combo=ttk.Combobox(toolbar,textvariable=self.choice,values=names,state='readonly',width=23)
        combo.grid(row=0,column=1,sticky='ew',padx=(0,8))
        def choose(_):
            selected=self.choice.get()
            self.drug={'kind':'catalog','compound_id':selected.split(' / ')[1],'name':selected.split(' / ')[1]} if ' / ' in selected else None
            self.render()
        combo.bind('<<ComboboxSelected>>',choose)
        def use_regimen():
            self.drug=get_selected();self.choice.set('方案选中 / '+self.drug['name'] if self.drug else '未选择物质');self.render()
        ttk.Button(toolbar,text='载入方案选中项',command=use_regimen).grid(row=0,column=2,padx=4)
        ttk.Button(toolbar,text='编辑多药方案',command=open_regimen).grid(row=0,column=3,padx=4)
        self.baseline=tk.StringVar()
        ttk.Label(toolbar,textvariable=self.baseline,foreground=MUTED).grid(row=1,column=0,columnspan=2,sticky='w',pady=(8,0))
        ttk.Button(toolbar,text='生理 / 基因参数',command=open_context).grid(row=1,column=2,padx=4,pady=(6,0))
        ttk.Button(toolbar,text='来源 / 条件估计',command=open_pgx).grid(row=1,column=3,padx=4,pady=(6,0))
        ttk.Label(toolbar,text='亮色：文献关联，非个人反应',foreground=MUTED).grid(row=0,column=4,sticky='e',padx=12)
        toolbar.columnconfigure(4,weight=1)
        center=ttk.Frame(self,style='Card.TFrame');center.grid(row=2,column=0,columnspan=2,sticky='nsew')
        self.canvas=WebBody(center,self.select_region);self.canvas.pack(fill='both',expand=True)
        right=ttk.Frame(self,style='Card.TFrame',padding=12,width=340);right.grid(row=2,column=2,sticky='nsew',padx=(8,0));right.pack_propagate(False)
        self.keys=list(REGIONS);self.region_choice=tk.StringVar(value=REGIONS[self.selected][0])
        directory=ttk.Combobox(right,textvariable=self.region_choice,values=[REGIONS[k][0] for k in self.keys],state='readonly')
        directory.pack(fill='x',pady=(0,10));directory.bind('<<ComboboxSelected>>',lambda _:self.select_region(self.keys[directory.current()]))
        self.heading=tk.StringVar();ttk.Label(right,textvariable=self.heading,font=('Microsoft YaHei UI',17,'bold')).pack(anchor='w',pady=(0,12))
        reportframe=ttk.Frame(right);reportframe.pack(fill='both',expand=True)
        self.detail=tk.Text(reportframe,bg=PANEL,fg=TEXT,wrap='word',relief='flat',font=('Microsoft YaHei UI',11),padx=4,pady=8,state='disabled',width=32,height=1)
        scroll=ttk.Scrollbar(reportframe,command=self.detail.yview);self.detail.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');self.detail.pack(fill='both',expand=True)
        self.related=ttk.Frame(right,style='Card.TFrame');self.related.pack(fill='x',pady=10)
        self.source_btn=ttk.Button(right,text='打开当前区域证据原文 ↗',command=self.open_source);self.source_btn.pack(fill='x')
        self.render()
    def select_region(self,key):
        if key not in REGIONS:return
        self.selected=key;self.region_choice.set(REGIONS[key][0]);self.render()
    def render(self):
        context=self.get_context();p=context.get('physiology',{})
        self.baseline.set('体重：'+str(p.get('weight_kg') or '未填写')+' kg  · 年龄：'+str(p.get('age_years') or '未填写')+'  · 基因：'+str(len(context.get('genes',[])))+' 项')
        data=region_details(self.drug,self.selected);self.heading.set(data['name'])
        substance=self.drug.get('name',self.drug.get('compound_id','')) if self.drug else '未选择物质'
        geometry='几何：用户指定 HTML 原稿 / 补充示意；形状和系统配色不构成药效证据。'
        if self.canvas.fallback:geometry='几何：BodyParts3D / DBCLS 简化参考网格；子宫为原有示意层。'
        if self.selected in ('uterus','testes','biceps','triceps','quadriceps') and not self.canvas.fallback:geometry='几何：补充示意层，用于保留既有区域入口；不是实际组织仿真。'
        lines=[substance,'',geometry,'',('文献关联 · 待人工审核' if data['evidence'] else 'INSUFFICIENT_EVIDENCE · 无已收录区域证据'),'']
        for evidence in data['evidence']:
            lines += [evidence['text'],'','来源章节：'+evidence['section'],evidence['url'],'核对：'+evidence['checked_on']+' / '+evidence['review_status'],'']
        if not data['evidence']:lines += ['此区域仍可浏览。资料缺失不等于没有作用，也不表示安全。','']
        lines += ['关联结构', '、'.join(REGIONS[k][0] for k in data['members']),data['relation_note'],'','当前未计算','个人效果强度、器官浓度、损伤程度及系统间因果影响。']
        self.detail.configure(state='normal');self.detail.delete('1.0','end');self.detail.insert('1.0','\n'.join(lines));self.detail.configure(state='disabled');self.detail.yview_moveto(0)
        for child in self.related.winfo_children():child.destroy()
        for key in data['members']:ttk.Button(self.related,text='查看 '+REGIONS[key][0],command=lambda k=key:self.select_region(k)).pack(fill='x',pady=2)
        self.source_btn.configure(state='normal' if data['evidence'] else 'disabled')
        self.canvas.update_state(self.drug,self.selected)
    def open_source(self):
        evidence=region_details(self.drug,self.selected)['evidence']
        if evidence:webbrowser.open(evidence[0]['url'])
