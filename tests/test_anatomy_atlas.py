import unittest
from pathlib import Path
import json, math

class AtlasTests(unittest.TestCase):
 def test_bundle_geometry_and_provenance(self):
  p=Path(__file__).parents[1]/'assets/anatomy/bodyparts3d.json'
  self.assertTrue(p.is_file(), 'offline atlas bundle is required')
  data=json.loads(p.read_text(encoding='utf-8'))
  self.assertEqual(data['source_commit'],'f0eeb6e843380cfe6b83797cf8c3e1af74de5e61')
  self.assertEqual(data['license'],'CC-BY-SA-2.1-JP')
  regions={part['region'] for part in data['parts']}
  self.assertTrue({'brain','heart','lungs','liver','stomach','kidneys','bladder','testes','biceps','triceps','quadriceps','shell'} <= regions)
  self.assertLess(sum(len(p['faces']) for p in data['parts']),25000)
  for part in data['parts']:
   self.assertTrue(part['source_sha256'])
   self.assertTrue(all(math.isfinite(n) for v in part['vertices'] for n in v))
   self.assertTrue(all(len(set(f))==3 and all(0<=i<len(part['vertices']) for i in f) for f in part['faces']))
   self.assertGreater(len(part['faces']),10)

 def test_viewer_uses_one_aligned_coordinate_system(self):
  from src.anatomy_atlas import load_atlas
  parts=load_atlas()
  skin=next(v for k,v,f in parts if k=='shell')
  self.assertAlmostEqual(min(v[1] for v in skin),-270)
  self.assertAlmostEqual(max(v[1] for v in skin),270)
  centers={}
  for kind,vertices,faces in parts:
   centers.setdefault(kind,[]).extend(vertices)
  y=lambda key:sum(p[1] for p in centers[key])/len(centers[key])
  self.assertLess(y('brain'),y('heart'))
  self.assertLess(y('heart'),y('bladder'))
  self.assertLess(y('bladder'),y('quadriceps'))
  self.assertEqual(sum(k=='uterus' for k,v,f in parts),3)
  self.assertLess(abs(y('uterus')-y('bladder')),20,'schematic must stay in imported pelvis')

 def test_simplification_is_deterministic_and_preserves_orientation(self):
  from tools.build_anatomy_atlas import cluster
  v=[(0,0,0),(1,0,0),(0,1,0),(0.01,0.01,0)]
  f=[(0,1,2),(3,1,2)]
  a=cluster(v,f,.1)
  self.assertEqual(a,cluster(v,f,.1))
  self.assertEqual(len(a[1]),1)
  p,q,r=[a[0][i] for i in a[1][0]]
  self.assertGreater((q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0]),0)

 def test_atlas_matches_viewer_inward_winding(self):
  from src.anatomy_atlas import load_atlas
  _,vertices,faces=next(p for p in load_atlas() if p[0]=='liver')
  center=[sum(v[i] for v in vertices)/len(vertices) for i in range(3)]
  signed_volume=0
  for face in faces:
   a,b,c=[[vertices[j][i]-center[i] for i in range(3)] for j in face]
   cross=(b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0])
   signed_volume+=sum(a[i]*cross[i] for i in range(3))
  self.assertLess(signed_volume,0,'viewer culls positive projected winding')
