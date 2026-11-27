import datetime as dt, io, logging, os, sqlite3, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from founder_jarvis import operations
from founder_jarvis.runtime import Store
from founder_jarvis.shared_business import Bridge

class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.data=self.root/'data';self.data.mkdir();self.dest=self.root/'backups'
        for name in operations.DBS:
            with sqlite3.connect(self.data/name) as d:d.execute('CREATE TABLE sample(x)');d.execute('INSERT INTO sample VALUES(42)')
        (self.data/operations.PREF).write_text('{"language":"ru"}')
    def test_backup_restore(self):
        snap=operations.snapshot(self.data,self.dest);m=operations.verify(snap);self.assertEqual(len(m['files']),4)
        restored=operations.restore_to(snap,self.root/'restore')
        for name in operations.DBS:
            with sqlite3.connect(restored/name) as db:self.assertEqual(db.execute('SELECT x FROM sample').fetchone()[0],42)
        with self.assertRaises(RuntimeError):operations.restore_to(snap,restored)
    def test_corrupt_backup_rejected(self):
        snap=operations.snapshot(self.data,self.dest);(snap/operations.PREF).write_text('changed')
        with self.assertRaises(RuntimeError):operations.restore_to(snap,self.root/'restore')
        self.assertFalse((self.root/'restore').exists())
    def test_daily_retention(self):
        now=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)
        for day in range(10):
            stamp=now+dt.timedelta(days=day)
            self.assertTrue(operations.daily_backup(self.data,self.dest,stamp));self.assertIsNone(operations.daily_backup(self.data,self.dest,stamp))
        self.assertEqual(len(list(self.dest.glob('snapshot-*'))),7)
    def test_wal_backup(self):
        p=self.data/operations.DBS[0];db=sqlite3.connect(p)
        try:
            db.execute('PRAGMA journal_mode=WAL');db.execute('INSERT INTO sample VALUES(43)');db.commit()
            snap=operations.snapshot(self.data,self.dest)
            with sqlite3.connect(snap/p.name) as copy:self.assertEqual(copy.execute('SELECT count(*) FROM sample').fetchone()[0],2)
        finally:db.close()
    def test_corrupt_local(self):
        (self.data/operations.DBS[0]).write_bytes(b'bad')
        self.assertEqual(operations.check_local(self.data)[operations.DBS[0]],'corrupt')
    def test_no_secret_in_trace(self):
        secret='123456789:abcdefghijk'; key='a'*64
        with patch.dict(os.environ,{'TELEGRAM_BOT_TOKEN':secret}):
            try:raise ValueError('https://api.telegram.org/bot'+secret+' '+key)
            except ValueError:
                import sys
                rec=logging.LogRecord('test',logging.ERROR,'',0,'Error Bearer '+key,(),sys.exc_info());text=operations.PrivateFormatter().format(rec)
            self.assertNotIn(secret,text);self.assertNotIn(key,text)
    def test_owner_local_queue(self):
        s=Store(self.root/'queue.sqlite3')
        try:
            s.add(1,'private','chat',False,1);s.add(2,'current','chat',False,2)
            self.assertEqual(s.next(2)['chat'],2);self.assertIsNone(s.next(2));self.assertEqual(s.next(1)['chat'],1)
        finally:s.db.close()
    def test_finish_retry_same_payload(self):
        b=Bridge('a'*64);payload={'id':'abc','answer':'ok'}
        with patch.object(b,'call',side_effect=[RuntimeError('Backend unavailable'),{'ok':True}]) as fn:
            self.assertEqual(b.finish(payload),{'ok':True});self.assertEqual(fn.call_count,2);self.assertEqual(fn.call_args_list[0],fn.call_args_list[1])
        with patch.object(b,'call',side_effect=RuntimeError('HTTP 409 LEASE_LOST')) as fn:
            with self.assertRaises(RuntimeError):b.finish(payload)
            self.assertEqual(fn.call_count,1)
    def test_simulated_72h_with_restarts(self):
        from founder_jarvis import autonomy
        p=self.root/'longrun.sqlite3';start=dt.datetime(2026,11,24,0,tzinfo=autonomy.ZONE)
        ledger=autonomy.Ledger(p);notices=[];research=[]
        try:
            for i in range(72*60):
                now=start+dt.timedelta(minutes=i)
                if i%137==0:ledger.close();ledger=autonomy.Ledger(p)
                ledger.plan(now);job=ledger.claim(now)
                if job:
                    if job['kind'].startswith('research'):research.append(job['id'])
                    ledger.complete(job,{'text':'test fixture'},now,job['kind']=='morning')
                n=ledger.claim_notice(now)
                if n: notices.append(n['id']);ledger.notice_done(n['id'],True,now)
            self.assertEqual(len(notices),3);self.assertEqual(len(set(notices)),3)
            self.assertEqual(len(research),6);self.assertEqual(len(set(research)),6)
            self.assertEqual(ledger.status(),{'done':12})
        finally:ledger.close()
    def test_doctor_does_not_return_exception_text(self):
        from founder_jarvis.macos.doctor import run_check
        out={}
        def failure():raise ValueError('secret string')
        run_check('network',failure,out)
        self.assertEqual(out,{'network':{'status':'error','type':'ValueError'}})
