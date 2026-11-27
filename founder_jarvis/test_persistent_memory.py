import unittest, tempfile, json
from pathlib import Path
from unittest.mock import Mock
from founder_jarvis import persistent_memory as m, shared_business


def record(i,content,kind='business',trust='owner'):
    return dict(id=f'record-{i:04}',kind=kind,content=content,trust=trust,source='app:test',updated_at=i,version=1)

class PersistentMemoryTests(unittest.TestCase):
    def test_100_facts_100_distractors_and_20_ru_uz_queries(self):
        facts=[record(i,f'Маршрут код{1000+i} значение {i}') for i in range(100)]
        distractors=[record(100+i,f'Другая заметка номер {i}','episodic') for i in range(100)]
        hits=sum(any(r['id']==facts[i]['id'] for r in m.recall(facts+distractors,f'Что известно про код{1000+i}?')) for i in range(100))
        self.assertGreaterEqual(hits,90)
        for i in range(20):
            text=f'Uzbekistan loyiha belgi{i+100} maqsad' if i%2 else f'Цель проекта маркер{i+100}'
            row=record(i,text,'decision');q=f'belgi{i+100} nima?' if i%2 else f'маркер{i+100} решение?'
            with self.subTest(i=i):self.assertIn(row['id'],[r['id'] for r in m.recall([row]+distractors,q)])
    def test_20_deletions_rebuild_no_recall(self):
        for i in range(20):
            row=record(i,f'secretmarker{i+100}');self.assertTrue(m.recall([row],row['content']))
            self.assertFalse(m.recall([{**row,'deleted':True}],row['content']))
            self.assertFalse(m.recall([],row['content']))
    def test_candidate_and_customer_not_recalled(self):
        records=[record(1,'marker100','customer'),record(2,'marker100','decision','candidate'),record(3,'marker100','research','untrusted'),record(4,'marker100'),record(5,'a'*64)]
        self.assertEqual([x['id'] for x in m.recall(records,'marker100')],['record-0004'])
    def test_fts_injection_is_literal(self):
        row=record(1,'hotel trip')
        for q in ['" OR *','NEAR(hotel trip)','hotel); DROP TABLE recall;--','🙂','{foo:bar}']:
            m.recall([row],q)
    def test_typed_commands_are_owner_only_and_idempotent(self):
        b=Mock();b.call.return_value={'id':'note-result','version':1}
        job={'id':'job-123456','source':'app','prompt':'Запомни decision: Не менять цену','lease':'lease'}
        self.assertIn('Сохранено',m.command_reply(b,job,[]));args=b.call.call_args.args[1];self.assertEqual(args['kind'],'decision');self.assertEqual(args['lease'],'lease')
        m.command_reply(b,job,[]);self.assertEqual(args['id'],b.call.call_args.args[1]['id'])
        b.reset_mock();self.assertIsNone(m.command_reply(b,{**job,'source':'briefing'},[]));b.call.assert_not_called()
    def test_candidates_exact_source_no_extra_model(self):
        b=Mock();j={'id':'job-123456','source':'telegram','lease':'lease','prompt':'Моя цель — 20 бронирований'}
        m.capture_candidate(b,j);args=b.call.call_args.args[1];self.assertEqual(args['content'],j['prompt']);self.assertEqual(args['action'],'candidate')
        b.reset_mock();m.capture_candidate(b,{**j,'source':'briefing'});m.capture_candidate(b,{**j,'prompt':'Моя цель — что?'});b.call.assert_not_called()
    def test_extractor_output_must_be_verbatim(self):
        b=Mock();j={'id':'job-123456','source':'telegram','lease':'lease','prompt':'/extract decision: Не менять стоимость услуг'}
        out=m.command_reply(b,j,[],lambda _:['Не менять стоимость услуг','fabricated answer'])
        self.assertIn('1',out);b.call.assert_called_once();self.assertEqual(b.call.call_args.args[1]['content'],'Не менять стоимость услуг')
    def test_shared_context_does_not_inject_legacy_or_control_response(self):
        p={'job':{'prompt':'маркер100'},'history':[{'prompt':'/memory candidates','answer':'old secret','status':'done'}],'memory':[{'content':'legacy secret'}],'typedMemory':[record(1,'маркер100')],'snapshot':{}}
        _,h=shared_business.answer_context(p,['old local secret']);s=json.dumps(h,ensure_ascii=False);self.assertNotIn('secret',s);self.assertIn('маркер100',s)

    def test_migration_backup_and_owner_scope(self):
        import sqlite3
        from contextlib import closing
        from founder_jarvis.memory_migrate import backup,load_records
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/'jobs.sqlite3'
            with closing(sqlite3.connect(db)) as c:
                c.executescript("CREATE TABLE memory(id INTEGER, chat INTEGER, text TEXT); CREATE TABLE jobs(id INTEGER, chat INTEGER, mode TEXT, state TEXT, prompt TEXT); INSERT INTO memory VALUES(1,7,'owner note'),(2,8,'other note'); INSERT INTO jobs VALUES(3,7,'chat','done','owner question'),(4,8,'chat','done','other question');")
                c.commit()
            a=load_records(db,7);self.assertEqual(len(a),1);self.assertEqual(a,load_records(db,7));self.assertEqual(len(load_records(db,7,True)),2)
            self.assertNotEqual(a[0]['id'],load_records(db,8)[0]['id'])
            copy=backup(db,Path(tmp)/'backups');self.assertEqual(copy.stat().st_mode & 0o777,0o600)
            with closing(sqlite3.connect(copy)) as c:self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_multi_sentence_capture_bounded_and_verbatim(self):
        b=Mock();text='Привет. Моя цель — 20 поездок. Мы решили сохранить комиссию. Наш план — проверить спрос. Моя задача — ещё одна.'
        m.capture_candidate(b,{'source':'app','id':'job-123456','lease':'lease','prompt':text})
        self.assertEqual(b.call.call_count,3)
        for call in b.call.call_args_list:self.assertIn(call.args[1]['content'],text);self.assertEqual(call.args[1]['action'],'candidate')
