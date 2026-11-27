import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as N
from founder_jarvis.runtime import Store, authorized, agent_command, config_file, chunks
import tomllib

class Tests(unittest.TestCase):
    def test_queue_approval_and_dedupe(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)/'jobs.db'); i,new=s.add(42,'modify','edit',False,1)
            self.assertTrue(new); self.assertIsNone(s.next()); self.assertEqual(s.add(42,'modify','edit',False,1),(i,False))
            self.assertFalse(s.transition(i,99,'pending','queued')); self.assertTrue(s.transition(i,42,'pending','queued'))
            self.assertEqual(s.next()['id'],i); s.finish(i,'done','ok'); self.assertEqual(s.history(42)[0]['assistant'],'ok')
    def test_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'jobs.db'; s=Store(p); s.add(1,'a','chat',True,1); s.next(); s.db.close(); s=Store(p)
            self.assertEqual(s.recent(1)[0]['state'],'interrupted'); self.assertIsNone(s.next())
    def test_auth(self):
        self.assertTrue(authorized(N(effective_chat=N(type='private',id=42),effective_user=N(id=42)),42))
        self.assertFalse(authorized(N(effective_chat=N(type='group',id=42),effective_user=N(id=42)),42))
        self.assertFalse(authorized(N(effective_chat=N(type='private',id=43),effective_user=N(id=43)),42))
    def test_scope(self):
        c=agent_command('ollama','m','chat','--evil',[]); self.assertNotIn('file_write',c[c.index('--tools')+1]); self.assertIn('file_write',agent_command('ollama','m','edit','x',[])[c.index('--tools')+1]); self.assertIn('--',c)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.toml'; config_file(p,Path(d)); cfg=tomllib.loads(p.read_text()); self.assertFalse(cfg['skills']['enabled']); self.assertEqual(cfg['security']['allowed_dirs'],[d]); self.assertFalse(cfg['tools']['mcp']['enabled'])
    def test_chunks(self):
        text='😀'*5000; self.assertEqual(''.join(chunks(text)),text); self.assertTrue(all(len(p.encode('utf-16-le'))//2<=4096 for p in chunks(text)))

if __name__=='__main__': unittest.main()
