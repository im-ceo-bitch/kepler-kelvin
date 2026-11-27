import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from founder_jarvis.runtime import agent_command, install_status, local_model_status, mac_voice, Voice

class RecoveryTests(unittest.TestCase):
    def test_agent_uses_separate_python(self):
        with patch.dict(os.environ, {'KELVIN_AGENT_PYTHON':'/local/core/python'}):
            self.assertEqual(agent_command('ollama','m','chat','hi',[])[0],'/local/core/python')
    def test_model_probe(self):
        with patch('urllib.request.urlopen',return_value=io.BytesIO(b'{"models":[{"name":"m"}]}')):
            self.assertEqual(local_model_status('m'),'Модель найдена')
        with patch('urllib.request.urlopen',return_value=io.BytesIO(b'{"models":[]}')):
            self.assertEqual(local_model_status('m'),'Модель ещё не загружена')
        with patch('urllib.request.urlopen',side_effect=OSError):
            self.assertEqual(local_model_status('m'),'Ollama недоступна')
    def test_voice_fallback(self):
        voices='Alex                 en_US # hello\nYuri (Enhanced)      ru_RU # привет\n'
        with patch('subprocess.run',return_value=SimpleNamespace(stdout=voices)), patch.dict(os.environ,{'JARVIS_MAC_VOICE':'Milena'}):
            self.assertEqual(mac_voice('ru'),'Yuri (Enhanced)')
            with self.assertRaises(RuntimeError): mac_voice('uz')
    def test_voice_subprocess_no_bot_secret(self):
        with tempfile.TemporaryDirectory() as d:
            executable=Path(d)/'python'; executable.touch()
            with patch.dict(os.environ,{'KELVIN_SPEECH_PYTHON':str(executable),'TELEGRAM_BOT_TOKEN':'secret','JARVIS_OWNER_ID':'42','KELVIN_ENV_FILE':'/secret'}),patch('subprocess.run',return_value=SimpleNamespace(stdout='{"text":"hello"}')) as run:
                self.assertEqual(Voice().transcribe(Path(d)/'voice.ogg'),'hello')
                env=run.call_args.kwargs['env']; self.assertNotIn('TELEGRAM_BOT_TOKEN',env); self.assertNotIn('KELVIN_ENV_FILE',env); self.assertNotIn('JARVIS_OWNER_ID',env)
    def test_install_status(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'status'
            with patch.dict(os.environ,{'KELVIN_INSTALL_STATUS':str(p)}):
                self.assertEqual(install_status(),'Нет данных установки'); p.write_text('Checking model'); self.assertEqual(install_status(),'Checking model')
    def test_install_order(self):
        s=(Path(__file__).parent/'macos/install.sh').read_text()
        self.assertNotIn('uv sync',s)
        self.assertNotIn('pull "$MODEL"',s)
        self.assertIn('service.py runtime',s)
