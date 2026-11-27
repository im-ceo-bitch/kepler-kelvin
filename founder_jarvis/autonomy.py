"""Business-specific policy around upstream TaskScheduler.
One persistent event ledger. No continuous inference loop, no autonomous writes
outside Kelvin's own journal. All research, delivery and retries have bounds.
"""
from __future__ import annotations
import asyncio
import datetime as dt
import json
import logging
import sqlite3
import threading
from zoneinfo import ZoneInfo
from founder_jarvis import strategic_intelligence
from founder_jarvis.research_evidence import TOPICS, GENERAL_TOPICS, WATCHLIST, validate_report, render_report

log=logging.getLogger('kelvin.autonomy')
ZONE=ZoneInfo('Asia/Tashkent')
MAX_ATTEMPTS=2
MAX_RESEARCH_ATTEMPTS_PER_DAY=4
# All windows local. Expired slots are never replayed after a long shutdown.
SLOTS=(('morning',8,11),('research-a',12,16),('research-b',16,20),('evening',21,23))
TOPIC_LABELS={'market':'Рынок умры','competitors':'Конкуренты','marketing':'Маркетинг','platforms':'Туристические платформы','demand':'Спрос','hajj':'Хадж и умра','customer':'Поведение клиентов','social':'Социальные сети','risks':'Риски'}

