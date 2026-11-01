"""Generate original architectural assets for The Unfinished Confession.
Usage (Blender executable required):
  blender -b -P blender/scene_generator.py -- --scene 01 --output game/assets/models/scene_01.glb --preview docs/scene_01_preview.png
Never run with a reference image as a direct texture: these are original mesh constructions.
"""
import argparse, json, math, os, sys
from pathlib import Path

try:
    import bpy
    from mathutils import Vector
except ImportError:
    bpy = None


def parse_args():
    a = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument('--scene', default='01', choices=['01', '02', '03', '04', '05'])
    p.add_argument('--output', default='game/assets/models/scene_01.glb')
    p.add_argument('--blend', default='')
    p.add_argument('--preview', default='')
    return p.parse_args(a)


def material(name, rgba, roughness=.82, metallic=.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgba,1.0)
    mat.use_nodes = True
    bsdf=mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(*rgba,1.0)
    bsdf.inputs['Roughness'].default_value=roughness
    bsdf.inputs['Metallic'].default_value=metallic
    return mat


def cube(name, location, scale, mat, bevel=.02):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj=bpy.context.object;obj.name=name;obj.dimensions=scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod=obj.modifiers.new('Micro-bevel for highlights','BEVEL')
        mod.width=bevel; mod.segments=2
        if hasattr(mod,'affect'): mod.affect='EDGES'
        bpy.context.view_layer.objects.active=obj
        try: bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception: pass
    for poly in obj.data.polygons: poly.use_smooth=False
    return obj


def set_camera(location,target):
    bpy.ops.object.camera_add(location=location)
    cam=bpy.context.object;cam.name='PREVIEW_CAMERA'
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=24
    bpy.context.scene.camera=cam


def light(name, position, color, energy, size):
    bpy.ops.object.light_add(type='AREA', location=position)
    ob=bpy.context.object;ob.name=name;ob.data.energy=energy;ob.data.shape='RECTANGLE'
    ob.data.size=size;ob.data.size_y=size*.35;ob.data.color=color
    ob.rotation_euler=(Vector((0,1.2,0))-ob.location).to_track_quat('-Z','Y').to_euler()


def generate(scene_code):
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    S=bpy.context.scene; S.unit_settings.system='METRIC'
    concrete=material('chalk concrete',(.34,.36,.37))
    stone=material('graphite floor',(.09,.11,.12))
    brass=material('oxidised bronze',(.52,.39,.27),.58,.58)
    paper=material('old paper',(.59,.53,.43))
    mirror=material('black mirror without reflection',(.018,.022,.025),.16)
    cube('walkable floor',(0,0,0),(7,.28,21),stone)
    cube('left architectural volume',(-3.6,2.6,0),(.35,5.2,21),concrete)
    cube('right architectural volume',(3.6,2.6,0),(.35,5.2,21),concrete)
    cube('ceiling volume',(0,5.0,0),(7,.3,21),concrete)
    if scene_code=='01':
        for i in range(9):
            z=-9+i*2.0
            cube('aperture_%02d'%i,(-3.35,2.9,z),(.10,2.4,.15),brass,.01)
            cube('diagonal ray sign_%02d'%i,(-2.8,.16,z+.4),(1.0,.01,.045),paper,.0)
        cube('portrait base',(0,.65,2),(1.9,1.3,.9),stone)
        for x in [-.70,.70]: cube('frame vertical', (x,1.82,2.0),(.07,1.3,.10),brass)
        for y in [1.2,2.45]: cube('frame horizontal',(0,y,2.0),(1.47,.07,.10),brass)
    elif scene_code=='02':
        for side in [-1,1]:
            for i in range(12):
                z=-9.2+i*1.6
                cube('rack pillar',(side*2.8,2.3,z),(.13,3.5,.12),brass)
                for lev in range(4):
                    cube('stacked archive', (side*3.02,.8+lev*.77,z+.25),(.5,.22,.42),paper)
        cube('breath register',(0,.8,2.0),(1.7,1.6,1.1),stone)
    elif scene_code=='03':
        for i in range(7):
            scale=1.0-(i*.09)
            z=-6.8+i*2.1
            for x in [-2*scale,2*scale]: cube('frame-x',(x,2.4,z),(.12,3.8*scale,.12),brass)
            cube('frame-y',(0,2.4+1.9*scale,z),(4.0*scale,.12,.12),brass)
        cube('black rectangle',(0,2.2,5.5),(2.2,3.3,.02),mirror)
    elif scene_code=='04':
        for i in range(18):
            z=-9.4+i*1.03
            for side in [-1,1]:
                cube('unindexed cabinet', (side*3.0,2.0,z),(.7,3.2,.85),stone)
                for lev in range(3): cube('label-less drawer', (side*2.6,1.+lev*.85,z),(.09,.62,.72),brass)
    else:
        cube('undecidable threshold',(0,2,6),(4.5,3.7,.08),mirror)
        for i in range(5):
            cube('subtle ceiling marker',(0,4.7,-8+i*3.5),(4.5,.04,.045),brass)
    light('diffuse light from beyond frame',(1.6,4,-5.5),(1.0,.82,.63),850,7)
    light('cold fill',(-1.7,3.4,4.0),(.40,.55,1.0),300,4)
    set_camera((0,1.64,-9),(0,1.9,3.5))
    S.render.engine='CYCLES'
    S.cycles.samples=24
    S.render.resolution_x=960;S.render.resolution_y=540;S.render.resolution_percentage=100
    S.world.color=(.04,.045,.05)
    return {'scene':scene_code,'objects':len(bpy.data.objects),'meshes':len([x for x in bpy.data.objects if x.type=='MESH'])}


def self_check(report, target):
    problems=[]
    for obj in bpy.data.objects:
        if obj.type !='MESH': continue
        if any(d<0.001 for d in obj.dimensions): problems.append(obj.name+': very thin/zero size')
        if max(obj.dimensions)>100: problems.append(obj.name+': scale > 100m')
        if not obj.data.materials: problems.append(obj.name+': missing material')
    report['warnings']=problems
    Path(target).parent.mkdir(parents=True,exist_ok=True)
    Path(target).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


def main():
    if bpy is None: raise RuntimeError('Requires Blender embedded Python; do not run using normal Python.')
    a=parse_args()
    summary=generate(a.scene)
    out=Path(a.output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    if a.preview:
        bpy.context.scene.render.filepath=str(Path(a.preview).resolve())
        Path(a.preview).resolve().parent.mkdir(parents=True,exist_ok=True)
        bpy.ops.render.render(write_still=True)
    if a.blend:
        Path(a.blend).resolve().parent.mkdir(parents=True,exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.blend).resolve()))
    bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=False)
    summary['glb']=str(out)
    summary['rendered_preview']=bool(a.preview)
    self_check(summary,str(out.with_suffix('.qa.json')))
    print('FINISHED:',json.dumps(summary))

if __name__=='__main__':main()
