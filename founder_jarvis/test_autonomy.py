import asyncio, datetime as dt, json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from founder_jarvis import autonomy as a, research_evidence as e


def stamp(day=27,h=8,m=0):return dt.datetime(2026,11,day,h,m,tzinfo=a.ZONE)
def snapshot(n):return {'data':{'supportThreads':{'available':True,'rows':[{'unread':n}]}}}
def research_result(topic='market',at=None):
    at=at or stamp().isoformat();raw='### Source\nSource: https://example.org/travel\nSummary: Family travel preferences depend on available dates and accommodation.'
    src=e.observations(raw,topic,at)[0]
    report={'findings':[{'source_id':src['id'],'quote':src['snippet'],'implication':'Проверить гипотезу'}],'recommendation':'Сравнить обращения','measure':'Измерить долю','risk':'Неизвестна репрезентативность'}
    return {'sources':[src],'report':report,'text':'unused'}

class LedgerTests(unittest.TestCase):
    def setUp(self):
        d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup);self.path=Path(d.name)/'ledger';self.l=a.Ledger(self.path);self.addCleanup(lambda:self.l.close())
    def restart(self):self.l.close();self.l=a.Ledger(self.path)
    def test_100_repeated_ticks_and_10_restarts(self):
        for i in range(100):
            if i%10==0:self.restart()
            self.l.plan(stamp());j=self.l.claim(stamp())
            if j:self.l.complete(j,{'text':'Утро'},stamp(),True)
        self.assertEqual(self.l.status(),{'done':1});notice=self.l.claim_notice(stamp());self.assertIsNotNone(notice)
        self.l.notice_done(notice['id'],True,stamp());self.restart();self.assertIsNone(self.l.claim_notice(stamp()))
    def test_expired_no_catchup(self):
        self.l.plan(stamp());self.l.plan(stamp(h=21));self.assertEqual(self.l.status(),{'expired':1,'queued':1});self.assertEqual(self.l.claim(stamp(h=21))['kind'],'evening')
    def test_retry_and_daily_budget_persistent(self):
        self.l.plan(stamp(h=12));j=self.l.claim(stamp(h=12));self.l.failed(j,stamp(h=12));self.assertIsNone(self.l.claim(stamp(h=12,m=1)))
        self.restart();j=self.l.claim(stamp(h=12,m=15));self.assertEqual(j['attempts'],2);self.l.failed(j,stamp(h=12,m=15));self.assertIsNone(self.l.claim(stamp(h=12,m=30)))
        self.l.plan(stamp(h=16));j=self.l.claim(stamp(h=16));self.l.failed(j,stamp(h=16));j=self.l.claim(stamp(h=16,m=15));self.l.failed(j,stamp(h=16,m=15))
        self.assertEqual(self.l.db.execute('SELECT used FROM auto_budget').fetchone()[0],4);self.assertEqual(self.l.status(),{'failed':2})
    def test_recovery_and_ambiguous_send_not_retried(self):
        self.l.plan(stamp(h=12));j=self.l.claim(stamp(h=12));self.restart();j2=self.l.claim(stamp(h=12));self.assertEqual(j['id'],j2['id']);self.assertEqual(j2['attempts'],2)
        self.l.complete(j2,research_result(),stamp(h=12));self.l.plan(stamp(h=8));morning=self.l.claim(stamp(h=8));self.l.complete(morning,{'text':'Hello'},stamp(h=8),True)
        self.l.claim_notice(stamp(h=8));self.restart();self.assertIsNone(self.l.claim_notice(stamp(h=8)));self.assertEqual(self.l.db.execute("SELECT delivery FROM auto_jobs WHERE kind='morning'").fetchone()[0],'uncertain')
    def test_pause_persist_and_expire_pending(self):
        self.l.plan(stamp());j=self.l.claim(stamp());self.l.complete(j,{'text':'Hello'},stamp(),True);self.l.set('enabled','0');self.restart();self.assertEqual(self.l.setting('enabled','1'),'0');self.l.set('enabled','1');self.assertIsNone(self.l.claim_notice(stamp()))
    def test_signals_require_real_sustained_growth(self):
        self.assertFalse(self.l.observe({},stamp()));self.assertFalse(self.l.observe(snapshot(2),stamp()));self.assertFalse(self.l.observe(snapshot(5),stamp(h=8,m=30)));self.assertTrue(self.l.observe(snapshot(5),stamp(h=9)));self.assertFalse(self.l.observe(snapshot(5),stamp(h=9,m=30)));self.assertFalse(self.l.observe(snapshot(5),stamp(day=28)));self.assertEqual(self.l.status(),{'done':1})
    def test_100_mixed_observations_critical_and_quiet_hours(self):
        # Previously unknown/unavailable data alone must never produce an alert.
        def metric(available,n=0):return {'data':{'bookingsByStatus':{'available':available},'supportThreads':{'available':True,'rows':[{'unread':n}]}}}
        now=stamp(h=1)
        for i in range(100):
            self.l.observe(metric(False),now+dt.timedelta(seconds=i))
        self.assertFalse(self.l.status())
        self.l.observe(metric(True,2),stamp(h=2));self.l.observe(metric(False,5),stamp(h=2,m=30));self.assertTrue(self.l.observe(metric(False,5),stamp(h=3)))
        critical=self.l.claim_notice(stamp(h=3));self.assertEqual(critical['kind'],'critical');self.l.notice_done(critical['id'],True,stamp(h=3))
        self.assertIsNone(self.l.claim_notice(stamp(h=3))) # no nighttime ordinary/important message
        for i in range(20):self.l.observe(metric(False,5),stamp(h=3)+dt.timedelta(minutes=i+1))
        self.assertEqual(self.l.status(),{'done':2});self.assertIsNone(self.l.claim_notice(stamp(h=8)))
    def test_adaptive_topic_only_whitelisted(self):
        # Choose a day on which adaptation is allowed.
        now=stamp(day=20,h=12)
        while now.date().toordinal()%3:now+=dt.timedelta(days=1)
        prev=now-dt.timedelta(days=1);self.l.plan(prev);job=self.l.claim(prev)
        report=research_result('market',prev.isoformat());report['report']['next_topic']='hajj';self.l.complete(job,report,prev)
        self.l.plan(now);self.assertEqual(self.l.claim(now)['topic'],'hajj')
    def test_publish_retries_bounded(self):
        self.l.plan(stamp());j=self.l.claim(stamp());self.l.complete(j,{'text':'Hello'},stamp(),True)
        for m in range(0,75,15):
            now=stamp()+dt.timedelta(minutes=m);r=self.l.pending_publish(now)[0];self.l.publish_failed(r['id'],json.loads(r['result']),now)
            self.assertFalse(self.l.pending_publish(now))
        self.restart();self.assertFalse(self.l.pending_publish(stamp(day=28)))
    def test_no_duplicate_morning_or_repeat_recommendation(self):
        self.l.plan(stamp(day=26,h=12));j=self.l.claim(stamp(day=26,h=12));self.l.complete(j,research_result(at=stamp(day=26,h=12).isoformat()),stamp(day=26,h=12))
        self.assertEqual(len(self.l.research_since_briefing()),1);self.l.plan(stamp());j=self.l.claim(stamp());self.l.complete(j,{'text':'morning'},stamp(),True);self.assertFalse(self.l.research_since_briefing())
    def test_rotation_covers_all_topics(self):
        topics={r[2] for i in range(18) for h in [12,16] for r in a.slots(stamp(day=1,h=h)+dt.timedelta(days=i))};self.assertEqual(topics,set(e.TOPICS))
    def test_brief_length_no_invented_zero(self):
        result=research_result(at=stamp(day=26).isoformat());text=a.brief('morning',{},[result],stamp());self.assertLessEqual(len(text),900);self.assertIn('недоступны',text);self.assertIn('example.org',text);self.assertNotIn('0 непрочитанных',text)