def slots(now):
    day=now.date().isoformat(); n=now.date().toordinal()
    for kind,start,end in SLOTS:
        if start<=now.hour<end:
            topic=GENERAL_TOPICS[(n-n//3)%len(GENERAL_TOPICS)] if kind=='research-a' else list(WATCHLIST)[n%len(WATCHLIST)] if kind=='research-b' else ''
            yield (f'kelvin-auto-{day}-{kind}',kind,topic,day,now.timestamp(),now.replace(hour=end,minute=0,second=0,microsecond=0).timestamp())

class Ledger:
    def __init__(self,path):
        self.db=sqlite3.connect(path);self.db.row_factory=sqlite3.Row
        self.db.executescript('''PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS auto_jobs(id TEXT PRIMARY KEY,kind TEXT,topic TEXT,day TEXT,due REAL,expires REAL,state TEXT DEFAULT 'queued',attempts INTEGER DEFAULT 0,result TEXT,delivery TEXT DEFAULT 'none',error TEXT);
        CREATE TABLE IF NOT EXISTS auto_audit(seq INTEGER PRIMARY KEY,job TEXT,action TEXT,at REAL);
        CREATE TABLE IF NOT EXISTS auto_control(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS auto_sources(id TEXT PRIMARY KEY,topic TEXT,observed REAL,data TEXT);
        CREATE TABLE IF NOT EXISTS auto_signal(key TEXT PRIMARY KEY,value INTEGER,at REAL,streak INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS auto_budget(day TEXT PRIMARY KEY,used INTEGER NOT NULL);
        ''')
        # Only research/reads may retry. Never resend an ambiguous Telegram send.
        with self.db:
            self.db.execute("UPDATE auto_jobs SET state='queued' WHERE state='running' AND attempts<?",(MAX_ATTEMPTS,))
            self.db.execute("UPDATE auto_jobs SET state='failed',error='interrupted' WHERE state='running'")
            self.db.execute("UPDATE auto_jobs SET delivery='uncertain' WHERE delivery='sending'")
    def close(self):self.db.close()
    def _audit(self,id,action,now):self.db.execute('INSERT INTO auto_audit(job,action,at) VALUES(?,?,?)',(id,action,now))
    def setting(self,key,default):
        r=self.db.execute('SELECT value FROM auto_control WHERE key=?',(key,)).fetchone();return r[0] if r else default
    def set(self,key,value):
        with self.db:
            self.db.execute('INSERT INTO auto_control VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(value)))
            if key=='enabled' and str(value)=='0':
                self.db.execute("UPDATE auto_jobs SET delivery='expired' WHERE delivery='pending'")
    def plan(self,now):
        with self.db:
            self.db.execute("UPDATE auto_jobs SET state='expired' WHERE state='queued' AND expires<=?",(now.timestamp(),))
            for item in slots(now):
                # One bounded adaptive slot every third day, only among approved public topics.
                if item[1]=='research-a' and now.date().toordinal()%3==0:
                    previous=self.last_research(1)
                    suggestion=previous[0]['report'].get('next_topic') if previous else None
                    if suggestion in GENERAL_TOPICS and suggestion!=previous[0]['sources'][0]['topic']:
                        item=(*item[:2],suggestion,*item[3:])
                if self.db.execute('INSERT OR IGNORE INTO auto_jobs(id,kind,topic,day,due,expires) VALUES(?,?,?,?,?,?)',item).rowcount:self._audit(item[0],'queued',now.timestamp())
    def claim(self,now):
        ts=now.timestamp(); day=now.date().isoformat()
        with self.db:
            row=self.db.execute("SELECT * FROM auto_jobs WHERE state='queued' AND due<=? AND expires>? AND attempts<? ORDER BY CASE WHEN kind='morning' THEN 0 WHEN kind='evening' THEN 1 ELSE 2 END,due LIMIT 1",(ts,ts,MAX_ATTEMPTS)).fetchone()
            if not row:return None
            if row['kind'].startswith('research'):
                self.db.execute('INSERT OR IGNORE INTO auto_budget VALUES(?,0)',(day,))
                if not self.db.execute('UPDATE auto_budget SET used=used+1 WHERE day=? AND used<?',(day,MAX_RESEARCH_ATTEMPTS_PER_DAY)).rowcount:
                    self.db.execute("UPDATE auto_jobs SET state='failed',error='budget' WHERE id=?",(row['id'],));return None
            self.db.execute("UPDATE auto_jobs SET state='running',attempts=attempts+1 WHERE id=?",(row['id'],));self._audit(row['id'],'claimed',ts)
            return dict(row)|{'attempts':row['attempts']+1}
    def failed(self,job,now):
        ts=now.timestamp();retry=job['attempts']<MAX_ATTEMPTS and ts+900<job['expires']
        with self.db:
            self.db.execute("UPDATE auto_jobs SET state=?,due=?,error='research_or_transport_failed' WHERE id=? AND state='running'",('queued' if retry else 'failed',ts+900,job['id']));self._audit(job['id'],'retry' if retry else 'failed',ts)
    def complete(self,job,result,now,delivery=False):
        ts=now.timestamp()
        with self.db:
            for source in result.get('sources',[]):
                self.db.execute('INSERT OR IGNORE INTO auto_sources VALUES(?,?,?,?)',(source['id'],source['topic'],ts,json.dumps(source,ensure_ascii=False)))
            self.db.execute("UPDATE auto_jobs SET state='done',result=?,delivery=?,error=NULL WHERE id=? AND state='running'",(json.dumps(result,ensure_ascii=False),'pending' if delivery and self.setting('enabled','1')=='1' and ts<job['expires'] else 'none',job['id']));self._audit(job['id'],'done',ts)
    def last_research(self,limit=3):
        return [json.loads(r[0]) for r in self.db.execute("SELECT result FROM auto_jobs WHERE state='done' AND kind LIKE 'research-%' AND json_extract(result,'$.report') IS NOT NULL ORDER BY due DESC LIMIT ?",(limit,))]
    def research_since_briefing(self):
        r=self.db.execute("SELECT COALESCE(MAX(due),0) FROM auto_jobs WHERE kind='morning' AND state='done'").fetchone()
        return [json.loads(x[0]) for x in self.db.execute("SELECT result FROM auto_jobs WHERE state='done' AND kind LIKE 'research-%' AND json_extract(result,'$.report') IS NOT NULL AND due>? ORDER BY due DESC LIMIT 3",(r[0],))]
    def prior_ids(self,topic):return [r[0] for r in self.db.execute('SELECT id FROM auto_sources WHERE topic=? ORDER BY observed DESC LIMIT 50',(topic,))]
    def pending_publish(self,now):
        # Publish every report at most once per canonical id (backend idempotency).
        return [dict(r) for r in self.db.execute("SELECT * FROM auto_jobs WHERE state='done' AND kind IN ('morning','evening','important','critical','research-a','research-b') AND COALESCE(json_extract(result,'$.published'),0)=0 AND COALESCE(json_extract(result,'$.publish_attempts'),0)<5 AND COALESCE(json_extract(result,'$.publish_after'),0)<=? ORDER BY due LIMIT 3",(now.timestamp(),))]
    def publish_failed(self,id,result,now):
        result['publish_attempts']=result.get('publish_attempts',0)+1
        result['publish_after']=now.timestamp()+900
        with self.db:
            self.db.execute('UPDATE auto_jobs SET result=? WHERE id=?',(json.dumps(result,ensure_ascii=False),id));self._audit(id,'archive_retry' if result['publish_attempts']<5 else 'archive_failed',now.timestamp())
    def published(self,id,result):
        result['published']=1
        with self.db:self.db.execute('UPDATE auto_jobs SET result=? WHERE id=?',(json.dumps(result,ensure_ascii=False),id))
    def claim_notice(self,now):
        ts=now.timestamp()
        with self.db:
            # Do not replay old morning/alert notices. Archive is still retained.
            self.db.execute("UPDATE auto_jobs SET delivery='expired' WHERE delivery='pending' AND expires<=?",(ts,))
            r=self.db.execute("SELECT * FROM auto_jobs WHERE delivery='pending' AND expires>? AND (kind!='important' OR ?) ORDER BY CASE WHEN kind='critical' THEN 0 WHEN kind='important' THEN 1 ELSE 2 END,due LIMIT 1",(ts,8<=now.hour<22)).fetchone()
            if not r:return None
            self.db.execute("UPDATE auto_jobs SET delivery='sending' WHERE id=?",(r['id'],));self._audit(r['id'],'send_started',ts);return dict(r)
    def notice_done(self,id,success,now):
        with self.db:self.db.execute('UPDATE auto_jobs SET delivery=? WHERE id=?',('sent' if success else 'uncertain',id));self._audit(id,'sent' if success else 'uncertain',now.timestamp())
    def _event(self,id,kind,day,ts,text,expires):
        result={'text':text,'published':0}
        if self.db.execute("INSERT OR IGNORE INTO auto_jobs(id,kind,topic,day,due,expires,state,result,delivery) VALUES(?,?,?,?,?,?,'done',?,'pending')",(id,kind,'',day,ts,expires,json.dumps(result,ensure_ascii=False))).rowcount:
            self._audit(id,'signal',ts);return True
        return False
    def observe(self,snapshot,now):
        """Deterministic signals only. Missing fields are not evidence of outages.
        Critical: previously available bookings aggregate fails twice. Re-arm
        after recovery; at most one such alert per local day. Ordinary data is
        kept in the next digest. No model can assign a critical priority.
        """
        ts=now.timestamp();day=now.date().isoformat();created=False
        metrics=snapshot.get('data',{}) if isinstance(snapshot,dict) else {}
        availability=metrics.get('bookingsByStatus',{}).get('available')
        with self.db:
            old=self.db.execute("SELECT * FROM auto_signal WHERE key='bookings_available'").fetchone()
            if availability is True:
                self.db.execute("INSERT INTO auto_signal VALUES('bookings_available',1,?,0) ON CONFLICT(key) DO UPDATE SET value=1,at=excluded.at,streak=0",(ts,))
            elif availability is False and old and 0<ts-old['at']<=7200 and old['value']==1:
                streak=old['streak']+1
                self.db.execute("UPDATE auto_signal SET at=?,streak=? WHERE key='bookings_available'",(ts,streak))
                if streak>=2:
                    self.db.execute("UPDATE auto_signal SET value=0 WHERE key='bookings_available'")
                    created=self._event(f'kelvin-auto-{day}-availability','critical',day,ts,'Не удаётся получить ранее доступные данные о бронированиях: две проверки backend подряд завершились без этого показателя. Проверь доступность базы. Это не подтверждает сбой всего приложения.',ts+3600) or created
            n=unread(snapshot)
            if n is None:return created
            old=self.db.execute("SELECT * FROM auto_signal WHERE key='unread'").fetchone()
            streak=0
            if old and 0<ts-old['at']<=7200 and n>=5:
                streak=old['streak']+1 if old['streak'] or n-old['value']>=3 else 0
            self.db.execute("INSERT INTO auto_signal VALUES('unread',?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,at=excluded.at,streak=excluded.streak",(n,ts,streak))
            if streak>=2:
                created=self._event(f'kelvin-auto-{day}-unread','important',day,ts,f'В iumrah накопилось {n} непрочитанных обращений поддержки (по данным backend). Проверь очередь сегодня.',ts+3600) or created
                self.db.execute("UPDATE auto_signal SET streak=0 WHERE key='unread'")
        return created
    def status(self):
        return dict(self.db.execute('SELECT state,COUNT(*) FROM auto_jobs GROUP BY state').fetchall())


def unread(snapshot):
    try:
        metric=snapshot['data']['supportThreads'];val=metric['rows'][0]['unread']
        if metric['available'] is True and type(val) is int and val>=0:return val
    except (KeyError,IndexError,TypeError):pass
    return None


def brief(kind,snapshot,reports,now):
    # Reports are recommendations only, not facts from the owner memory.
    # Use at most one recent research finding; no giant automatic voice report.
    lines=['Доброе утро.' if kind=='morning' else 'Итоги дня.']
    n=unread(snapshot)
    if n is not None:lines.append(f'В поддержке {n} непрочитанных обращений (снимок backend).')
    else:lines.append('Показатели поддержки сейчас недоступны.')
    analysis=strategic_intelligence.report(snapshot,now)
    new=strategic_intelligence.fresh_proposals(analysis,snapshot.get("strategicDecisions",[]))
    if new:
        r=new[0]
        lines.extend([r["reason"], "Предлагаю: "+r["action"], "Проверка: "+r["measure"]])
        return "\n".join(lines)[:900]
    if kind=='evening':
        reviews=strategic_intelligence.decision_reviews(snapshot.get('strategicDecisions',[]),analysis,now)
        ready=[r for r in reviews if r['state']=='ready_for_review']
        if ready:
            lines.append('Есть решение, для которого уже доступно сопоставимое окно: '+ready[0]['proposal']+'. Сверка — /decisions; факт выполнения не подтверждён.')
            return '\n'.join(lines)[:900]
    recent=None
    for item in reports:
        try:
            observed=dt.datetime.fromisoformat(item['sources'][0]['observed_at'])
            if dt.timedelta(0)<=now-observed<=dt.timedelta(days=2):recent=item;break
        except (KeyError,IndexError,ValueError,TypeError):continue
    if recent:
        report=recent['report'];lines.append('Предлагаю: '+report['recommendation'][:330]);lines.append('Проверка: '+report['measure'][:160]);src=next((s for s in recent['sources'] if s['id']==report['findings'][0]['source_id']),None)
        lines.append('Основание — поисковая выдержка, требует проверки.'+((' '+src['url']) if src and len(src['url'])<=180 else ''))
    elif n and n>=5:lines.append('Приоритет: проверить непрочитанные обращения.')
    else:lines.append('Нет нового исследования с доступными источниками; вывод о рынке пока не делаю.')
    return '\n'.join(lines)[:900]

class Service:
    def __init__(self,ledger,bridge,research,send,lock,clock=None):
        self.ledger=ledger;self.bridge=bridge;self.research=research;self.send=send;self.lock=lock;self.clock=clock or (lambda:dt.datetime.now(ZONE));self.task=None;self.stopping=False;self.cancel_event=threading.Event()
    def kick(self):
        # Scheduler callback is fast; the actual work is a single tracked task.
        if not self.stopping and (self.task is None or self.task.done()):self.task=asyncio.create_task(self.tick())
    async def snapshot(self,strategy=False):
        if not self.bridge:return {}
        return (await asyncio.to_thread(self.bridge.call,'autonomy',{'action':'snapshot','strategy':strategy}))['snapshot']
    async def tick(self):
        try:await self._tick()
        except asyncio.CancelledError:raise
        except Exception as e:log.warning('Autonomy tick failed: %s',type(e).__name__)
    async def _tick(self):
        now=self.clock();l=self.ledger
        if l.setting('enabled','1')!='1':return
        l.plan(now)
        # One read every 30 minutes; failure is not a zero or a user-facing alert.
        if self.bridge and now.timestamp()-float(l.setting('last_poll','0'))>=1800:
            l.set('last_poll',now.timestamp())
            try:l.observe(await self.snapshot(),now)
            except Exception as e:log.warning('Signal snapshot failed: %s',type(e).__name__)
        # A confirmed critical signal should not wait behind background research.
        if l.db.execute("SELECT 1 FROM auto_jobs WHERE kind='critical' AND delivery='pending' AND expires>?",(self.clock().timestamp(),)).fetchone():
            await self.deliver_notice()
        # Don't compete with an active owner request. No background typing/status.
        if not self.lock.locked():
            async with self.lock:
                job=l.claim(self.clock())
                if job:
                    try:
                        if job['kind'].startswith('research'):
                            result=await asyncio.to_thread(self.research,job['topic'],l.prior_ids(job['topic']))
                            # Persist only validated evidence; no implicit owner-memory writes.
                            if result.get('report') is not None:
                                report=validate_report(result['report'],result['sources']);result={'report':report,'sources':result['sources'],'text':render_report(job['topic'],result['sources'],report)}
                                if job['topic'] in WATCHLIST:result['text']='Изменились доступные поисковые выдержки. Это не подтверждение изменения предложения.\n'+result['text']
                            else:
                                # A no-change observation is retained locally, never a new public claim.
                                result={'report':None,'sources':result['sources'],'text':result.get('text','Новых поисковых выдержек не обнаружено.'),'published':1}
                        else:
                            snap=await self.snapshot(strategy=True);result={'text':brief(job['kind'],snap,l.research_since_briefing() if job['kind']=='morning' else l.last_research(),self.clock()),'published':0}
                        l.complete(job,result,self.clock(),delivery=job['kind']=='morning')
                    except Exception as e:
                        l.failed(job,self.clock());log.warning('Autonomy job %s failed: %s',job['kind'],type(e).__name__)
        if self.stopping or l.setting('enabled','1')!='1':return
        if self.bridge:
            for row in l.pending_publish(self.clock()):
                try:
                    result=json.loads(row['result']);await asyncio.to_thread(self.bridge.call,'autonomy',{'action':'publish','id':row['id'],'kind':row['kind'],'text':result['text']});l.published(row['id'],result)
                except Exception:l.publish_failed(row['id'],result,self.clock()) # bounded retry, no user spam
        if self.stopping or l.setting('enabled','1')!='1':return
        await self.deliver_notice()
    async def deliver_notice(self):
        if self.stopping or self.ledger.setting('enabled','1')!='1':return
        l=self.ledger;row=l.claim_notice(self.clock())
        if row:
            ok=False
            try:await self.send(json.loads(row['result'])['text'][:900]);ok=True
            except Exception:pass
            finally:l.notice_done(row['id'],ok,self.clock())
    async def stop(self):
        self.stopping=True;self.cancel_event.set()
        if self.task:
            # Do not launch more work. Existing bounded subprocess may finish;
            # interrupted work is reclaimed from ledger on next service startup.
            try:await asyncio.wait_for(asyncio.shield(self.task),timeout=5)
            except asyncio.TimeoutError:
                self.task.cancel();await asyncio.gather(self.task,return_exceptions=True)
