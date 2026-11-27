import unittest, tempfile, asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from founder_jarvis.native_advisor import answer,MarketSearch
from founder_jarvis import advisor
class NativeAdvisor(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.workspace=Path(temp.name)
    def test_real_orchestrator_dispatch(self):
        search=Mock();search.execute.return_value=SimpleNamespace(success=True,content='https://example.com evidence')
        complete=Mock(side_effect=['TOOL: market_search\nINPUT: {"topic":"competitors"}','FINAL_ANSWER: готово'])
        self.assertTrue(answer('Проверь конкурентов',[],self.workspace,complete,search).startswith('готово'));self.assertEqual(complete.call_count,2);self.assertEqual(search.execute.call_count,1)
        self.assertIn('https://example.com',complete.call_args.args[0])
    def test_reject_arbitrary_query(self):
        search=Mock();t=MarketSearch(search);self.assertFalse(t.execute(topic='secret').success);self.assertFalse(t.execute(topic='market',query='secret').success);search.execute.assert_not_called()
    def test_regular_dialog_no_search(self):
        search=Mock();complete=Mock(return_value='FINAL_ANSWER: привет');self.assertEqual(answer('Привет',[],self.workspace,complete,search),'привет');search.execute.assert_not_called()
    def test_report_search_failure_evidence(self):
        search=Mock();search.execute.side_effect=RuntimeError('offline');complete=Mock(return_value='FINAL_ANSWER: данных нет');self.assertTrue(answer('Утренний доклад',[],self.workspace,complete,search).startswith('данных нет'));self.assertIn('Поиск недоступен',complete.call_args.args[0])
class NativeScheduler(unittest.IsolatedAsyncioTestCase):
    async def test_real_scheduler(self):
        with tempfile.TemporaryDirectory() as d:
            fired=asyncio.Event()
            async def dispatch():fired.set();return 'ok'
            sched,db=advisor.scheduler(Path(d),asyncio.get_running_loop(),dispatch)
            try:await asyncio.wait_for(fired.wait(),3)
            finally:await asyncio.to_thread(sched.stop);db.close()
