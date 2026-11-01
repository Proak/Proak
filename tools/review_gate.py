"""Judge a completed QA record conservatively. Never interpret absence of tests as PASS."""
import json,sys
from pathlib import Path
if len(sys.argv)!=2: raise SystemExit('Usage: python tools/review_gate.py path/to/review.json')
p=Path(sys.argv[1]); d=json.loads(p.read_text(encoding='utf-8'))
fail=[]; blockers=[]
for k in ('task_id','commit','reviewer','author','gate','status','test_results'):
 if not d.get(k): fail.append('missing:'+k)
if d.get('author')==d.get('reviewer'): fail.append('same agent wrote/reviewed')
if d.get('p0_issues'): fail.append('P0 unresolved')
if d.get('status')!='PASS': blockers.append('status is not PASS')
tests=d.get('test_results',[])
if not tests or not all(t.get('status')=='PASS' and t.get('evidence') for t in tests): blockers.append('test failure, blocked, not run or missing evidence')
sc=d.get('scores',{})
if sc:
 if any(not isinstance(v,(int,float)) or v<0 or v>4 for v in sc.values()): blockers.append('unrated scores')
 elif sum(sc.values())<18 or min(sc.values())<2: blockers.append('quality threshold not met')
if not d.get('evidence_files'): blockers.append('no evidence media')
# Static path existence is an additional necessary condition, never sufficient proof of an actual gameplay test.
def actual_evidence_path(s):
 path=Path(s)
 if path.is_absolute(): return path
 root=Path(__file__).resolve().parents[1]
 project_path=root/path
 return project_path if project_path.is_file() else p.parent/path
for path_str in d.get('evidence_files', []):
 evidence=actual_evidence_path(path_str)
 if not evidence.is_file() or evidence.stat().st_size==0:
  blockers.append('evidence media missing/empty: '+path_str)
for result in tests:
 if result.get('status')=='PASS':
  e=actual_evidence_path(result.get('evidence',''))
  if not e.is_file() or e.stat().st_size==0: blockers.append('test evidence missing/empty: '+str(result.get('evidence')))
print(json.dumps({'gate':'PASS' if not fail and not blockers else 'BLOCKED','hard_errors':fail,'blockers':blockers},ensure_ascii=False,indent=2))
if fail or blockers:sys.exit(1)
