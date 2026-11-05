"""Tk lifecycle adapter for the local embedded HTML renderer."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk
from src.web_anatomy import make_state, read_selection, fallback_view


class WebBody(ttk.Frame):
    def __init__(self,parent,on_select):
        super().__init__(parent)
        self.on_select=on_select;self.process=None;self.pending=None;self.events=queue.Queue()
        self.stopped=False;self.ready=False;self.fallback=None
        self.host=tk.Frame(self,bg='#051530');self.host.pack(fill='both',expand=True)
        self.notice=ttk.Label(self.host,text='正在加载内嵌 HTML 人体视图…');self.notice.pack(pady=30)
        footer=ttk.Frame(self);footer.pack(fill='x')
        self.status=tk.StringVar(value='HTML X-Ray · 本地离线资源')
        ttk.Label(footer,textvariable=self.status).pack(side='left')
        ttk.Button(footer,text='简化视图',command=self.use_fallback).pack(side='right')
        self.host.bind('<Configure>',self.resize)
        self.bind('<Destroy>',self.destroyed)
        self.after(100,self.start)

    def start(self):
        if self.stopped:return
        root=Path(__file__).resolve().parents[1]
        logs=root/'data/cache';logs.mkdir(parents=True,exist_ok=True)
        self.log=(logs/'webview.log').open('w',encoding='utf-8')
        try:
            env=dict(os.environ,PYTHONIOENCODING='utf-8')
            self.process=subprocess.Popen([sys.executable,'-m','src.webview_host',str(self.host.winfo_id()),
                str(self.host.winfo_width()),str(self.host.winfo_height())],cwd=root,env=env,
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,encoding='utf-8',
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            threading.Thread(target=self.read,daemon=True).start()
            self.after(50,self.poll);self.after(15000,self.timeout)
        except OSError as exc:self.error(str(exc))

    def read(self):
        for line in self.process.stdout:self.events.put(line)

    def send(self,message):
        if self.process and self.process.poll() is None:
            try:self.process.stdin.write(json.dumps(message,ensure_ascii=True)+'\n');self.process.stdin.flush()
            except (OSError,ValueError):self.error('渲染进程连接已断开')

    def poll(self):
        if self.stopped:return
        while not self.events.empty():
            line=self.events.get_nowait();selected=read_selection(line)
            if selected:self.on_select(selected);continue
            try:data=json.loads(line)
            except ValueError:continue
            if data.get('event')=='ready':
                self.ready=True;self.notice.pack_forget();self.status.set('HTML X-Ray · 离线渲染已就绪')
                if self.pending:self.send({'action':'state','state':self.pending})
            elif data.get('event')=='error':self.error(data.get('message','渲染失败'))
        if self.process and self.process.poll() is not None:
            self.error('HTML 渲染进程已退出；可使用简化视图。');return
        self.after(50,self.poll)

    def error(self,message):
        self.status.set(message);self.notice.configure(text=message);self.notice.pack(pady=30)

    def timeout(self):
        if not self.stopped and not self.ready:self.error('HTML 未能就绪；检查 WebEngine / 图形支持，或使用简化视图。')

    def resize(self,event):
        if event.widget==self.host:self.send({'action':'size','width':event.width,'height':event.height})

    def update_state(self,drug,selected):
        self.pending=make_state(drug,selected)
        if self.fallback:
            self.update_fallback()
        elif self.ready:self.send({'action':'state','state':self.pending})

    def update_fallback(self):
        p=self.pending;view,layer=fallback_view(p['selected'])
        self.fallback.update_map(p['effects'],p['selected'],p['members'],view,layer)

    def use_fallback(self):
        if self.fallback:return
        self.stop();self.host.destroy()
        from src.body_canvas import BodyCanvas
        self.fallback=BodyCanvas(self,self.on_select,lambda _:None,width=600,height=600)
        self.fallback.pack(fill='both',expand=True)
        self.status.set('简化参考图谱视图 · 重启模块可恢复 HTML')
        if self.pending:
            self.update_fallback();self.on_select(self.pending['selected'])

    def stop(self):
        self.stopped=True
        if self.process:
            self.send({'action':'close'})
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:self.process.terminate()
        if hasattr(self,'log'):self.log.close()

    def destroyed(self,event):
        if event.widget==self:self.stop()
