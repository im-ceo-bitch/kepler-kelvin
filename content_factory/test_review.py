import hashlib
import tempfile
import unittest
from pathlib import Path
from content_factory.review import evaluate, WEIGHTS


class ReviewGate(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        asset=self.root/'fixture.mp4'
        asset.write_bytes(b'synthetic unit fixture')
        self.record={'format':'video','version':'v1','creator':'editor','reviewer':'director',
            'scores':{k:{'points':v,'observation':'fixture observation'} for k,v in WEIGHTS.items()},
            'examined':[{'path':asset.name,'sha256':hashlib.sha256(asset.read_bytes()).hexdigest(),
                         'location':'0:01'}], 'critical':[]}

    def test_threshold_and_critical_veto(self):
        score=self.record['scores']['strategy']
        for points, decision in [(5,'submit_to_founder'),(4,'revise')]:
            score['points']=points
            self.assertEqual(evaluate(self.record,self.root)['decision'],decision)
        score['points']=20
        self.record['critical']=['unverified offer']
        self.assertEqual(evaluate(self.record,self.root)['decision'],'revise')

    def test_version_and_independence(self):
        self.record['reviewer']=' Editor '
        with self.assertRaises(ValueError):
            evaluate(self.record,self.root)
        self.record['reviewer']='director'
        (self.root/'fixture.mp4').write_bytes(b'new version')
        with self.assertRaises(ValueError):
            evaluate(self.record,self.root)
