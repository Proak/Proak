"""Static asset and content QA. This is not a substitute for Godot/Blender runtime testing."""
import json, re, wave
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
GAME=ROOT/'game'
errors=[]
checks=[]
def check(name, cond, detail=''):
    checks.append({'name':name,'status':'PASS' if cond else 'FAIL','detail':detail})
    if not cond: errors.append(name+': '+detail)

for file in ['game/project.godot','game/scenes/main.tscn','game/scripts/main.gd','game/scripts/player.gd','docs/GDD_游戏设计.md','docs/CLAUDE_START_HERE.md','blender/scene_generator.py']:
    check('Exists '+file,(ROOT/file).is_file())
gd=(GAME/'scripts/main.gd').read_text(encoding='utf-8')
paths=sorted(set(re.findall('res://([A-Za-z_./0-9]+)',gd)))
for p in paths:check('Referenced resource '+p,(GAME/p).exists())
check('Five station dialogue arrays','"没有最终一页"' in gd and 'current_stage' in gd)
check('Mirror mechanic implemented','MOUSE_BUTTON_RIGHT' in gd)
check('Progression gates implemented','queue_free()' in gd and 'gates' in gd)
for p in (GAME/'assets/textures').glob('*.png'):
    with Image.open(p) as im: check('Texture '+p.name,im.size==(512,512),str(im.size))
for p in (GAME/'assets/audio').glob('*.wav'):
    with wave.open(str(p)) as sound:
        check('Audio '+p.name,sound.getnframes()>1000 and sound.getframerate()==22050,str(sound.getnframes()))
check('No third-party reference images packaged',len(list((ROOT/'reference').glob('*.jpg'))+list((ROOT/'reference').glob('*.png')))==0)
report={'status':'STATIC PASS — NOT RUNTIME TESTED' if not errors else 'STATIC FAIL', 'pass':sum(c['status']=='PASS' for c in checks),'failed':len(errors),'checks':checks,'errors':errors,'runtime_tested':False,'blender_render_tested':False}
(ROOT/'qa_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'pass':report['pass'],'failed':report['failed']},ensure_ascii=False))
if errors: raise SystemExit(1)
