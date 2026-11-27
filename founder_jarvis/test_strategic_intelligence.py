import copy, datetime as dt, json, unittest
from unittest.mock import Mock
from founder_jarvis import strategic_intelligence as s, shared_business, autonomy
from founder_jarvis.test_autonomy import research_result
NOW=dt.datetime(2026,11,27,12,tzinfo=dt.timezone.utc)
def fixture(now=NOW):
    d=lambda x:(now+dt.timedelta(days=x)).isoformat()
    rows={'bookingCohort':[dict(period='current',total=10,active=3,cancelled=1,pending=6),dict(period='previous',total=5,active=3,cancelled=0,pending=2)],'careCohort':[dict(period='current',total=10,familyKnown=10,family=7),dict(period='previous',total=5,familyKnown=5,family=1)],'careMonths':[dict(period='current',dimension='2026-12',total=8,family=7),dict(period='current',dimension='2027-01',total=2,family=0),dict(period='previous',dimension='2026-12',total=5,family=1)],'appSessions':[dict(period='current',total=100,checkout=20,submitted=12,both=5,errors=3,crashes=2),dict(period='previous',total=80,checkout=10,submitted=8,both=4,errors=0,crashes=0)],'careDue':[dict(total=6,due=2)],'bookingTiers':[dict(period='current',dimension='comfort',total=10),dict(period='previous',dimension='economy',total=5)]}
    return {'strategy':{'version':1,'asOf':d(0),'windows':{'current':{'start':d(-7),'end':d(0)},'previous':{'start':d(-14),'end':d(-7)}},'metrics':{k:{'available':True,'rows':v,'source':'test.source'} for k,v in rows.items()}}}
