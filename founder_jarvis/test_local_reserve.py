import tempfile
import unittest
from unittest.mock import Mock, patch
from pathlib import Path

from founder_jarvis.native_advisor import LocalReserveTransport
from founder_jarvis.runtime import ClaudeRateLimited, execute_claude


class ReserveTests(unittest.TestCase):
    def test_switch_only_once_after_429(self):
        cloud = Mock(side_effect=ClaudeRateLimited())
        with patch("openjarvis.engine.ollama.OllamaEngine") as local:
            engine = LocalReserveTransport(Path("."), cloud)
            engine.generate([], model="default")
            engine.generate([], model="default")
            self.assertEqual(cloud.call_count, 1)
            self.assertEqual(local.return_value.generate.call_count, 2)
            self.assertEqual(local.return_value.generate.call_args.kwargs["model"], "qwen2.5:3b")
            engine.close()
            local.return_value.close.assert_called_once()

    def test_other_errors_do_not_switch(self):
        with patch("openjarvis.engine.ollama.OllamaEngine") as local:
            engine = LocalReserveTransport(Path("."), Mock(side_effect=RuntimeError("auth")))
            with self.assertRaises(RuntimeError):
                engine.generate([])
            local.assert_not_called()

    def test_request_text_cannot_trigger_reserve(self):
        with tempfile.TemporaryDirectory() as root, patch("founder_jarvis.runtime.claude_command", return_value=["claude"]), patch("subprocess.Popen") as process:
            instance = process.return_value
            instance.returncode = 0
            instance.communicate.return_value = ('{"is_error":false,"result":"rate limit 429"}', '')
            self.assertEqual(execute_claude("hi", [], root), "rate limit 429")
            instance.returncode = 1
            instance.communicate.return_value = ('{"is_error":true,"api_error_status":429}', '')
            with self.assertRaises(ClaudeRateLimited):
                execute_claude("hi", [], root)

    def test_reserve_scope(self):
        from founder_jarvis.native_advisor import reserve_allowed
        for prompt in ('Привет', 'Ответь только словом сапфир.', 'Какое слово было в предыдущем ответе? Ответь тем же словом.'):
            self.assertTrue(reserve_allowed(prompt))
        for prompt in ('Придумай оффер', 'Сколько бронирований?', 'Сделай видео', 'Привет, придумай цены', 'Исследуй рынок'):
            self.assertFalse(reserve_allowed(prompt))
        self.assertFalse(reserve_allowed('Привет', ['market']))

    def test_provider_rejects_codex(self):
        from founder_jarvis.native_advisor import provider_engine
        with patch.dict('os.environ', {'KELVIN_PROVIDER':'codex'}):
            with self.assertRaises(RuntimeError): provider_engine(Path('.'))

    def test_scoped_agent_local_fallback_is_marked(self):
        from founder_jarvis.native_advisor import answer
        from founder_jarvis.native_advisor import ClaudeRateLimited
        with tempfile.TemporaryDirectory() as d, patch.dict('os.environ', {'KELVIN_PROVIDER':'claude','KELVIN_LOCAL_ON_CLAUDE_LIMIT':'1'}), patch('openjarvis.engine.ollama.OllamaEngine') as local:
            local.return_value.generate.return_value={'content':'FINAL_ANSWER: привет','usage':{}}
            result=answer('Привет',[],Path(d),Mock(side_effect=ClaudeRateLimited()),Mock())
            self.assertTrue(result.startswith('привет'));self.assertIn('Локальный резерв',result)

    def test_no_reserve_for_offer(self):
        from founder_jarvis.native_advisor import answer
        with tempfile.TemporaryDirectory() as d, patch.dict('os.environ', {'KELVIN_PROVIDER':'claude','KELVIN_LOCAL_ON_CLAUDE_LIMIT':'1'}), patch('openjarvis.engine.ollama.OllamaEngine') as local:
            with self.assertRaises(ClaudeRateLimited):answer('Составь коммерческий оффер',[],Path(d),Mock(side_effect=ClaudeRateLimited()),Mock())
            local.assert_not_called()
