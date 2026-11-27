import os,tempfile,unittest,sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock,patch
from types import SimpleNamespace
from founder_jarvis import native_advisor as n, intelligence_core as core

class IntelligenceCoreTests(unittest.TestCase):
    def test_30_denied_tool_attempts_audited(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'KELVIN_PROVIDER':'claude','KELVIN_PERSONA_ROOT':d}):
            search=Mock(); names=['file_write','shell','channel_send','memory_store','unknown','market_search']
            for i in range(30):
                name=names[i%6];args='{"topic":"private"}' if name=='market_search' else '{}'
                f=Mock(side_effect=[f'TOOL: {name}\nINPUT: {args}','FINAL_ANSWER: действие не выполнено'])
                self.assertEqual(n.answer('Попробуй запрещённое действие',[],Path(d),f,search),'действие не выполнено')
            search.execute.assert_not_called()
            with closing(sqlite3.connect(Path(d)/'.kelvin-core/audit.db')) as db:
                rows=db.execute("SELECT COUNT(*) FROM security_events WHERE content_preview LIKE '%tool=%'").fetchone()[0]
                self.assertGreaterEqual(rows,30)
    def test_40_routing_protocol_cases(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'KELVIN_PROVIDER':'claude','KELVIN_PERSONA_ROOT':d}):
            for i in range(40):
                search=Mock();search.execute.return_value=SimpleNamespace(success=True,content='https://example.org/evidence')
                completion=Mock(side_effect=['TOOL: market_search\nINPUT: {"topic":"platforms"}','FINAL_ANSWER: проверено'] if i%2 else ['FINAL_ANSWER: привет'])
                out=n.answer('Проверь платформы' if i%2 else 'Привет',[],Path(d),completion,search)
                self.assertEqual(search.execute.call_count,i%2)
                self.assertTrue(out.startswith('проверено' if i%2 else 'привет'))
    def test_provider_switch_no_fallback(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'KELVIN_PROVIDER':'ollama','KELVIN_LOCAL_MODEL':'qwen2.5:3b'}),patch('openjarvis.engine.ollama.OllamaEngine') as factory:
            engine,model=n.provider_engine(Path(d));self.assertIs(engine,factory.return_value);self.assertEqual(model,'qwen2.5:3b');factory.assert_called_once_with(host='http://127.0.0.1:11434',timeout=120)
        with patch.dict(os.environ,{'KELVIN_PROVIDER':'unknown'}):
            with self.assertRaises(RuntimeError):n.provider_engine(Path('.'))
    def test_native_extractor_strict_quotes(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'KELVIN_PROVIDER':'claude','KELVIN_PERSONA_ROOT':d}):
            result=n.extract_candidates('Моя цель — индивидуальная умра',Path(d),Mock(return_value='["индивидуальная умра","fabricated result"]'))
            self.assertEqual(result,['индивидуальная умра'])
    def test_failed_engine_not_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            e=Mock();e.engine_id='test';e.health.return_value=False
            with self.assertRaises(RuntimeError):core.build_system(e,'default',[],Path(d))
