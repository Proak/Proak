"""Run with python -m unittest discover -s tests."""
import unittest,sys,json,tempfile,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class GateTest(unittest.TestCase):
 def run_gate(self,data):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'test.json'
   (Path(d)/'test.mp4').write_bytes(b'UNIT_TEST_DUMMY_EVIDENCE_NOT_A_REAL_VIDEO')
   for t in data.get('test_results',[]): t['evidence']='test.mp4'
   data['evidence_files']=['test.mp4']
   path.write_text(json.dumps(data),encoding='utf-8')
   return subprocess.run([sys.executable,str(ROOT/'tools/review_gate.py'),str(path)],capture_output=True,text=True)
 def review(self):
  return {'task_id':'T','commit':'deadbeef','author':'writer','reviewer':'independent','gate':'G3','status':'PASS','p0_issues':[], 'test_results':[{'name':'PIE','status':'PASS','evidence':'production/qa/test.mp4'}], 'evidence_files':['production/qa/test.mp4'],'scores':{'clarity':3,'mechanics':3,'pacing':3,'visual':3,'narrative':3,'reliability':3}}
 def test_pass_record(self): self.assertEqual(self.run_gate(self.review()).returncode,0)
 def test_self_review_fails(self):
  r=self.review(); r['reviewer']=r['author'];self.assertNotEqual(self.run_gate(r).returncode,0)
 def test_not_run_fails(self):
  r=self.review();r['test_results'][0]['status']='NOT_RUN';self.assertNotEqual(self.run_gate(r).returncode,0)
 def test_p0_fails(self):
  r=self.review();r['p0_issues']=['softlock'];self.assertNotEqual(self.run_gate(r).returncode,0)
if __name__=='__main__':unittest.main()
