"""Original parameterized anatomy, not a clinical atlas or tissue simulation."""
import math

# x/y/z centers and radii; +z is anterior. Paired parts share evidence identity.
PARTS = [
 ('brain',(-10,-215,0),(20,27,22)),('brain',(10,-215,0),(20,27,22)),
 ('lungs',(-28,-105,0),(22,48,23)),('lungs',(28,-105,0),(22,48,23)),
 ('heart',(5,-92,24),(18,28,18)),('liver',(-13,-38,9),(43,22,23)),
 ('stomach',(24,-12,13),(19,29,17)),
 ('kidneys',(-29,9,-19),(12,20,11)),('kidneys',(29,9,-19),(12,20,11)),
 ('bladder',(0,72,12),(17,19,14)),('uterus',(0,88,0),(15,19,9)),
 ('uterus',(-17,76,0),(12,4,4)),('uterus',(17,76,0),(12,4,4)),
 ('testes',(-8,112,7),(7,12,7)),('testes',(8,112,7),(7,12,7)),
 ('biceps',(-64,-87,16),(11,35,12)),('biceps',(64,-87,16),(11,35,12)),
 ('triceps',(-65,-87,-15),(13,38,12)),('triceps',(65,-87,-15),(13,38,12)),
 ('quadriceps',(-25,137,13),(16,56,13)),('quadriceps',(25,137,13),(16,56,13)),
 ('quadriceps',(-37,134,6),(9,48,10)),('quadriceps',(37,134,6),(9,48,10)),
]
SHELL = [((0,-214,0),(33,42,28)),((0,-162,0),(14,23,15)),
 ((0,-95,0),(57,66,32)),((0,-10,0),(45,47,27)),((0,62,0),(48,38,29)),
 ((-65,-94,0),(18,53,19)),((65,-94,0),(18,53,19)),
 ((-81,-16,0),(13,45,14)),((81,-16,0),(13,45,14)),
 ((-88,36,0),(11,20,8)),((88,36,0),(11,20,8)),
 ((-27,135,0),(24,61,25)),((27,135,0),(24,61,25)),
 ((-28,222,-2),(16,48,16)),((28,222,-2),(16,48,16)),
 ((-28,270,10),(16,10,28)),((28,270,10),(16,10,28))]

def rotate(point,yaw,pitch):
    x,y,z=point; c,s=math.cos(yaw),math.sin(yaw)
    x,z=x*c+z*s,-x*s+z*c; c,s=math.cos(pitch),math.sin(pitch)
    return x,y*c-z*s,y*s+z*c

def clamp_zoom(value): return max(.65,min(2.4,value))

def mesh(center,radii,kind='',rows=12,cols=20):
    vertices=[]
    for i in range(rows+1):
        lat=-math.pi/2+math.pi*i/rows
        for j in range(cols):
            lon=2*math.pi*j/cols
            x,y,z=math.cos(lat)*math.cos(lon),math.sin(lat),math.cos(lat)*math.sin(lon)
            if kind=='brain':
                fold=1+.06*math.sin(9*lon+3*lat)*math.cos(12*lat)
                x*=fold;z*=fold
            if kind=='kidneys': x*=1-.35*max(0,math.cos(lon))*(1-y*y)
            if kind=='heart': x*=.8-.25*y;z*=.9-.15*y
            if kind=='lungs': x*=.85+.18*y
            if kind=='liver': y+=.16*x
            vertices.append(tuple(center[k]+v*radii[k] for k,v in enumerate((x,y,z))))
    faces=[]
    for i in range(rows):
        for j in range(cols):
            faces.append((i*cols+j,i*cols+(j+1)%cols,(i+1)*cols+(j+1)%cols,(i+1)*cols+j))
    return vertices,faces
