"""Blender 5.2 LTS first lighting/camera/art-direction pass.
Invocation after installing Blender:
blender -b -t 4 --python blender/scene01_art_pass.py
This imports an ORIGINAL blockout GLB and saves a .blend, renders 3 camera stills.
No render is claimed until this script actually runs on a machine with Blender.
"""
import bpy, math, json
from pathlib import Path
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT/'production/blockout/scene_01_entrance_BLOCKOUT.glb'
OUT = ROOT/'production/claude_art/scene01'
OUT.mkdir(parents=True, exist_ok=True)
assert SRC.exists(), SRC
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1.0
bpy.ops.import_scene.gltf(filepath=str(SRC))
# Move all imported geometry into an isolated collection.
col=bpy.data.collections.new('SCENE_01_BLOCKOUT_SOURCE')
bpy.context.scene.collection.children.link(col)
for obj in list(bpy.context.scene.objects):
    if obj.type == 'MESH':
        for c in list(obj.users_collection): c.objects.unlink(obj)
        col.objects.link(obj)
# Light rig based on plausible aperture directions, not random ambient lights.
def area(name, pos, target, power, size, color):
    ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.shape='DISK';ld.size=size;ld.color=color
    obj=bpy.data.objects.new(name,ld);bpy.context.scene.collection.objects.link(obj)
    obj.location=pos;direction=Vector(target)-obj.location;obj.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
    return obj
area('LIGHT_Morning_Windows', (-5.0,2.7,4.8), (0.9,0.1,.6), 1600, 5.4, (1.0,.75,.50))
area('LIGHT_Counter_Fill',(-3,-1.0,3.3),(-3.4,0,1.0),210,2.1,(.66,.78,1.0))
area('LIGHT_Exit_Cold',(0,8.5,3.4),(0,3.5,1.2),170,1.8,(.45,.65,1.0))
world=bpy.data.worlds.new('WORLD_Late_Dawn')
bpy.context.scene.world=world;world.use_nodes=True
bg=world.node_tree.nodes.get('Background')
bg.inputs['Color'].default_value=(.08,.10,.115,1)
bg.inputs['Strength'].default_value=.14

def camera(name, pos, look):
    dat=bpy.data.cameras.new(name);dat.lens=28
    obj=bpy.data.objects.new(name,dat);bpy.context.scene.collection.objects.link(obj)
    obj.location=pos
    obj.rotation_euler=(Vector(look)-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj
cams={
  'entrance':camera('CAM_Entrance',(0,-7.1,1.65),(0,6.4,1.68)),
  'counter':camera('CAM_Counter',(-1.3,-2.2,1.65),(-4.0,-.2,1.05)),
  'return':camera('CAM_Return',(1.4,5.5,1.65),(5.5,1.0,1.85)),
}
sc=bpy.context.scene
sc.render.engine='BLENDER_EEVEE_NEXT'
sc.render.resolution_x=1280;sc.render.resolution_y=720;sc.render.resolution_percentage=75
sc.render.image_settings.file_format='PNG'
sc.view_settings.view_transform='AgX'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'scene01_entrance_artpass.blend'))
results=[]
for label,cam in cams.items():
    sc.camera=cam;file=str(OUT/f'scene01_{label}_actual_blender_render.png')
    sc.render.filepath=file
    bpy.ops.render.render(write_still=True)
    results.append(file)
assert all(Path(p).exists() for p in results)
(OUT/'scene01_render_qa.json').write_text(json.dumps({'blender_render_tested':True,'renders':results,'source':str(SRC),'note':'Blockout beauty lighting pass, not final cinematic art'},indent=2))
print('RENDER_DONE',results)
