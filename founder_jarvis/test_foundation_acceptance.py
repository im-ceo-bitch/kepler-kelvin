import hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from founder_jarvis.macos.foundation_acceptance import configure_reserve,receipts,live_probe
class FoundationAcceptance(unittest.TestCase):
    def test_preserve_private_config_and_backup(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'runtime.env';path.write_text('PRIVATE=keep\nKELVIN_PROVIDER=codex\nKELVIN_LOCAL_ON_CLAUDE_LIMIT=0\n')
            self.assertTrue(configure_reserve(path));self.assertIn('PRIVATE=keep',path.read_text());self.assertIn('KELVIN_PROVIDER=claude',path.read_text());self.assertNotIn('codex',path.read_text());self.assertFalse(configure_reserve(path));self.assertEqual(len(list(Path(d).glob('*.bak'))),1);self.assertEqual(path.stat().st_mode&0o777,0o600)
    def test_receipt_exact_id(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'runtime.log';ident='foundation-probe-'+'a'*24;p.write_text('Foundation receipt '+ident+'-1 done '+'b'*64+'\nFoundation receipt other-1 done '+'c'*64)
            self.assertEqual(receipts(p,ident),{ident+'-1':{'status':'done','sha256':'b'*64}})
    def test_busy_queue_blocks_probe(self):
        class Bridge:
            def call(self,*args):return {'protocol':7,'queue':{'running':1}}
            def enqueue(self,*args):raise AssertionError('Must not enqueue')
        with self.assertRaisesRegex(RuntimeError,'busy'):live_probe(Bridge(),Path('.'))
    def test_probe_checks_ack_and_context(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'runtime.log';word='сапфир';hash_=hashlib.sha256(word.encode()).hexdigest()
            class Bridge:
                def call(self,*args):return {'protocol':7,'queue':{}}
                def enqueue(self,key,*args):
                    with p.open('a') as f:f.write(f'Foundation receipt {key} done {hash_}\n')
            with patch('secrets.choice',return_value=word):result=live_probe(Bridge(),p)
            self.assertTrue(result['passed']);self.assertEqual(len(result['turns']),2)
