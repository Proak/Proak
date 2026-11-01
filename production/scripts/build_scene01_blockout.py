"""Generate ORIGINAL geometry for L00 Entrance using trimesh, without Blender or Unreal.
This is a structural BLOCKOUT, NOT final-quality modeling, textures or lighting.
Unit: metres; Z up; +Y towards the basement door. Exports glTF GLB.
"""
from pathlib import Path
import json
import numpy as np
import trimesh
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'production'/'blockout'; OUT.mkdir(parents=True,exist_ok=True)
scene=trimesh.Scene()
objects=[]
COLORS={
 'concrete':[121,126,130,255], 'floor':[80,90,96,255], 'iron':[58,67,70,255],
 'paper':[193,174,139,255], 'brass':[145,108,73,255], 'dark':[31,36,38,255],
 'light':[219,202,159,255], 'glass':[122,147,152,180], 'rust':[111,72,62,255]
}
def add(n,center,size,mat='concrete'):
    mesh=trimesh.creation.box(extents=size)
    mesh.apply_translation(center)
    mesh.visual.face_colors=np.array(COLORS[mat],dtype=np.uint8)
    scene.add_geometry(mesh, geom_name=n, node_name=n)
    objects.append(dict(id=n,center=center,size=size,material=mat,triangles=len(mesh.faces)))
# Shell 13m x 19m x 4.2m
add('SM_Floor_00',(0,0,-.11),(13,19,.22),'floor')
add('SM_Ceiling_00',(0,0,4.30),(13,19,.22))
add('SM_Wall_Left',(-6.52,2.0,2.1),(.24,15.0,4.2))
add('SM_Wall_Left_Entry',(-6.52,-7.5,2.1),(.24,4,4.2))
add('SM_Wall_Right',(6.52,0,2.1),(.24,19,4.2))
# Front entrance aperture and rear basement door opening
for s in (-1,1):
    add(f'SM_Wall_Entrance_Side_{s}',(s*4.05,-9.5,2.1),(4.95,.25,4.2))
add('SM_Wall_Entrance_Header',(0,-9.5,3.75),(3.1,.25,.9))
for s in (-1,1):
    add(f'SM_Wall_Rear_Side_{s}',(s*3.50,9.5,2.1),(6.1,.24,4.2))
add('SM_Wall_Rear_Header',(0,9.5,3.65),(1.08,.24,1.10))
add('SM_Basement_Door', (0,9.32,1.05),(1.15,.1,2.12),'iron')
add('SM_Basement_Door_Handle',(.43,9.13,1.06),(.12,.13,.03),'brass')
add('SM_Basement_Door_Plate',(.0,9.16,1.75),(.6,.025,.28),'brass')
# Front desk + enclosed office counter
add('SM_Counter_Base',(-3.45,-.35,.50),(4.25,1.05,1.0),'iron')
add('SM_Counter_Top',(-3.45,-.35,1.06),(4.5,1.20,.09),'brass')
add('SM_Counter_Window_Frame',(-3.5,.25,2.0),(4.45,.13,.11),'dark')
for s in (-1,1):
    add(f'SM_Counter_Window_Post_{s}',(-3.5+s*2.18,.25,2.45),(.10,.12,2.9),'dark')
add('SM_Counter_Slot',(-3.4,-.955,1.25),(.65,.11,.1),'paper')
add('SM_CardSlot_01',(-4.35,-.955,1.35),(.45,.1,.29),'brass')
# Archive shelving in alcove to right; walkable aisle maintained
for j in range(5):
    y = -5.5+j*2.2
    add(f'SM_ShelfRight_Back_{j}',(5.85,y,1.85),(.10,1.82,3.45),'dark')
    for h in (0.55,1.15,1.8,2.45,3.15):
        add(f'SM_ShelfRight_{j}_{int(h*100)}',(5.45,y,h),(.84,1.82,.07),'iron')
    for k in range(4):
        add(f'SM_FileBox_{j}_{k}',(5.42,y-.65+k*.42,1.43),(.35,.29,.42),'paper')
# Floor tile joints, pillars, wiring and high window slats
for j,y in enumerate(range(-8,9,2)):
    add(f'SM_Floor_Seam_{j}',(0,y,.008),(12.7,.02,.008),'dark')
for i in range(1,6):
    yy=-7.4+i*2.8
    add(f'SM_Left_Pillar_{i}',(-6.20,yy,2.06),(.53,.55,4.11),'concrete')
    add(f'SM_High_Window_Frame_{i}',(-6.06,yy,3.35),(.12,1.1,.9),'dark')
    add(f'SM_Window_Glass_{i}',(-6.015,yy,3.35),(.02,.9,.6),'glass')
