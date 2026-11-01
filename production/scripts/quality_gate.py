"""Offline quality gate: truthfully distinguishes static checks from engine tests."""
from pathlib import Path
import json,ast,subprocess,sys
import trimesh
import yaml
ROOT=Path(__file__).resolve().parents[2]
checks=[]
def add(name,ok,details=''):
 checks.append({'check':name,'state':'PASS' if ok else 'FAIL','details':details})
 return ok
spec=yaml.safe_load((ROOT/'production/scene_specs/scene_01_entrance.yaml').read_text())
gdd=(ROOT/'docs/GDD_v02_DIRECTORS_CUT.md').read_text()
add('GDD theme and game pillars',all(x in gdd for x in ('追逐','谜题','安全区','原创')))
add('Six-act level progression', all(x in gdd for x in ('拂晓登记处','正午复核层','坐标档案馆','最后一张回执')))
add('Stage YAML physical clearance',spec['human_scale']['hall_clearance_cm']>=130)
add('Source and licensing policy',(ROOT/'production/reference/scene_01_sources.json').exists())
add('Blender authored script compiles',bool(ast.parse((ROOT/'blender/scene01_art_pass.py').read_text())))
for f in (ROOT/'production/scripts').glob('*.py'):
 try:ast.parse(f.read_text());add('Python syntax '+f.name,True)
 except SyntaxError as e:add('Python syntax '+f.name,False,str(e))
for f in ('ue58/Confession.uproject','production/reference/scene_01_sources.json'):
 try:json.loads((ROOT/f).read_text());add('Valid JSON '+f,True)
 except Exception as e:add('Valid JSON '+f,False,str(e))
meshfile=ROOT/'production/blockout/scene_01_entrance_BLOCKOUT.glb'
try:
 scene=trimesh.load(meshfile,force='scene')
 add('Real glB opens in trimesh',bool(scene.geometry))
 tri=sum(len(m.faces) for m in scene.geometry.values())
 add('Triangle budget for prototype',tri<10000,'faces: '+str(tri))
 add('Geometry all watertight proxies',all(m.is_watertight for m in scene.geometry.values()))
except Exception as e:add('Real glB opens in trimesh',False,str(e))
old=ROOT/'tools/audit_project.py'
run=subprocess.run([sys.executable,str(old)],capture_output=True,text=True)
add('Godot resource/static asset preflight',run.returncode==0,run.stdout.strip()+' '+run.stderr.strip())
gd=(ROOT/'game/scripts/main.gd').read_text()
for tag in ('_turn_valve','_collect_evidence','_begin_chase','_advance_chase'):
 add('Gameplay code contains '+tag,tag in gd)
add('Audio originates in project',len(list((ROOT/'game/assets/audio').glob('*.wav')))==5)
blocking=[x for x in checks if x['state']=='FAIL']
report={
 'build':'2026-11-01/v0.2','static_status':'FAIL' if blocking else 'PASS',
 'static_pass':len(checks)-len(blocking),'static_fail':len(blocking),
 'unreal_compiled':False,'unreal_run_tested':False,'blender_rendered':False,'godot_runtime_tested':False,
 'gameplay_playtested':False,'flags':'These are UNTESTED; no claim of playable FPS or final visuals.',
 'checks':checks,'blocking':blocking
}
(ROOT/'production/qa/STATIC_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'static_status':report['static_status'],'pass':report['static_pass'],'fail':report['static_fail']},ensure_ascii=False))
if blocking:sys.exit(1)
