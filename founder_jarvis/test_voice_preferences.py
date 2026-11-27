import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from founder_jarvis.voice_preferences import VoicePreferences
from founder_jarvis.runtime import Voice, mac_voice

class VoicePreferenceTests(unittest.TestCase):
    def test_persist_across_restart_and_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'voice.json'; pref=VoicePreferences(path)
            self.assertEqual(pref.load(),'ru'); pref.save('uz')
            self.assertEqual(VoicePreferences(path).load(),'uz')
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            pref.save('ru'); self.assertEqual(pref.load(),'ru')
    def test_invalid_value_does_not_replace(self):
        with tempfile.TemporaryDirectory() as d:
            p=VoicePreferences(Path(d)/'voice.json'); p.save('uz')
            for invalid in ('en','../../bad','auto',None):
                with self.assertRaises(ValueError): p.save(invalid)
            self.assertEqual(p.load(),'uz')
    def test_corrupt_setting(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'voice.json'; path.write_text('broken')
            self.assertEqual(VoicePreferences(path).load('uz'),'uz')
            self.assertEqual(VoicePreferences(path).load('invalid'),'ru')
    def test_selected_language_is_forwarded_to_local_whisper(self):
        with tempfile.TemporaryDirectory() as d:
            exe=Path(d)/'python'; exe.touch()
            with patch.dict(os.environ,{'KELVIN_SPEECH_PYTHON':str(exe)}),patch('subprocess.run',return_value=SimpleNamespace(stdout='{"text":"salom"}')) as run:
                self.assertEqual(Voice('uz').transcribe(Path(d)/'voice.ogg'),'salom')
                self.assertEqual(run.call_args.args[0][-1],'uz')
    def test_no_wrong_language_voice_fallback(self):
        with patch('subprocess.run',return_value=SimpleNamespace(stdout='Yuri    ru_RU # привет\n')):
            with self.assertRaises(RuntimeError): mac_voice('uz')
    def test_voice_subprocesses_do_not_receive_bot_token(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'TELEGRAM_BOT_TOKEN':'secret'}),patch('shutil.which',return_value='/usr/bin/fake'),patch('sys.platform','darwin'),patch('founder_jarvis.runtime.mac_voice',return_value='Yuri'),patch('subprocess.run') as run:
            self.assertEqual(Voice('ru').speak('Привет',Path(d)).name,'speech.ogg')
            for call in run.call_args_list:
                self.assertNotIn('TELEGRAM_BOT_TOKEN',call.kwargs['env'])

class VoiceBenchmarkTests(unittest.TestCase):
    def test_word_error_rate_and_uzbek_normalization(self):
        from founder_jarvis.voice_benchmark import word_errors
        self.assertEqual(word_errors('Salom, o‘zbek tilida!',"salom o'zbek tilida"),(0,3))
        self.assertEqual(word_errors('Новые заявки за неделю','новые заявки неделю'),(1,4))
        self.assertEqual(word_errors('Привет',''),(1,1))
    def test_missing_files_are_not_success(self):
        import json
        from founder_jarvis.voice_benchmark import benchmark, summarize, MANIFEST
        with tempfile.TemporaryDirectory() as d:
            rows=json.loads(MANIFEST.read_text());results=benchmark(Path(d),rows)
            self.assertEqual(len(results),40)
            self.assertTrue(all(r['status']=='missing' for r in results))
            self.assertFalse(summarize(results)['ru']['complete']);self.assertIsNone(summarize(results)['uz']['wer'])
    def test_measurement_on_fake_recognizer_is_labeled_by_test(self):
        import wave
        from founder_jarvis.voice_benchmark import benchmark, summarize
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'ru-01.wav'
            with wave.open(str(path),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\0\0'*16000)
            rows=benchmark(Path(d),[{'id':'ru-01','language':'ru','text':'Привет'}],lambda lang:SimpleNamespace(transcribe=lambda p:'Привет'))
            self.assertEqual(rows[0]['status'],'measured');self.assertEqual(summarize(rows)['ru']['wer'],0)
