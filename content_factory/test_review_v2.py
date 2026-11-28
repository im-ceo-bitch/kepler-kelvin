import tempfile,unittest
from pathlib import Path
from content_factory.review_v2 import *

class GateV2(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def fixture(self,fmt='carousel'):
        names=['a.png','b.png'] if fmt=='carousel' else ['a.md']
        files=[]
        for name in names:
            p=self.root/name;p.write_text('fixture');files.append({'path':name,'sha256':digest(p)})
        m={'version':'1','format':fmt,'files':files}
        r={'manifest_sha256':manifest_digest(m),'scores':{k:{'points':v,'observation':'observed'} for k,v in RUBRICS[fmt].items()},'examined':[{'path':n,'location':'whole slide','observation':'observed'} for n in names],'critical':[],'rights_verified':True,'claims_verified':True,'language_verified':True}
        return m,r
    def test_no_auto_publish(self):
        m,r=self.fixture();out=evaluate_review(m,r,self.root,lambda *x:{})
        self.assertEqual(out['decision'],'independent_review_required');self.assertFalse(out['publication_authorized'])
    def test_missing_card(self):
        m,r=self.fixture();r['examined'].pop()
        with self.assertRaises(ValueError):evaluate_review(m,r,self.root,lambda *x:{})
    def test_changed_card(self):
        m,r=self.fixture();(self.root/'a.png').write_text('new')
        with self.assertRaises(ValueError):evaluate_review(m,r,self.root,lambda *x:{})
    def test_claims_block(self):
        m,r=self.fixture();r['claims_verified']=False
        self.assertEqual(evaluate_review(m,r,self.root,lambda *x:{})['decision'],'revise')
    def test_wrong_rubric(self):
        m,r=self.fixture();r['scores']={}
        with self.assertRaises(ValueError):evaluate_review(m,r,self.root,lambda *x:{})
    def test_real_script(self):
        m,r=self.fixture('talking_head_script');self.assertEqual(evaluate_review(m,r,self.root)['technical'],'pass')
    def test_critical(self):
        m,r=self.fixture();r['critical']=['rights missing'];self.assertEqual(evaluate_review(m,r,self.root,lambda *x:{})['decision'],'revise')
    def test_wrong_version(self):
        m,r=self.fixture();m['version']='2'
        with self.assertRaises(ValueError):evaluate_review(m,r,self.root,lambda *x:{})