def report(x=None,now=NOW):return s.report(x or fixture(now),now)
def record(value,stamp=1,id='strategy-test'):return {'id':id,'kind':'decision','trust':'owner','content':json.dumps(value),'created_at':stamp,'version':1}
class Strategy(unittest.TestCase):
    def test_01_missing(self):self.assertFalse(s.report({},NOW)['available'])
    def test_02_stale(self):self.assertFalse(report(fixture(),NOW+dt.timedelta(minutes=31))['available'])
    def test_03_future(self):self.assertFalse(report(fixture(),NOW-dt.timedelta(minutes=3))['available'])
    def test_04_period_mismatch(self):
        x=fixture();x['strategy']['windows']['previous']['end']=NOW.isoformat();self.assertFalse(report(x)['available'])
    def test_05_version(self):
        x=fixture();x['strategy']['version']=2;self.assertFalse(report(x)['available'])
    def test_06_zero_denominator(self):self.assertIsNone(s.pair(0,0)['percent']);self.assertIsNone(s.compare(4,0)['changePercent'])
    def test_07_negative_boolean(self):self.assertIsNone(s.pair(True,3));self.assertIsNone(s.compare(-1,3));self.assertIsNone(s.pair(4,3))
    def test_08_valid_cohort(self):self.assertEqual(report()['metrics']['bookingCohort']['change']['changePercent'],100);self.assertEqual(report()['metrics']['bookingCohort']['activeShare']['percent'],30)
    def test_09_unknown_is_not_zero(self):
        x=fixture();x['strategy']['metrics']['bookingCohort']={'available':False};self.assertNotIn('bookingCohort',report(x)['metrics'])
    def test_10_empty_known(self):
        x=fixture();x['strategy']['metrics']['bookingCohort']['rows']=[];self.assertEqual(report(x)['metrics']['bookingCohort']['change']['current'],0)
    def test_11_invalid_partition(self):
        x=fixture();x['strategy']['metrics']['bookingCohort']['rows'][0]['active']=9;self.assertNotIn('bookingCohort',report(x)['metrics']);self.assertNotIn('bookingTiers',report(x)['metrics'])
    def test_12_family_signal(self):
        r=next(x for x in report()['recommendations'] if x['id']=='family');self.assertIn('7 из 10',r['reason']);self.assertIn('гипотеза',r['reason'])
    def test_13_small_sample(self):
        x=fixture();x['strategy']['metrics']['careCohort']['rows'][0].update(total=3,familyKnown=3,family=3);self.assertNotIn('family',[r['id'] for r in report(x)['recommendations']])
    def test_14_specific_month(self):self.assertIn('month-2026-12',[r['id'] for r in report()['recommendations']])
    def test_15_dimension_total_mismatch(self):
        x=fixture();x['strategy']['metrics']['careMonths']['rows'][0]['total']=9;self.assertNotIn('careMonths',report(x)['metrics'])
    def test_16_dimension_injection(self):
        x=fixture();x['strategy']['metrics']['careMonths']['rows'][0]['dimension']='secret';self.assertNotIn('careMonths',report(x)['metrics'])
    def test_17_session_measure(self):self.assertEqual(report()['metrics']['appSessions']['checkoutWithSubmit']['percent'],25)
    def test_18_invalid_session_overlap(self):
        x=fixture();x['strategy']['metrics']['appSessions']['rows'][0]['both']=15;self.assertNotIn('appSessions',report(x)['metrics'])
    def test_19_due_priority(self):self.assertEqual(report()['recommendations'][0]['id'],'care-due')
    def test_20_brief_single_action(self):
        x=fixture();b=autonomy.brief('morning',x,[],NOW);self.assertLessEqual(len(b),900);self.assertEqual(b.count('Предлагаю:'),1);self.assertIn('2 из 6',b)
    def test_21_context(self):
        x=fixture(dt.datetime.now(dt.timezone.utc));p,_=shared_business.answer_context({'snapshot':x,'job':{'prompt':'Как бизнес?'},'typedMemory':[]});self.assertIn('Validated strategic metrics',p);self.assertIn('care-due',p)
    def test_22_no_model_for_command(self):
        x=fixture(dt.datetime.now(dt.timezone.utc));b=Mock();v=s.command(b,{'source':'app','prompt':'/strategy'},{'snapshot':x});self.assertIn('Заявки',v);b.call.assert_not_called()
    def test_23_owner_decision_persisted(self):
        x=fixture(dt.datetime.now(dt.timezone.utc));b=Mock();j={'source':'telegram','prompt':'/decision family accept','id':'test-1234','lease':'lease'};s.command(b,j,{'snapshot':x});action,data=b.call.call_args.args;self.assertEqual(action,'records');self.assertEqual(data['kind'],'decision');self.assertEqual(json.loads(data['content'])['baseline'],7);self.assertEqual(data['lease'],'lease');b.reset_mock();s.command(b,{**j,'source':'customer'},{'snapshot':x});b.call.assert_not_called()
    def test_24_no_accept_unknown(self):
        b=Mock();s.command(b,{'source':'app','prompt':'/decision missing accept','id':'x','lease':'y'},{'snapshot':fixture(dt.datetime.now(dt.timezone.utc))});b.call.assert_not_called()
    def test_25_followup_nonoverlap(self):
        d={'schema':1,'proposal':'family','status':'accept','kpi':'careFamily','baseline':7,'baselineEnd':NOW.isoformat()};r=[record(d)];self.assertEqual(s.decision_reviews(r,report(),NOW)[0]['state'],'awaiting_comparable_data');later=NOW+dt.timedelta(days=7);self.assertEqual(s.decision_reviews(r,report(now=later),later)[0]['state'],'ready_for_review')
    def test_26_latest_reject(self):
        d={'schema':1,'proposal':'family','status':'accept','kpi':'careFamily','baseline':7,'baselineEnd':NOW.isoformat()};self.assertFalse(s.decision_reviews([record(d),record({**d,'status':'reject'},2,'strategy-other')],report(),NOW))
    def test_27_public_evidence(self):
        e=research_result('market',NOW.isoformat());r=s.research_context([e],report(),NOW);self.assertEqual(r[0]['url'],'https://example.org/travel');self.assertIn('family',r[0]['relatedProposals']);self.assertIn('not proof',r[0]['verification'])
    def test_28_stale_evidence(self):self.assertFalse(s.research_context([research_result('market',(NOW-dt.timedelta(days=8)).isoformat())],report(),NOW))
    def test_29_fabricated_quote(self):
        e=research_result('market',NOW.isoformat());e['report']['findings'][0]['quote']='Fake unsupported evidence text';self.assertFalse(s.research_context([e],report(),NOW))
    def test_30_unknown_metrics_followup(self):
        d={'schema':1,'proposal':'family','status':'accept','kpi':'careFamily','baseline':7,'baselineEnd':NOW.isoformat()};later=NOW+dt.timedelta(days=8);self.assertIsNone(s.decision_reviews([record(d)],s.report({},later),later)[0]['current'])
    def test_31_decided_proposal_not_repeated_in_brief(self):
        x=fixture();d={'schema':1,'proposal':'care-due','status':'reject','kpi':'careDue','baseline':2,'baselineEnd':NOW.isoformat()};x['strategicDecisions']=[record(d)]
        self.assertNotIn('Проверить просроченные обращения Care',autonomy.brief('morning',x,[],NOW));self.assertNotIn('care-due',[r['id'] for r in s.fresh_proposals(report(x),x['strategicDecisions'])])
    def test_32_decision_retry_no_duplicate_even_if_snapshot_missing(self):
        import hashlib
        j={'source':'telegram','prompt':'/decision family accept','id':'job-id','lease':'lease'};ident='strategy-'+hashlib.sha256(j['id'].encode()).hexdigest()[:32];b=Mock()
        self.assertIn('уже',s.command(b,j,{'snapshot':{},'typedMemory':[record({},id=ident)]}));b.call.assert_not_called()
    def test_33_reject_existing_when_signal_missing(self):
        j={'source':'app','prompt':'/decision family reject','id':'job-id','lease':'lease'};d={'schema':1,'proposal':'family','status':'accept','kpi':'careFamily','baseline':7,'baselineEnd':NOW.isoformat()};b=Mock();s.command(b,j,{'snapshot':{},'typedMemory':[record(d)]});self.assertEqual(json.loads(b.call.call_args.args[1]['content'])['status'],'reject')
