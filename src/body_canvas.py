"""Depth-sorted anatomical mesh viewer with orbit, zoom and evidence picking."""
import math
import tkinter as tk
from src.anatomy_mesh import PARTS,SHELL,mesh,rotate,clamp_zoom
COLORS={'mechanism':'#5BD8C7','metabolism':'#8EAFFF','excretion':'#8ED6E2','label_concern':'#E7B45A'}

class BodyCanvas(tk.Canvas):
 def __init__(self,parent,select,hover,**kwargs):
  super().__init__(parent,background='#101D28',highlightthickness=0,**kwargs)
  self.select=select;self.hover=hover;self.effects={};self.selected=None;self.members=[]
  self.view='正面';self.reproductive='隐藏';self.yaw=0.;self.pitch=0.;self.zoom=1.
  self._start=None;self._moved=False;self._pending=None
  self.parts=[(k,*mesh(c,r,k,rows=10,cols=16)) for k,c,r in PARTS]
  self.shell=[mesh(c,r,rows=8,cols=12) for c,r in SHELL]
  self.bind('<Configure>',lambda _:self.schedule())
  self.bind('<ButtonPress-1>',self.press);self.bind('<B1-Motion>',self.drag)
  self.bind('<ButtonRelease-1>',self.release);self.bind('<Motion>',self.motion)
  self.bind('<MouseWheel>',lambda e:self.zoom_by(1.12 if e.delta>0 else 1/1.12))
  self.bind('<Button-4>',lambda _:self.zoom_by(1.12));self.bind('<Button-5>',lambda _:self.zoom_by(1/1.12))
 def schedule(self):
  if self._pending is None:self._pending=self.after_idle(self.draw)
 def update_map(self,effects,selected,members,view,reproductive):
  if view!=self.view:self.yaw=0 if view=='正面' else math.pi;self.pitch=0
  self.effects=effects;self.selected=selected;self.members=members;self.view=view;self.reproductive=reproductive;self.schedule()
 def reset_view(self):
  self.yaw=0 if self.view=='正面' else math.pi;self.pitch=0;self.zoom=1.;self.schedule()
 def zoom_by(self,factor):self.zoom=clamp_zoom(self.zoom*factor);self.schedule()
 def region_at(self,x,y):
  for item in reversed(self.find_overlapping(x,y,x,y)):
   for tag in self.gettags(item):
    if tag.startswith('region:'):return tag[7:]
  return None
 def press(self,e):self._start=(e.x,e.y,self.yaw,self.pitch);self._moved=False
 def drag(self,e):
  if self._start is None:return
  x,y,a,b=self._start;dx,dy=e.x-x,e.y-y
  if dx*dx+dy*dy>16:self._moved=True
  if self._moved:
   self.yaw=a+dx*.012;self.pitch=max(-1.4,min(1.4,b+dy*.009));self.schedule()
 def release(self,e):
  if self._start is not None and not self._moved:
   region=self.region_at(e.x,e.y)
   if region:self.select(region)
  self._start=None
 def motion(self,e):
  if self._start is None:self.hover(self.region_at(e.x,e.y))
 def draw(self):
  self._pending=None;self.delete('all')
  w,h=self.winfo_width(),self.winfo_height();scale=min(max(w-24,1)/210,max(h-38,1)/550)*self.zoom
  def project(p):
   x,y,z=rotate(p,self.yaw,self.pitch);perspective=900/(900-z)
   return (w/2+x*scale*perspective,(h-24)/2+y*scale*perspective,z)
  # Body envelope stays a faint wire mask; all organs carry depth and move together.
  for vertices,faces in self.shell:
   pts=[project(p) for p in vertices]
   for i in range(1,8):
    ring=[pts[i*12+j] for j in range(12)];ring.append(ring[0])
    self.create_line([v for p in ring for v in p[:2]],fill='#263F4B',width=.6,smooth=True)
   for j in (0,3,6,9):
    self.create_line([v for i in range(9) for v in pts[i*12+j][:2]],fill='#263F4B',width=.6,smooth=True)
  surfaces=[]
  for kind,vertices,faces in self.parts:
   if kind in ('testes','uterus') and self.reproductive!={'testes':'睾丸分层','uterus':'子宫分层'}[kind]:continue
   pts=[project(p) for p in vertices]
   base=COLORS.get(self.effects.get(kind),'#78949F');rgb=[int(base[i:i+2],16) for i in (1,3,5)]
   for face in faces:
    # Surface lighting and denser longitudinal edges reveal volumes and muscle bundles.
    q=[pts[i] for i in face]
    cross=(q[1][0]-q[0][0])*(q[2][1]-q[0][1])-(q[1][1]-q[0][1])*(q[2][0]-q[0][0])
    if cross>=0:continue
    depth=sum(p[2] for p in q)/4
    brightness=.58+.35*(depth+60)/120;brightness=max(.4,min(1,brightness))
    color='#'+''.join(f'{int(c*brightness):02x}' for c in rgb)
    surfaces.append((depth,kind,[v for p in q for v in p[:2]],color))
  for _,kind,points,color in sorted(surfaces,key=lambda v:v[0]):
   active=kind in self.effects;selected=kind==self.selected;linked=kind in self.members
   self.create_polygon(points,fill=color,stipple='gray75' if active else 'gray25',
      outline='#91AAB6' if selected else '#657F8B' if linked else '',
      width=.65 if selected else .35,tags=('region:'+kind,))
  self.create_text(w/2,h-12,text=f'拖动旋转 · 滚轮缩放 {self.zoom:.0%}',fill='#A9BAC8',font=('Microsoft YaHei UI',9))
