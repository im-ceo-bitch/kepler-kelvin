import json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from types import SimpleNamespace
from founder_jarvis import native_advisor as n
from founder_jarvis.research_evidence import observations,validate_report

RAW='### Test source\nSource: https://example.org/article\nSummary: Travel booking preferences vary across different families and dates.'
class NativeResearchTests(unittest.TestCase):
    def test_original_executor_and_bounded_synthesis(self):
        with tempfile.TemporaryDirectory() as d:
            source=observations(RAW,'market')[0]
            valid={'findings':[{'source_id':source['id'],'quote':'Travel booking preferences vary across different families and dates.','implication':'Проверить спрос на семейные пакеты.'}],'recommendation':'Проверить статистику обращений','measure':'Доля запросов о семейных поездках','risk':'Выборка не характеризует весь рынок'}
            search=Mock();search.execute.return_value=SimpleNamespace(content=RAW,success=True)
            complete=Mock(return_value='FINAL_ANSWER: '+json.dumps(valid,ensure_ascii=False))
            result=n.research('market',Path(d),complete,search)
            self.assertEqual(result['report'],valid);self.assertIn('https://example.org/article',result['text']);self.assertEqual(complete.call_count,1);self.assertEqual(search.execute.call_count,1)
            complete.reset_mock();same=n.research('market',Path(d),complete,search,prior=[source['id']]);self.assertIsNone(same['report']);complete.assert_not_called()
    def test_search_failure_no_model(self):
        with tempfile.TemporaryDirectory() as d:
            search=Mock();search.execute.return_value=SimpleNamespace(content='',success=False);complete=Mock()
            with self.assertRaises(RuntimeError):n.research('market',Path(d),complete,search)
            complete.assert_not_called()
    def test_malformed_model_report_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            search=Mock();search.execute.return_value=SimpleNamespace(content=RAW,success=True)
            complete=Mock(return_value='FINAL_ANSWER: {"findings":[]}')
            with self.assertRaises(ValueError):n.research('market',Path(d),complete,search)
            self.assertEqual(complete.call_count,1)

    def test_watchlist_baseline_no_inference_and_host_scope(self):
        with tempfile.TemporaryDirectory() as d:
            raw='### Offer\nSource: https://umrabor.uz/ru\nSummary: Family pilgrimage offer and other travel terms are visible.'
            search=Mock();search.execute.return_value=SimpleNamespace(content=raw,success=True);complete=Mock()
            result=n.research('watch-umrabor',Path(d),complete,search);self.assertIsNone(result['report']);self.assertIn('Первое наблюдение',result['text']);complete.assert_not_called()
            search.execute.return_value=SimpleNamespace(content=RAW,success=True)
            with self.assertRaises(RuntimeError):n.research('watch-umrabor',Path(d),complete,search)
