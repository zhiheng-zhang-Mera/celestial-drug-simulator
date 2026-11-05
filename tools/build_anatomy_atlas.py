"""Reproduce the offline atlas from pinned, attributed BodyParts3D STL assets.

Run: python tools/build_anatomy_atlas.py --cache <directory>
No upstream code is executed. Source meshes keep their separate CC BY-SA terms.
"""
import argparse
import concurrent.futures
import hashlib
import json
import math
from pathlib import Path
import struct
import urllib.request
import subprocess

COMMIT = 'f0eeb6e843380cfe6b83797cf8c3e1af74de5e61'
BASE = f'https://raw.githubusercontent.com/Kevin-Mattheus-Moerman/BodyParts3D/{COMMIT}/'
ROOT = Path(__file__).resolve().parents[1]

def read_stl(raw):
    count = struct.unpack_from('<I', raw, 80)[0]
    if len(raw) != 84 + count * 50:
        raise ValueError('Invalid binary STL length')
    vertices, faces, index = [], [], {}
    for offset in range(84, len(raw), 50):
        values = struct.unpack_from('<12fH', raw, offset)
        face = []
        for j in (3, 6, 9):
            point = tuple(values[j:j+3])
            if not all(math.isfinite(v) for v in point):
                raise ValueError('Nonfinite STL vertex')
            if point not in index:
                index[point] = len(vertices)
                vertices.append(point)
            face.append(index[point])
        faces.append(face)
    return vertices, faces

def cluster(vertices, faces, cell):
    bins, remap = {}, []
    for point in vertices:
        key = tuple(round(v / cell) for v in point)
        if key not in bins:
            bins[key] = [len(bins), [0., 0., 0.], 0]
        item = bins[key]
        for k in range(3): item[1][k] += point[k]
        item[2] += 1
        remap.append(item[0])
    out = [[round(n / item[2], 4) for n in item[1]] for item in bins.values()]
    triangles, seen = [], set()
    for face in faces:
        f = [remap[i] for i in face]
        key = tuple(sorted(f))
        if len(set(f)) == 3 and key not in seen:
            seen.add(key)
            triangles.append(f)
    used = sorted({i for f in triangles for i in f})
    indices = {old:new for new,old in enumerate(used)}
    return [out[i] for i in used], [[indices[i] for i in f] for f in triangles]

def simplify(vertices, faces, budget):
    lo, hi = .05, max(max(p[k] for p in vertices)-min(p[k] for p in vertices) for k in range(3))
    best = cluster(vertices, faces, hi)
    for _ in range(17):
        cell = (lo+hi)/2
        result = cluster(vertices, faces, cell)
        if len(result[1]) <= budget: hi, best = cell, result
        else: lo = cell
    return best

def main(cache):
    cache.mkdir(parents=True, exist_ok=True)
    def download(path):
        destination = cache / Path(path).name
        if not destination.exists():
            temporary=destination.with_suffix(destination.suffix+'.part')
            subprocess.run(['curl.exe','--fail','--location','--silent','--show-error',
                '--retry','3','--max-time','180',BASE+path,'--output',str(temporary)],check=True)
            temporary.replace(destination)
        return destination.read_bytes()
    names_raw = download('assets/BodyParts3D_data/parts_list_e.txt')
    names = dict(line.split('\t',1) for line in names_raw.decode().splitlines()[1:] if '\t' in line)
    composite_raw = download('assets/BodyParts3D_data/composite_parts.txt')
    index=cache/'tree.json'
    if not index.exists():
        index.write_bytes(urllib.request.urlopen(f'https://api.github.com/repos/Kevin-Mattheus-Moerman/BodyParts3D/git/trees/{COMMIT}?recursive=1').read())
    tree=json.loads(index.read_text(encoding='utf-8-sig'))
    if tree['sha'] != COMMIT: raise ValueError('Unexpected upstream tree')
    available = {Path(p['path']).stem for p in tree['tree'] if p['path'].endswith('.stl')}
    cortex = sorted(({line.split('\t')[2] for line in composite_raw.decode().splitlines()[1:] if line.startswith('FMA61830\t')} |
        {'FMA72975','FMA72976','BP49','BP50','FMA61822','FMA67944'}) & available)
    groups = [('brain', cortex, 4500), ('shell',['FMA7163'],12000)]
    for region, ids, budget in (
        ('heart',[7274],600),('liver',[7197],500),('stomach',[7148],400),
        ('kidneys',[7204,7205],300),('lungs',[7333,7337,7370,7371,7383],220),
        ('bladder',[15900],220),('testes',[7211,7212],100),
        ('biceps',range(37684,37688),150),('triceps',range(37695,37701),150),
        ('quadriceps',range(38928,38936),180)):
        groups += [(region, ['FMA'+str(i)], budget) for i in ids]
    ids = sorted({key for _, group, _ in groups for key in group})
    def get_mesh(key):
        path='assets/BodyParts3D_data/stl/'+key+'.stl'
        raw=download(path)
        expected=next(item['sha'] for item in tree['tree'] if item['path']==path)
        actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if actual!=expected:raise ValueError('Source blob mismatch: '+key)
        return key, raw
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        sources = dict(pool.map(get_mesh, ids))
    parts=[]
    for region, group, budget in groups:
        fingerprint=hashlib.sha256(('cluster-v1:'+str(budget)+':'+''.join(hashlib.sha256(sources[k]).hexdigest() for k in group)).encode()).hexdigest()
        cached=cache/(fingerprint+'.json')
        if cached.exists():
            parts.append(json.loads(cached.read_text(encoding='utf-8')))
            continue
        vertices, faces = [], []
        for key in group:
            v,f=read_stl(sources[key]);offset=len(vertices)
            vertices.extend(v);faces.extend([[i+offset for i in t] for t in f])
        vertices,faces=simplify(vertices,faces,budget)
        parts.append(dict(region=region,source_ids=group,names=[names.get(k,k) for k in group],budget=budget,
            source_sha256={k:hashlib.sha256(sources[k]).hexdigest() for k in group},
            vertices=vertices,faces=faces))
        cached.write_text(json.dumps(parts[-1],separators=(',',':')),encoding='utf-8')
        print(region, group, len(vertices), len(faces), flush=True)
    for part in parts:
        budget=2400 if part['region']=='shell' else 800 if part['region']=='brain' else 70 if part['region'] in ('biceps','triceps','quadriceps') else 150
        v,f=simplify(part['vertices'],part['faces'],budget)
        part['lod_vertices']=v;part['lod_faces']=f
    out=ROOT/'assets/anatomy'
    out.mkdir(parents=True,exist_ok=True)
    (out/'LICENSE-BodyParts3D.txt').write_bytes(download('LICENSE_content'))
    (out/'bodyparts3d.json').write_text(json.dumps(dict(source_commit=COMMIT,
        license='CC-BY-SA-2.1-JP',coordinate_system='x left; y posterior; z superior; millimeters',
        adaptation='Deterministic vertex clustering; selected source subsets; no clinical validation',parts=parts),separators=(',',':')),encoding='utf-8')

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cache',type=Path,required=True)
    main(parser.parse_args().cache)
