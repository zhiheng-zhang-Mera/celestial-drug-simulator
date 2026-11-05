"""Minimal regimen entry; source lookup is separate from hypothetical IV curves."""
import copy
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from src.simulation import simulate

ROUTES={'口服 / 片剂':'oral','经皮':'transdermal','舌下':'sublingual','注射':'injection',
        '其他':'other','静脉推注 · 假设模型':'iv_bolus','输注':'infusion'}


def study_lines(evidence):
    return [evidence['source_location'],evidence['context'],evidence['uncertainty'],
            '适用性：'+evidence['applicability'],'来源结构校验：'+evidence['structural_check'],
            f"研究观察 AUC 比率：{evidence['auc_ratio']}；当前方案预测：未准入。",
            (evidence.get('source') or {}).get('url','来源缺失：拒绝准入')]


def editor_item(values, route, custom=False, advanced=False, category='medicine'):
    from src.drug_library import resolve_name, profile_for
    name=values.get('name','').strip()
    identity=resolve_name(name) if not custom and not advanced else None
    profile=profile_for(identity,route) if identity else None
    def number(key, integer=False):
        raw=values.get(key,'')
        value='' if raw is None else str(raw).strip()
        return (int(value) if integer else float(value)) if value else None
    item=dict(name=name,kind='catalog' if identity else 'custom',compound_id=identity or '',
              category=category,route=route,source=values.get('source','').strip(),
              dose_mg=number('dose_mg'),interval_h=number('interval_h'),count=number('count',True),
              model_mode='evidence',volume_l=None,half_life_h=(profile or {}).get('half_life_h'))
    if advanced:
        item.update(kind='synthetic',model_mode='synthetic',volume_l=number('volume_l'),half_life_h=number('half_life_h'))
    if profile:item['parameter_source']=profile
    simulate([item])
    return item


