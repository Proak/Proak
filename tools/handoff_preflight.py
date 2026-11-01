"""Handoff consistency only. DOES NOT run any game engine or certify gameplay."""
import json,re,sys,os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
issues=[];passes=[]
def check(condition,description): (passes if condition else issues).append(description)
required=['CLAUDE.md','00_READ_ME_FIRST.md','01_CLAUDE_HANDOFF_PROMPT.txt','CLAUDE_APP_SINGLE_FILE.txt','docs/AUDIT_REPORT_v04.md','production/vertical_slice_plan.json','ue58/Confession.uproject','tools/studio_static_audit.py']
for f in required:check((root/f).is_file(),'required '+f)
plan=json.loads((root/'production/scene_plan.json').read_text(encoding='utf-8'))
vs=json.loads((root/'production/vertical_slice_plan.json').read_text(encoding='utf-8'))
ids={item['id'] for item in plan['segments']}
check(len(ids)==24,'canonical 24 beat IDs')
check(len(vs['parts'])==6,'six vertical-slice parts')
check(all(part['source'] in ids for part in vs['parts']),'slice sources map onto canonical beats')
check(sum(part['target_minutes'] for part in vs['parts']) in range(14,18),'slice target minutes 14-17')
check((root/'production/scene_specs/scene_01_entrance.yaml').read_text().startswith('id: L0_B01'),'scene spec canonical ID')
check((root/'ue58/Source/Confession/Private/ConfessionCharacter.cpp').is_file(),'UE C++ source exists')
for f in [root/'.claude/agents/gameplay-engineer.md',root/'docs/PROMPTS/MASTER_ORCHESTRATOR.md',root/'docs/STUDIO_BLUEPRINT_v03.md']:
 txt=f.read_text(encoding='utf-8')
 check('`unreal/Source' not in txt,'no nonexistent Unreal path in '+str(f.relative_to(root)))
check(all(p.get('qa_status')!='PASS' for p in plan['segments']),'no unverified beat PASS flags')
print(json.dumps({'kind':'STATIC_HANDOFF_ONLY','result':'PASS' if not issues else 'FAIL','checks_passed':len(passes),'issues':issues,'engines_tested':False,'real_player_tested':False},ensure_ascii=False,indent=2))
if issues:sys.exit(1)
