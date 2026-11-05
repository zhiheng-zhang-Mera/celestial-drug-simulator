"""Figma-derived desktop anatomy workspace, using existing external module services."""
import tkinter as tk
from tkinter import ttk
import webbrowser
from src.anatomy import REGIONS, region_details, highlighted_regions, EVIDENCE
from src.body_canvas import BodyCanvas, COLORS

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
        super().__init__(parent,padding=16)
        self.drug=None;self.selected='brain';self.get_context=get_context
        self.columnconfigure(1,weight=1);self.columnconfigure(2,weight=0)
        self.rowconfigure(1,weight=1)
        banner=tk.Label(self,text='器官亮色 = 文献关联 · 非已发生的个人反应；组织默认中性透明蒙版',bg='#1D2A38',fg=MUTED,anchor='w',padx=16,pady=10)
        banner.grid(row=0,column=0,columnspan=3,sticky='ew',pady=(0,16))
        left=ttk.Frame(self,style='Card.TFrame',padding=16,width=255);left.grid(row=1,column=0,sticky='nsew',padx=(0,16));left.grid_propagate(False)
        left.columnconfigure(0,weight=1);left.rowconfigure(10,weight=1)
        ttk.Label(left,text='01  当前物质',font=('Microsoft YaHei UI',13,'bold')).grid(row=0,column=0,sticky='w')
        names=['未选择物质','来源库 / atomoxetine']+['来源库 / '+key for key in catalog['compounds']]
        self.choice=tk.StringVar(value=names[0]);combo=ttk.Combobox(left,textvariable=self.choice,values=names,state='readonly',width=23)
        combo.grid(row=1,column=0,sticky='ew',pady=(12,8))
        def choose(_):
            selected=self.choice.get()
            self.drug={'kind':'catalog','compound_id':selected.split(' / ')[1],'name':selected.split(' / ')[1]} if ' / ' in selected else None
            self.render()
        combo.bind('<<ComboboxSelected>>',choose)
        def use_regimen():
            self.drug=get_selected();self.choice.set('方案选中 / '+self.drug['name'] if self.drug else '未选择物质');self.render()
        ttk.Button(left,text='使用方案中选中的物质',command=use_regimen).grid(row=2,column=0,sticky='ew',pady=3)
        ttk.Button(left,text='编辑多药方案  →',command=open_regimen).grid(row=3,column=0,sticky='ew',pady=3)
        self.baseline=tk.StringVar()
        ttk.Label(left,text='02  生理与基因',font=('Microsoft YaHei UI',13,'bold')).grid(row=4,column=0,sticky='w',pady=(20,8))
        ttk.Label(left,textvariable=self.baseline,wraplength=220,foreground=MUTED).grid(row=5,column=0,sticky='ew')
        ttk.Button(left,text='编辑本机基线',command=open_context).grid(row=6,column=0,sticky='ew',pady=7)
        ttk.Button(left,text='来源 / 基因条件估计',command=open_pgx).grid(row=7,column=0,sticky='ew')
        ttk.Label(left,text='03  器官 / 肌群 / 系统',font=('Microsoft YaHei UI',12,'bold')).grid(row=8,column=0,sticky='w',pady=(20,8))
        ttk.Label(left,text='列表支持键盘选择；系统虚线仅表示关联。',wraplength=220,foreground=MUTED).grid(row=9,column=0,sticky='ew')
        listframe=ttk.Frame(left);listframe.grid(row=10,column=0,sticky='nsew',pady=6)
        self.regions=tk.Listbox(listframe,bg='#1D2A38',fg=TEXT,selectbackground='#28534F',highlightthickness=0,exportselection=False,font=('Microsoft YaHei UI',10),height=10)
        scrollbar=ttk.Scrollbar(listframe,command=self.regions.yview);self.regions.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y');self.regions.pack(fill='both',expand=True)
        self.keys=list(REGIONS)
        for key,(name,kind,_) in REGIONS.items():self.regions.insert('end',name+('  · 系统' if kind=='system' else ''))
        self.regions.bind('<<ListboxSelect>>',lambda _:self.select_region(self.keys[self.regions.curselection()[0]]) if self.regions.curselection() else None)
        center=ttk.Frame(self,style='Card.TFrame',padding=16);center.grid(row=1,column=1,sticky='nsew')
        ttk.Label(center,text='作用区域地图',font=('Microsoft YaHei UI',16,'bold')).pack(anchor='w')
        controls=ttk.Frame(center,style='Card.TFrame');controls.pack(fill='x',pady=10)
        self.view=tk.StringVar(value='正面');self.reproductive=tk.StringVar(value='隐藏')
        for variable,options in ((self.view,('正面','背面')),(self.reproductive,('隐藏','睾丸分层','子宫分层'))):
            control=ttk.Combobox(controls,textvariable=variable,values=options,state='readonly',width=11);control.pack(side='left',padx=(0,8));control.bind('<<ComboboxSelected>>',lambda _:self.render())
        self.hover=tk.StringVar(value='点击组织，查看关联证据')
        ttk.Label(center,textvariable=self.hover,foreground=ACCENT).pack(anchor='w',pady=(0,8))
        self.canvas=BodyCanvas(center,self.select_region,self.on_hover,width=440,height=540);self.canvas.pack(fill='both',expand=True)
        ttk.Label(center,text='青：机制   蓝：代谢   浅蓝：排泄   金：标签关注',foreground=MUTED,font=('Microsoft YaHei UI',9)).pack(anchor='w',pady=(8,0))
        ttk.Label(center,text='正背面为解剖投影 · 生殖分层不由性别推断',foreground=MUTED,font=('Microsoft YaHei UI',9)).pack(anchor='w')
        right=ttk.Frame(self,style='Card.TFrame',padding=16,width=340);right.grid(row=1,column=2,sticky='nsew',padx=(16,0));right.pack_propagate(False)
        self.heading=tk.StringVar();ttk.Label(right,textvariable=self.heading,font=('Microsoft YaHei UI',17,'bold')).pack(anchor='w',pady=(0,12))
        reportframe=ttk.Frame(right);reportframe.pack(fill='both',expand=True)
        self.detail=tk.Text(reportframe,bg=PANEL,fg=TEXT,wrap='word',relief='flat',font=('Microsoft YaHei UI',11),padx=4,pady=8,state='disabled',width=32)
        scroll=ttk.Scrollbar(reportframe,command=self.detail.yview);self.detail.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');self.detail.pack(fill='both',expand=True)
        self.related=ttk.Frame(right,style='Card.TFrame');self.related.pack(fill='x',pady=10)
        self.source_btn=ttk.Button(right,text='打开当前区域证据原文 ↗',command=self.open_source);self.source_btn.pack(fill='x')
        self.render()
    def on_hover(self,key): self.hover.set(REGIONS[key][0]+' · 点击查看机制与证据' if key else '点击组织，查看关联证据')
    def select_region(self,key):
        self.selected=key
        if key=='triceps':self.view.set('背面')
        elif key=='biceps':self.view.set('正面')
        if key in ('testes','uterus'):self.reproductive.set({'testes':'睾丸分层','uterus':'子宫分层'}[key])
        self.regions.selection_clear(0,'end');self.regions.selection_set(self.keys.index(key));self.regions.see(self.keys.index(key));self.render()
    def render(self):
        context=self.get_context();p=context.get('physiology',{})
        self.baseline.set('体重：'+str(p.get('weight_kg') or '未填写')+' kg\n年龄：'+str(p.get('age_years') or '未填写')+'\n基因记录：'+str(len(context.get('genes',[])))+' 项\n未自动推断器官状态')
        data=region_details(self.drug,self.selected);self.heading.set(data['name'])
        substance=self.drug.get('name',self.drug.get('compound_id','')) if self.drug else '未选择物质'
        lines=[substance,'',('文献关联 · 待人工审核' if data['evidence'] else 'INSUFFICIENT_EVIDENCE · 无已收录区域证据'),'']
        for evidence in data['evidence']:
            lines += [evidence['text'],'','来源章节：'+evidence['section'],evidence['url'],'核对：'+evidence['checked_on']+' / '+evidence['review_status'],'']
        if not data['evidence']:lines += ['此区域仍可浏览。资料缺失不等于没有作用，也不表示安全。','']
        lines += ['关联结构', '、'.join(REGIONS[k][0] for k in data['members']),data['relation_note'],'','当前未计算','个人效果强度、器官浓度、损伤程度及系统间因果影响。']
        self.detail.configure(state='normal');self.detail.delete('1.0','end');self.detail.insert('1.0','\n'.join(lines));self.detail.configure(state='disabled');self.detail.yview_moveto(0)
        for child in self.related.winfo_children():child.destroy()
        for key in data['members']:ttk.Button(self.related,text='查看 '+REGIONS[key][0],command=lambda k=key:self.select_region(k)).pack(fill='x',pady=2)
        self.source_btn.configure(state='normal' if data['evidence'] else 'disabled')
        effects={key:region_details(self.drug,key)['evidence'][0]['category'] for key in highlighted_regions(self.drug)}
        members=data['members'] if data['kind']=='system' else []
        self.canvas.update_map(effects,self.selected,members,self.view.get(),self.reproductive.get())
    def open_source(self):
        evidence=region_details(self.drug,self.selected)['evidence']
        if evidence:webbrowser.open(evidence[0]['url'])