class RegimenWorkspace(ttk.Frame):
    def __init__(self,parent,tabs):
        super().__init__(parent,padding=10)
        self.rows=[];self.result=None;self.context={};self.body=None
        self.generation=0;self.busy=False;self.mail=queue.Queue();self.tabs=tabs
        ttk.Label(self,text='多药方案',font=('Microsoft YaHei UI',14,'bold')).pack(anchor='w')
        ttk.Label(self,text='输入药名即可分析机制；剂量与时间选填。默认参数按药物和途径匹配。').pack(anchor='w',pady=(0,8))
        editor=ttk.Frame(self);editor.pack(fill='x')
        self.variables={key:tk.StringVar() for key in ('name','dose_mg','interval_h','count','source','volume_l','half_life_h')}
        for col,(key,label,width) in enumerate((('name','药物 / 成分名称',26),('dose_mg','实际剂量 mg · 可选',15),('interval_h','用药间隔 h · 可选',16),('count','次数 · 可选',10))):
            ttk.Label(editor,text=label).grid(row=0,column=col,sticky='w',padx=5)
            if key=='name':
                widget=ttk.Combobox(editor,textvariable=self.variables[key],values=('雌二醇','比卡鲁胺','氟康唑','咪达唑仑','托法替布','atomoxetine'),width=width)
            else:widget=ttk.Entry(editor,textvariable=self.variables[key],width=width)
            widget.grid(row=1,column=col,sticky='ew',padx=5,pady=3)
        self.route=tk.StringVar(value='口服 / 片剂');self.category=tk.StringVar(value='medicine')
        ttk.Label(editor,text='途径 / 剂型').grid(row=0,column=4,sticky='w')
        ttk.Combobox(editor,textvariable=self.route,values=tuple(ROUTES),state='readonly',width=20).grid(row=1,column=4,padx=5)
        self.custom=tk.BooleanVar();self.advanced=tk.BooleanVar();self.online=tk.BooleanVar(value=True)
        options=ttk.Frame(self);options.pack(fill='x',pady=5)
        ttk.Checkbutton(options,text='按自定义物质处理',variable=self.custom).pack(side='left')
        ttk.Combobox(options,textvariable=self.category,state='readonly',values=('medicine','supplement','botanical','food_beverage','other'),width=16).pack(side='left',padx=8)
        ttk.Checkbutton(options,text='优先在线查询（失败使用离线资料）',variable=self.online).pack(side='left',padx=8)
        ttk.Checkbutton(options,text='高级：合成 IV 假设曲线',variable=self.advanced,command=self.toggle_advanced).pack(side='left',padx=8)
        self.defaults=tk.StringVar();ttk.Label(self,textvariable=self.defaults,wraplength=1050).pack(fill='x',pady=4)
        self.advanced_box=ttk.LabelFrame(self,text='合成模型参数 · 不代表所填药物的真实暴露',padding=6)
        for col,(key,label) in enumerate((('volume_l','容积 L'),('half_life_h','半衰期 h'),('source','来源 / 备注'))):
            ttk.Label(self.advanced_box,text=label).grid(row=0,column=col*2,padx=5)
            ttk.Entry(self.advanced_box,textvariable=self.variables[key],width=20).grid(row=0,column=col*2+1)
        self.actions=ttk.Frame(self);self.actions.pack(fill='x',pady=5)
        for label,command in [('添加',self.add),('更新选中',lambda:self.add(True)),('删除选中',self.remove),('分析联用机制',self.calculate),('导出报告',self.export),('生理 / 基因',self.open_context),('来源 / 条件估计',self.open_sources)]:
            ttk.Button(self.actions,text=label,command=command).pack(side='left',padx=3)
        self.status=tk.StringVar(value='等待添加药物。');ttk.Label(self,textvariable=self.status,wraplength=1050).pack(fill='x',pady=4)
        self.listing=ttk.Treeview(self,columns=('route','dose','half'),height=4,selectmode='browse')
        self.listing.heading('#0',text='药物 / 身份');self.listing.column('#0',width=280)
        for key,label in [('route','途径'),('dose','剂量 mg'),('half','资料半衰期 h')]:
            self.listing.heading(key,text=label);self.listing.column(key,width=150)
        self.listing.pack(fill='x');self.listing.bind('<<TreeviewSelect>>',self.load_row)
        from src.navigation import StableNotebook
        self.results=StableNotebook(self);self.results.pack(fill='both',expand=True,pady=6)
        report_host=ttk.Frame(self.results);self.results.add(report_host,text='联用机制与证据')
        self.report_host=report_host
        self.report=tk.Text(report_host,wrap='word',bg='#17222E',fg='#E8EFF5',font=('Microsoft YaHei UI',10),state='disabled',height=8)
        scrollbar=ttk.Scrollbar(report_host,command=self.report.yview);self.report.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y');self.report.pack(fill='both',expand=True)
        exposure_host=ttk.Frame(self.results);self.results.add(exposure_host,text='高级假设曲线数据')
        self.exposure=ttk.Treeview(exposure_host,show='headings');self.exposure.pack(fill='both',expand=True)
        for value in list(self.variables.values())+[self.route,self.custom,self.category,self.online,self.advanced]:value.trace_add('write',self.invalidate)
        self.invalidate();self.after(100,self.poll)

    def toggle_advanced(self):
        if self.advanced.get():self.advanced_box.pack(fill='x',before=self.actions,pady=5)
        else:self.advanced_box.pack_forget()

    def show(self,text):
        self.report.configure(state='normal');self.report.delete('1.0','end');self.report.insert('1.0',text);self.report.configure(state='disabled')

    def invalidate(self,*_):
        self.generation+=1;self.result=None
        self.exposure.delete(*self.exposure.get_children())
        self.show('输入或方案已变化，点击“分析联用机制”更新结果。')
        from src.drug_library import resolve_name,profile_for
        identity=resolve_name(self.variables['name'].get()) if not self.custom.get() else None
        p=profile_for(identity,ROUTES[self.route.get()]) if identity else None
        if self.advanced.get():self.defaults.set('高级模式需要手动假设参数，结果仅用于合成 IV 模型。')
        elif p:
            half=p.get('half_life_h');self.defaults.set(f"资料默认：{p.get('name',identity)} · {p.get('formulation','')} · 半衰期 {str(half)+' h' if half else '未提供匹配值'}。{p.get('parameter_note','')}")
        else:self.defaults.set('自定义 / 未识别物质：可添加并查看证据缺口；不会按同名药物继承参数。')

    def add(self,update=False):
        try:
            item=editor_item({k:v.get() for k,v in self.variables.items()},ROUTES[self.route.get()],self.custom.get(),self.advanced.get(),self.category.get())
            candidate=list(self.rows);selected=self.listing.selection()
            if update:
                if not selected:raise ValueError('请先选择要更新的药物。')
                candidate[int(selected[0])]=item
            else:candidate.append(item)
            simulate(candidate,self.context);self.rows=candidate;self.refresh()
        except (ValueError,OverflowError) as exc:self.status.set('无法添加：'+str(exc))

    def refresh(self):
        self.listing.delete(*self.listing.get_children())
        for i,item in enumerate(self.rows):
            self.listing.insert('','end',iid=str(i),text=item['name']+' · '+item['kind'],values=(item['route'],item.get('dose_mg') or '未填写',item.get('half_life_h') or '无匹配值'))
        self.invalidate();self.status.set(f'已添加 {len(self.rows)} 种。可直接分析，缺少药代参数不会阻止机制查询。')
        if self.body:self.body.drug=None;self.body.choice.set('未选择物质');self.body.render()

    def selected_item(self):
        selected=self.listing.selection()
        return dict(self.rows[int(selected[0])]) if selected else None

    def load_row(self,_):
        item=self.selected_item()
        if not item:return
        for key,var in self.variables.items():var.set('' if item.get(key) is None else str(item[key]))
        self.route.set(next(k for k,v in ROUTES.items() if v==item['route']))
        self.custom.set(item['kind']=='custom');self.category.set(item.get('category','medicine'))
        self.advanced.set(item.get('model_mode')=='synthetic');self.toggle_advanced()
        if self.body:self.body.drug=item;self.body.choice.set('方案选中 / '+item['name']);self.body.render()

    def remove(self):
        for i in sorted((int(i) for i in self.listing.selection()),reverse=True):self.rows.pop(i)
        self.refresh()

    def calculate(self):
        if self.busy:self.status.set('查询正在进行；输入变化后旧结果会自动作废。');return
        self.invalidate();self.results.select(self.report_host)
        try:result=simulate(copy.deepcopy(self.rows),copy.deepcopy(self.context))
        except (ValueError,OverflowError) as exc:self.status.set(str(exc));return
        self.busy=True;generation=self.generation;items=copy.deepcopy(self.rows);online=self.online.get()
        self.status.set('查询公开药物说明书中…仅发送药物成分名称，不发送剂量、生理或基因信息。' if online else '正在校验离线资料…')
        def work():
            try:
                from src.drug_library import analyze_labels
                result['label_analysis']=analyze_labels(items,online=online)
                self.mail.put((generation,result,None))
            except Exception as exc:self.mail.put((generation,None,str(exc)))
        threading.Thread(target=work,daemon=True).start()

    def poll(self):
        try:
            generation,result,error=self.mail.get_nowait();self.busy=False
            if generation!=self.generation:self.status.set('查询结束，但输入已变化；旧结果已丢弃，请重新分析。')
            elif error:self.status.set('查询失败：'+error)
            else:
                self.result=result;self.display_result(result)
        except queue.Empty:pass
        self.after(100,self.poll)

    def display_result(self,result):
        labels=result['label_analysis'];lines=['联用机制与证据',labels.get('note',''),'']
        for record in labels.get('records',[]):
            lines.extend([f"{record.get('name',record.get('compound_id',''))} · {record.get('status','')}",record.get('summary',''),
                          '来源：'+record.get('url',''), '获取：'+str(record.get('retrieved_at',''))])
            if record.get('error'):lines.append('在线查询说明：'+str(record['error']))
            lines.append('')
        for index,pair in enumerate(labels.get('pairs',[])):
            names=result['pairs'][index]['drugs']
            lines.extend([' + '.join(names)+' · '+pair['status'],pair.get('summary','')]+pair.get('sources',[])+[''])
        for pair in result['pairs']:
            lines.append(' + '.join(pair['drugs'])+' · 既有研究库：'+pair['status'])
            for ev in pair['evidence']:lines.extend(study_lines(ev))
        lines.extend(['','未计算个体联用浓度/风险倍率；机制线索不等同于临床配伍结论。',result['context']['note'],
                      '输入 SHA256：'+result['input_sha256']])
        self.show('\n'.join(lines));self.status.set(f"已分析 {len(self.rows)} 种 / {len(result['pairs'])} 对；在线 / 缓存 / 离线来源见报告。")
        curves=result['curves'];columns=['time']+[str(i) for i in range(len(curves))];self.exposure.configure(columns=columns)
        for col,title in zip(columns,['时间 h']+[c['name'] for c in curves]):self.exposure.heading(col,text=title);self.exposure.column(col,width=150)
        if curves:
            for i,t in enumerate(result['times_h']):self.exposure.insert('','end',values=[f'{t:.6g}']+[f"{c['values'][i]:.6g}" for c in curves])

    def export(self):
        if self.result is None:self.status.set('请先分析当前方案。');return
        path=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('JSON','*.json')])
        if path:
            try:
                with open(path,'w',encoding='utf-8') as stream:json.dump(self.result,stream,ensure_ascii=False,indent=2,allow_nan=False)
                self.status.set('已保存报告：'+path)
            except OSError as exc:self.status.set(str(exc))

    def open_context(self):
        from src.context_dialog import edit_context
        def save(context):
            self.context=context;self.invalidate()
            if self.body:self.body.render()
        edit_context(self,self.context,save)

    def open_sources(self):
        from src.pgx_dialog import open_pgx
        open_pgx(self)
