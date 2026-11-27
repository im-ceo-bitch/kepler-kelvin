import tempfile, unittest, time, os, sqlite3, subprocess, json
from pathlib import Path
from unittest.mock import patch
from founder_jarvis.runtime import Store, execute_agent, Voice
from founder_jarvis import integrations as i

class V4Tests(unittest.TestCase):
    def test_migrate_persist(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'db'; db=sqlite3.connect(p)
            db.execute('CREATE TABLE jobs(id INTEGER PRIMARY KEY, chat INTEGER NOT NULL, prompt TEXT NOT NULL, mode TEXT NOT NULL, voice INTEGER NOT NULL, state TEXT NOT NULL, answer TEXT, message_id INTEGER, UNIQUE(chat,message_id))')
            db.execute("INSERT INTO jobs VALUES(1,42,'old','chat',0,'done','answer',1)"); db.commit(); db.close()
            s=Store(p); n=s.remember(42,'iumrah'); s.db.close(); s=Store(p)
            self.assertEqual(s.history(42)[0]['assistant'],'answer'); self.assertEqual(s.memories(42)[0]['text'],'iumrah'); self.assertFalse(s.forget(7,n)); self.assertTrue(s.forget(42,n)); s.db.close()
    def test_approval_due(self):
        with tempfile.TemporaryDirectory() as d:
            s=Store(Path(d)/'db'); a,_=s.add(1,'open safari','mac',False,1,True); b,_=s.add(1,'future','chat',False,2,due=time.time()+3600)
            self.assertIsNone(s.next()); self.assertTrue(s.transition(a,1,'pending','queued')); self.assertEqual(s.next()['id'],a); self.assertIsNone(s.next()); s.db.close()
    def test_parser(self):
        for mode,text in [('mac','open safari'),('gh','publish app'),('cf','deploy app'),('ig','reply 123 hi'),('ig','dm 123 hi'),('work','app fix'),('gh','commit app fix')]: self.assertTrue(i.parse(mode,text)[2])
        for mode,text in [('mac','status'),('gh','runs x/y'),('ig','media'),('cf','status app'),('research','test')]: self.assertFalse(i.parse(mode,text)[2])
        for mode,text in [('mac','open /tmp/x'),('mac','url file:///etc/passwd'),('gh','runs --evil'),('cf','deploy ../x'),('ig','reply ../a text'),('ig','messages ../token'),('work','../app fix')]:
            with self.assertRaises(RuntimeError): i.parse(mode,text)
    def test_secret_env(self):
        with patch.dict(os.environ,{'TELEGRAM_BOT_TOKEN':'xx','CLOUDFLARE_API_TOKEN':'yy','ANTHROPIC_API_KEY':'zz','IG_TOKEN':'tt'}):
            self.assertTrue(all(k not in i.clean_env() for k in ['TELEGRAM_BOT_TOKEN','CLOUDFLARE_API_TOKEN','ANTHROPIC_API_KEY','IG_TOKEN']))
    def test_real_process(self):
        import sys
        self.assertEqual(i.run([sys.executable,'-c','print(42)']),'42')
        with self.assertRaises(RuntimeError): i.run([sys.executable,'-c','raise SystemExit(7)'])
    def test_local_git_branch(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); subprocess.run(['git','init','-q',d],check=True); subprocess.run(['git','-C',d,'-c','user.name=Test','-c','user.email=test@example.invalid','commit','--allow-empty','-qm','initial'],check=True)
            def edit(path,prompt,readonly=False): (path/'test.txt').write_text(prompt); return 'edited'
            with patch.object(i,'project',return_value=p),patch.object(i,'claude_work',side_effect=edit):
                result=i.execute('work','app fix'); self.assertIn('kelvin/',result); self.assertEqual((p/'test.txt').read_text(),'fix'); self.assertTrue(i.git_branch(p).startswith('kelvin/'))
                with self.assertRaises(RuntimeError): i.execute('work','app again')
    def test_readonly_and_write_dispatch(self):
        with patch.object(i,'ig_call',return_value='ok') as m:
            self.assertEqual(i.execute('ig','reply 123 hi'),'ok'); m.assert_called_once_with('123/replies',body={'message':'hi'})
        with patch.object(i,'run',return_value='ok') as m:
            self.assertEqual(i.execute('gh','runs owner/repo'),'ok'); self.assertEqual(m.call_args.args[0],['gh','run','list','--repo','owner/repo','--limit','10'])
    def test_claude_work_args(self):
        with patch.object(i,'run',return_value=json.dumps({'result':'ok'})) as m:
            self.assertEqual(i.claude_work('.', 'fix'), 'ok'); cmd=m.call_args.args[0]; self.assertIn('acceptEdits',cmd); self.assertIn('Bash',cmd[cmd.index('--disallowedTools')+1]); self.assertNotIn('bypassPermissions',cmd)
    def test_agent_routes(self):
        with patch.object(i,'execute',return_value='ok') as m:
            self.assertEqual(execute_agent('claude','default','gh','repos',[],'.','.','.'),'ok'); m.assert_called_once_with('gh','repos')
    def test_no_secret_on_disk_config_public(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cfg.json'; i.save(p,{'ig_token':'secret'}); self.assertEqual(p.stat().st_mode&0o777,0o600); self.assertEqual(i.load(p)['ig_token'],'secret')
