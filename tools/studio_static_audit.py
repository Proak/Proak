"""Static, deterministic project audit. No claims of 3D runtime or visual quality."""
import json, re, csv, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def add(name,ok,why=''):
 checks.append({'name':name,'status':'PASS' if ok else 'FAIL','detail':why})

core=['CLAUDE.md','docs/STUDIO_BLUEPRINT_v03.md','docs/SCENE_OUTLINE_24_BEATS.md','docs/PRODUCTION_RUNBOOK.md','docs/QUALITY_GATES_AND_DEAI.md','docs/PROMPTS/MASTER_ORCHESTRATOR.md','docs/UE_BLENDER_MCP_SETUP.md','production/asset_ledger.csv']
for name in core: add('exists:'+name,(ROOT/name).is_file())
plan=json.loads((ROOT/'production/scene_plan.json').read_text(encoding='utf-8'))
beats=plan['segments']; add('24 scene beats',len(beats)==24,str(len(beats)))
ids=[b.get('id') for b in beats]
add('unique scene IDs',len(ids)==len(set(ids)))
for act in ['0','I','II','III','IV','V']:
 add('four beats act '+act,sum(x.get('act')==act for x in beats)==4)
required=['name','objective','player_verb','foreshadow','reveal_or_feedback','exit_condition','threat','optional_reward']
for b in beats:
 for field in required: add(b['id']+':'+field, bool(str(b.get(field,'')).strip()))
 add(b['id']+':nonfiction QA status',b.get('qa_status') in ['PASS','FAIL','NOT_RUN','BLOCKED'])
 if b.get('qa_status')=='PASS': add(b['id']+':PASS evidence', bool(b.get('evidence')), 'PASS without evidence forbidden')
roles=list((ROOT/'.claude/agents').glob('*.md')); add('at least 11 independent agents',len(roles)>=11,str(len(roles)))
with (ROOT/'production/asset_ledger.csv').open(encoding='utf-8',newline='') as f:
 ledger=list(csv.DictReader(f))
for item in ledger:
 add('asset-rights-field:'+item['asset_id'],bool(item['licence'] and item['source_kind'] and item['rights_verified']))
 if item['game_shipped'].strip().upper()=='YES':
  add('shipped-rights-checked:'+item['asset_id'],item['rights_verified'].strip().upper()=='YES')
for p in (ROOT/'docs/PROMPTS').glob('*.md'):
 add('nonempty prompt:'+p.name,p.stat().st_size>150)
add('no UE sample mislabeled as packaged',not any((ROOT/'unreal').glob('*.exe')) if (ROOT/'unreal').exists() else True)
fail=[x for x in checks if x['status']=='FAIL']
report={'kind':'STATIC_ONLY','overall':'PASS' if not fail else 'FAIL','unreal_runtime':'BLOCKED','blender_runtime':'BLOCKED','player_testing':'NOT_RUN','checks':checks,'summary':{'pass':len(checks)-len(fail),'fail':len(fail)},'warnings':['Static PASS does not mean any playable Unreal build, Blender mesh render, game-feel, or lighting quality was verified.']}
out=ROOT/'production/qa/studio_static_report.json';out.parent.mkdir(exist_ok=True,parents=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'overall':report['overall'],**report['summary'],'report':str(out)},ensure_ascii=False))
if fail: sys.exit(1)
