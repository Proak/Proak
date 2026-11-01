"""Heuristic, non-authoritative lint: flags repeated empty rhetoric. NOT an AI detector."""
import sys,re,json
from pathlib import Path
patterns={
 'abstract reversal':r'(?:不是.{0,20}而是|你以为.{0,20}其实|It was never .{0,40} but)',
 'generic cosmic nouns':r'(?:命运|永恒|虚无|真实|深渊|意识|真相)',
 'generic vague line':r'(?:这一切才刚刚开始|这里并不是终点|你终究会明白)',
}
if len(sys.argv)<2: raise SystemExit('Usage: python tools/text_redflag_lint.py file1.md [file2.md ...]')
results=[]
for f in sys.argv[1:]:
 p=Path(f);txt=p.read_text(encoding='utf-8');counts={k:len(re.findall(v,txt,flags=re.I)) for k,v in patterns.items()}
 results.append({'file':str(p),'flags':counts,'warning':'Flags are prompts for human review, never automatic deletion or proof of AI authorship'})
print(json.dumps(results,ensure_ascii=False,indent=2))
