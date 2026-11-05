import unittest
from src.anatomy_mesh import rotate,clamp_zoom,mesh,PARTS
class MeshTests(unittest.TestCase):
 def test_rotation_preserves_length(self):
  for yaw,pitch in ((0,0),(1.5,.7),(3.14,-1.1)):
   q=rotate((10,20,30),yaw,pitch)
   self.assertAlmostEqual(sum(v*v for v in q),1400)
 def test_depth_changes_at_quarter_turn(self):
  import math
  q=rotate((10,0,0),math.pi/2,0)
  self.assertAlmostEqual(q[0],0);self.assertAlmostEqual(q[2],-10)
 def test_zoom_bounds(self):
  self.assertEqual(clamp_zoom(0),.65);self.assertEqual(clamp_zoom(9),2.4)
 def test_mesh_indices(self):
  import math
  for kind,c,r in PARTS:
   v,f=mesh(c,r,kind)
   self.assertTrue(all(math.isfinite(x) for p in v for x in p))
   self.assertTrue(all(0<=i<len(v) for face in f for i in face))
