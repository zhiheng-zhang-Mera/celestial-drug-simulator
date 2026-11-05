"""Offline geometry adapter. Model provenance is distinct from drug evidence."""
import json
from functools import lru_cache
from pathlib import Path
from src.anatomy_mesh import PARTS, mesh

ATLAS_PATH = Path(__file__).resolve().parents[1] / 'assets/anatomy/bodyparts3d.json'

def skin_groups(vertices):
    """Local convex envelopes of source skin; no decimation crease lines."""
    groups={}
    for point in vertices:
        x,y,z=point
        band=next((i for i,end in enumerate((-210,-180,-40,20,65,140,250,271)) if y<=end),7)
        side=0
        if band in (2,3):side=-1 if x < -45 else 1 if x > 45 else 0
        elif band in (4,5):side=(-2 if x<0 else 2) if abs(x)>55 else (-1 if x<0 else 1)
        elif band>=6:side=-1 if x<0 else 1
        groups.setdefault((band,side),[]).append(point)
    return list(groups.values())

def convex_hull(points):
    """2D monotone chain used only for the faint external mask."""
    pts=sorted(set((p[0],p[1]) for p in points))
    if len(pts)<3:return pts
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower=[];upper=[]
    for p in pts:
        while len(lower)>=2 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper)>=2 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]

@lru_cache(maxsize=2)
def load_atlas(low_detail=False):
    data=json.loads(ATLAS_PATH.read_text(encoding='utf-8'))
    skin=next(p for p in data['parts'] if p['region']=='shell')['vertices']
    lower=min(p[2] for p in skin);upper=max(p[2] for p in skin)
    scale=540/(upper-lower)
    cx=(min(p[0] for p in skin)+max(p[0] for p in skin))/2
    cy=(min(p[1] for p in skin)+max(p[1] for p in skin))/2
    parts=[]
    for part in data['parts']:
        # Original: x=left,y=posterior,z=superior. Viewer: y=down,z=anterior.
        points=part.get('lod_vertices',part['vertices']) if low_detail else part['vertices']
        triangles=part.get('lod_faces',part['faces']) if low_detail else part['faces']
        v=[((x-cx)*scale,270-(z-lower)*scale,-(y-cy)*scale) for x,y,z in points]
        # Axis reflection intentionally converts outward STL winding into the
        # viewer's existing inward winding (negative projected area faces camera).
        f=[tuple(face) for face in triangles]
        parts.append((part['region'],v,f))
    # The source is one male reference. Uterus remains an explicitly labeled schematic.
    bladder=next(v for k,v,f in parts if k=='bladder')
    anchor=[(min(p[i] for p in bladder)+max(p[i] for p in bladder))/2 for i in range(3)]
    for kind,center,radii in PARTS:
        if kind=='uterus':
            v,f=mesh(center,radii,kind,rows=8,cols=12)
            v=[(x*.65+anchor[0],(y-88)*.65+anchor[1]-8,z*.65+anchor[2]-12) for x,y,z in v]
            parts.append((kind,v,f))
    return parts
