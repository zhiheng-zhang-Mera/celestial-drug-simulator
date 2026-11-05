"""Original scalable 2D anatomical contours; no measured tissue simulation."""
import tkinter as tk

# Normalized front-view coordinates, patient right is viewer left.
OUTLINE = [140,18,123,23,115,40,116,62,125,77,131,82,131,99,111,104,87,111,77,130,68,166,56,214,45,263,38,294,43,307,51,303,63,272,77,223,87,190,91,169,94,220,89,253,89,279,99,306,106,343,107,391,109,435,108,476,102,496,110,504,128,503,132,489,130,447,131,399,139,351,146,314,153,351,161,399,162,447,160,489,164,503,183,504,190,496,184,476,183,435,185,391,186,343,194,306,204,279,204,253,199,220,202,169,207,190,217,223,231,272,243,303,252,307,257,294,250,263,239,214,227,166,218,130,207,111,183,104,163,99,163,82,170,77,178,62,178,40,170,23,154,18]
SHAPES = {
 'brain': [[146,27,129,29,122,40,123,53,128,67,143,70,147,65,152,70,166,66,174,54,173,39,162,28]],
 'lungs': [[135,117,122,118,108,139,102,169,109,186,134,179,139,160], [159,117,173,119,188,141,193,169,186,186,160,179,155,159]],
 'heart': [[147,147,140,140,132,145,132,158,144,173,153,179,163,165,162,153,155,147]],
 'liver': [[100,188,114,183,135,185,155,192,178,194,171,205,149,210,122,222,103,220,98,207]],
 'stomach': [[165,207,164,217,175,225,185,225,188,235,180,249,166,252,153,245,151,232,159,223,157,209]],
 'kidneys': [[113,229,104,236,104,251,111,259,119,255,117,249,113,247,119,239], [181,229,190,236,190,251,183,259,175,255,177,249,181,247,175,239]],
 'bladder': [[134,279,132,290,139,301,147,305,155,301,163,290,160,279,147,277]],
 'uterus': [[135,302,126,298,121,302,126,306,136,309,141,320,143,329,150,329,153,320,158,309,169,306,174,302,168,298,159,302,147,299]],
 'testes': [[137,327,130,332,131,344,138,348,144,341,143,333], [154,327,160,332,160,344,154,348,148,341,148,333]],
 'biceps': [[85,137,78,154,73,178,78,190,85,179,91,153], [209,137,216,154,221,178,216,190,209,179,203,153]],
 'triceps': [[84,134,75,146,67,175,70,195,80,187,87,163], [210,134,219,146,227,175,224,195,214,187,207,163]],
 'quadriceps': [[105,308,110,340,114,379,123,388,130,375,133,346,140,313,126,302], [189,308,184,340,180,379,171,388,164,375,161,346,154,313,168,302]],
}
COLORS = {'mechanism':'#5BD8C7','metabolism':'#8EAFFF','excretion':'#8ED6E2','label_concern':'#E7B45A'}

class BodyCanvas(tk.Canvas):
    def __init__(self, parent, select, hover, **kwargs):
        super().__init__(parent, background='#101D28', highlightthickness=0, **kwargs)
        self.select = select; self.hover = hover
        self.view='正面'; self.reproductive='隐藏'; self.effects={}; self.selected=None; self.members=[]
        self.bind('<Configure>', lambda _: self.draw())
    def update_map(self, effects, selected, members, view, reproductive):
        self.effects=effects; self.selected=selected; self.members=members; self.view=view; self.reproductive=reproductive; self.draw()
    def draw(self):
        self.delete('all')
        width,height=self.winfo_width(),self.winfo_height()
        scale=min(max(width-30,1)/300,max(height-38,1)/520)
        ox=(width-294*scale)/2; oy=12
        def coords(points): return [v*scale+(ox if i%2==0 else oy) for i,v in enumerate(points)]
        self.create_polygon(coords(OUTLINE),smooth=True,splinesteps=20,fill='#182B36',outline='#647E8A',width=1.3,stipple='gray25')
        # Torso midline, clavicles, ribs and pelvic contour provide depth without skin colors.
        for points in ([147,83,147,114,147,139],[114,113,130,116,147,112,164,116,180,113],
                       [100,258,119,266,132,279],[194,258,175,266,162,279],
                       [147,181,147,259]):
            self.create_line(coords(points),fill='#36505F',smooth=True,width=1)
        for dy in range(0,44,11):
            self.create_line(coords([106,139+dy,121,146+dy,137,142+dy]),fill='#2C4755',smooth=True)
            self.create_line(coords([188,139+dy,173,146+dy,157,142+dy]),fill='#2C4755',smooth=True)
        for region, polygons in SHAPES.items():
            if region=='biceps' and self.view=='背面': continue
            if region=='triceps' and self.view=='正面': continue
            if region in ('uterus','testes') and self.reproductive!={'uterus':'子宫分层','testes':'睾丸分层'}[region]: continue
            category=self.effects.get(region)
            color=COLORS.get(category,'#526D7A')
            for points in polygons:
                item=self.create_polygon(coords(points),smooth=True,splinesteps=20,fill=color,
                    stipple='gray75' if category else 'gray25',outline='#E8EFF5' if region==self.selected else color,
                    width=2.5 if region==self.selected else 1.2,tags=(region,))
                self.tag_bind(item,'<Button-1>',lambda _,r=region:self.select(r))
                self.tag_bind(item,'<Enter>',lambda _,r=region:self.hover(r))
                self.tag_bind(item,'<Leave>',lambda _:self.hover(None))
                if region in self.members:
                    # Dotted relation outline is distinct from a bright evidence fill.
                    self.create_polygon(coords(points),smooth=True,fill='',outline='#FFFFFF',dash=(3,4),width=2,tags=(region,))
                    self.tag_bind(region,'<Button-1>',lambda _,r=region:self.select(r))
            if region in ('brain','quadriceps','biceps','triceps'):
                for points in polygons:
                    xs=points[::2];ys=points[1::2];cx=sum(xs)/len(xs)
                    for delta in (-3,3):
                        self.create_line(coords([cx+delta,min(ys)+5,cx+delta-2,(min(ys)+max(ys))/2,cx+delta,max(ys)-5]),fill='#96AFB8',smooth=True,stipple='gray50')
        self.create_text(width/2,height-13,text=self.view+' · 示意组织蒙版 / 非组织动力学',fill='#A9BAC8',font=('Microsoft YaHei UI',9))
