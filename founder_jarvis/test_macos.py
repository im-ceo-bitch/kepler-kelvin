import unittest, tempfile, plistlib, tomllib
from pathlib import Path
from founder_jarvis.macos.service import plist
from founder_jarvis.runtime import config_file

class MacTests(unittest.TestCase):
    def test_launch_agent(self):
        p=plist('com.kelvin.manager',['/usr/bin/caffeinate','-s','/path with spaces/python','-m','founder_jarvis.runtime'],'/usr/bin',repo='/path with spaces',env={'KELVIN_ENV_FILE':'/private/path'})
        p=plistlib.loads(plistlib.dumps(p))
        self.assertTrue(p['RunAtLoad']); self.assertTrue(p['KeepAlive']); self.assertEqual(p['ThrottleInterval'],30)
        self.assertEqual(p['ProgramArguments'][2],'/path with spaces/python'); self.assertNotIn('TELEGRAM_BOT_TOKEN',p['EnvironmentVariables'])
    def test_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'config.toml'; config_file(path,Path(tmp)); data=tomllib.loads(path.read_text())
            self.assertIn('Your name is Kelvin',data['agent']['system_prompt'])
