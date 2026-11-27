import os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from founder_jarvis.runtime import execute_claude, execute_agent
from founder_jarvis.macos.service import register

class ClaudeTests(unittest.TestCase):
    def test_cli_and_secret_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'claude'; p.touch()
            with patch.dict(os.environ,{'KELVIN_CLAUDE_BIN':str(p),'TELEGRAM_BOT_TOKEN':'secret','JARVIS_OWNER_ID':'42'}),patch('subprocess.Popen') as popen:
                proc=popen.return_value; proc.returncode=0; proc.communicate.return_value=(' {"result":"Привет", "is_error":false}', '')
                self.assertEqual(execute_claude('hi',[],d),'Привет')
                args=popen.call_args.args[0]; self.assertEqual(args[args.index('--tools')+1],''); self.assertNotIn('secret',str(args)); self.assertNotIn('TELEGRAM_BOT_TOKEN',popen.call_args.kwargs['env'])
                self.assertIn('hi',proc.communicate.call_args.args[0])
    def test_dispatch(self):
        with patch('founder_jarvis.runtime.execute_claude',return_value='ok') as run:
            self.assertEqual(execute_agent('claude','default','chat','hi',[],'w','c','h'),'ok'); run.assert_called_once()
    def test_failed_response(self):
        with patch('founder_jarvis.runtime.claude_command',return_value=['claude']),patch('subprocess.Popen') as popen:
            proc=popen.return_value; proc.returncode=0; proc.communicate.return_value=(' {"is_error":true,"result":"bad"}', '')
            with self.assertRaises(RuntimeError): execute_claude('hi',[],'.')
    def test_register_retry(self):
        from types import SimpleNamespace as N
        states=iter([True,True,False,False,True]); calls=[]
        def run(args,**kw):
            calls.append(args[1]); return N(returncode=(0 if next(states) else 1) if args[1]=='print' else 0,stderr='')
        with patch('subprocess.run',side_effect=run),patch('time.sleep'):
            register('gui/501','com.kelvin.manager','/tmp/test.plist')
        self.assertEqual(calls.count('bootstrap'),2); self.assertIn('kickstart',calls)