for j in range(4):
    yy=-5.9+j*3.3
    add(f'SM_LampHousing_{j}',(-.8,yy,4.09),(1.2,.32,.14),'iron')
    add(f'SM_LampDiffuser_{j}',(-.8,yy,4.01),(1.05,.22,.025),'light')
# Post room props
add('SM_Desk_Clock',(-2.5,-.5,1.29),(.34,.23,.35),'dark')
add('SM_Wall_Clock',(1.5,9.18,3.2),(.62,.12,.62),'brass')
for i in range(3):
    add(f'SM_LetterTray_{i}',(-4.75,.04,1.22+i*.16),(.6,.55,.11),'iron')
add('SM_NoticePanel',(3.4,9.18,1.9),(1.55,.08,.9),'paper')
add('SM_EmptyFrame_Backing',(6.3,1.0,1.95),(.07,1.35,1.7),'dark')
for s in (-1,1):
    add(f'SM_EmptyFrame_H_{s}',(6.22,1.0,1.95+s*.83),(.13,1.4,.06),'brass')
    add(f'SM_EmptyFrame_V_{s}',(6.22,1.0+s*.69,1.95),(.13,.07,1.65),'brass')
# Pipe on ceiling and cabling to service door
for j in range(6):
    add(f'SM_CableTrunk_{j}',(2.2,-7.2+j*3.0,4.03),(.12,2.72,.12),'iron')
# Export (static geometric proxy)
blob=scene.export(file_type='glb')
(OUT/'scene_01_entrance_BLOCKOUT.glb').write_bytes(blob)
mins,maxs=scene.bounds
report={'scene':'L0_B01','blockout_only':True,'actual_ue_render':False,'actual_blender_render':False,
        'object_count':len(objects),'triangle_count':int(sum(o['triangles'] for o in objects)),
        'bounds_m':[mins.tolist(),maxs.tolist()],
        'check_nonfinite':all(np.isfinite(o['center']).all() and np.isfinite(o['size']).all() for o in objects),
        'check_positive_dimensions':all(min(o['size'])>0 for o in objects),
        'check_unique_names':len(set(o['id'] for o in objects))==len(objects),
        'geometry_note':'glb is real mesh data but blockout, not a cinematic screenshot or finished art'}
(OUT/'scene_01_geometry_qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(OUT/'scene_01_object_manifest.json').write_text(json.dumps(objects,ensure_ascii=False,indent=2))
# Original top-down layout schematic; intentionally labelled NOT GAMEPLAY
W,H=1300,900
im=Image.new('RGB',(W,H),(24,29,33));d=ImageDraw.Draw(im)
font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font=ImageFont.truetype(font_path,25);tiny=ImageFont.truetype(font_path,17)
L,T=330,130; scale=36
X=lambda x:round(L+(x+6.5)*scale)
Y=lambda y:round(T+(9.5-y)*scale)
# floor
d.rectangle((X(-6.5),Y(9.5),X(6.5),Y(-9.5)),outline=(160,177,174),width=5,fill=(51,58,64))
for s in objects:
    c,sz=s['center'],s['size']
    if c[2]>2.4 or s['id'].startswith(('SM_Floor','SM_Ceiling','SM_Wall','SM_Cable')):continue
    x,y,z=c;a,b,cz=sz
    a0,b0=X(x-a/2),Y(y+b/2);a1,b1=X(x+a/2),Y(y-b/2)
    col=(119,119,111) if s['material'] in ('iron','dark') else (157,127,86)
    if s['material']=='paper':col=(174,155,116)
    d.rectangle((a0,b0,a1,b1),fill=col,outline=(30,33,33),width=1)
d.rectangle((X(-.575),Y(9.50),X(.575),Y(9.15)),fill=(199,156,92))
d.line((X(0),Y(-8.9),X(0),Y(8.6)),fill=(108,190,162),width=3)
d.text((40,40),'L00  /  RECEIPT OFFICE  /  ORIGINAL BLOCKOUT',font=font,fill=(235,226,201))
d.text((40,83),'TOP-DOWN SCHEMATIC  -  NOT AN IN-ENGINE SCREENSHOT',font=tiny,fill=(184,192,195))
for txt,y in [('PLAYER START',735),('COUNTER / ACCESS CARD',770),('ARCHIVE SHELVES',805),('BASEMENT DOOR',840)]:d.text((40,y),txt,font=tiny,fill=(200,198,188))
for txt,coord in [('START',(X(-3.1),Y(-8.1))),('DOOR',(X(.5),Y(8.9))),('COUNTER',(X(-4.4),Y(-2.0))),('SHELVES',(X(4.9),Y(0.0)))]:d.text(coord,txt,font=tiny,fill=(236,216,168))
im.save(OUT/'scene_01_layout.png')
print(json.dumps({'created_glb_bytes':len(blob),**report},ensure_ascii=False))