class EvidenceTests(unittest.TestCase):
    def test_30_exact_quote_claims_and_hallucinated_variants(self):
        for i in range(30):
            topic=list(e.TOPICS)[i%9];r=research_result(topic);s=r['sources'];valid=r['report'];self.assertEqual(e.validate_report(valid,s),valid)
            for key,value in [('source_id','unseen'),('quote','Completely fabricated statement about prices.')]:
                bad=json.loads(json.dumps(valid));bad['findings'][0][key]=value
                with self.assertRaises(ValueError):e.validate_report(bad,s)
    def test_secret_and_invalid_url_excluded(self):
        for url in ['javascript:alert(1)','https://user:secret@example.org','https://localhost','https://example.org/'+'a'*64]:
            self.assertFalse(e.observations(f'### X\nSource: {url}\nSummary: Example public snippet for a test.', 'market'))
        self.assertFalse(e.observations('### X\nSource: https://example.org\nSummary: sk-ant-'+'A'*30,'market'))

class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_tick_quiet_research_archive_and_morning_notice(self):
        with tempfile.TemporaryDirectory() as d:
            l=a.Ledger(Path(d)/'db');self.addCleanup(l.close);now=[stamp(day=26,h=12)]
            bridge=Mock();bridge.call.side_effect=lambda action,data:{'snapshot':snapshot(1)} if data['action']=='snapshot' else {'ok':True}
            researcher=Mock(side_effect=lambda topic,prior:research_result(topic,now[0].isoformat()));send=AsyncMock();svc=a.Service(l,bridge,researcher,send,asyncio.Lock(),clock=lambda:now[0])
            await svc.tick();send.assert_not_awaited();researcher.assert_called_once();self.assertTrue(any(c.args[1].get('action')=='publish' for c in bridge.call.call_args_list))
            now[0]=stamp();await svc.tick();send.assert_awaited_once();self.assertLessEqual(len(send.call_args.args[0]),900)
            await svc.tick();send.assert_awaited_once();now[0]=stamp(h=21);await svc.tick();send.assert_awaited_once();self.assertEqual(l.status(),{'done':3})
    async def test_failed_search_never_notifies_and_pause_persists(self):
        with tempfile.TemporaryDirectory() as d:
            l=a.Ledger(Path(d)/'db');self.addCleanup(l.close);now=[stamp(h=12)];research=Mock(side_effect=RuntimeError('offline'));send=AsyncMock();svc=a.Service(l,None,research,send,asyncio.Lock(),clock=lambda:now[0]);await svc.tick();send.assert_not_awaited();now[0]=stamp(h=12,m=1);await svc.tick();research.assert_called_once();l.set('enabled','0');now[0]=stamp(h=12,m=16);await svc.tick();research.assert_called_once()
    async def test_owner_work_priority(self):
        with tempfile.TemporaryDirectory() as d:
            l=a.Ledger(Path(d)/'db');self.addCleanup(l.close);lock=asyncio.Lock();research=Mock();send=AsyncMock();svc=a.Service(l,None,research,send,lock,clock=lambda:stamp(h=12))
            async with lock:await svc.tick()
            research.assert_not_called();self.assertEqual(l.status(),{'queued':1})
