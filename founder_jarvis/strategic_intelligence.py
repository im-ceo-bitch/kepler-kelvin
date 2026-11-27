"""Deterministic interpretation of bounded backend aggregates.
No model can create metrics, authorize decisions, or change business data.
All proposals are advisory. Owner-approved decisions reuse canonical typed memory.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import re
from founder_jarvis.persistent_memory import eligible
from founder_jarvis.research_evidence import validate_report, public_url, host_allowed, TOPICS

UTC=dt.timezone.utc
NAMES={'bookingCohort':'Заявки на бронирование','careCohort':'Заявки Care','appSessions':'Сессии приложения','careDue':'Заявки Care с истёкшим сроком ответа'}

def time_value(s):
    try:
        d=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
        return d.astimezone(UTC) if d.tzinfo else None
    except (AttributeError,ValueError,TypeError):return None

def integer(v):return type(v) is int and 0<=v<=9_007_199_254_740_991

def pair(n,d):return {'numerator':n,'denominator':d,'percent':round(100*n/d,1) if d else None} if integer(n) and integer(d) and n<=d else None

def compare(current,previous):
    if not integer(current) or not integer(previous):return None
    return {'current':current,'previous':previous,'delta':current-previous,'changePercent':round((current-previous)*100/previous,1) if previous else None}

def report(snapshot,now=None):
    now=now or dt.datetime.now(UTC)
    s=snapshot.get('strategy') if isinstance(snapshot,dict) else None
    unavailable={'available':False,'reason':'Нет актуального проверяемого среза стратегической аналитики.','metrics':{},'recommendations':[]}
    if not isinstance(s,dict) or s.get('version')!=1:return unavailable
    at=time_value(s.get('asOf')); w=s.get('windows',{}); current=w.get('current',{}) if isinstance(w,dict) else {}; previous=w.get('previous',{}) if isinstance(w,dict) else {}
    if not isinstance(w,dict) or not isinstance(current,dict) or not isinstance(previous,dict):return unavailable
    c0,c1,p0,p1=[time_value(x) for x in (current.get('start'),current.get('end'),previous.get('start'),previous.get('end'))]
    if not all((at,c0,c1,p0,p1)) or c1!=at or p1!=c0 or c1-c0!=dt.timedelta(days=7) or p1-p0!=dt.timedelta(days=7) or not dt.timedelta(minutes=-2)<=now-at<=dt.timedelta(minutes=30):return unavailable
    raw=s.get('metrics',{}); out={}; rec=[]
    if not isinstance(raw,dict):return unavailable
    def rows(key):
        m=raw.get(key,{})
        if not isinstance(m,dict):return None
        return m.get('rows') if m.get('available') is True and isinstance(m.get('rows'),list) else None
    def cohort(key,fields):
        rr=rows(key)
        if rr is None:return None
        result={p:{f:0 for f in fields} for p in ('current','previous')};seen=set()
        for r in rr:
            if not isinstance(r,dict) or r.get('period') not in result or r['period'] in seen or any(not integer(r.get(f)) for f in fields):return None
            seen.add(r['period']);result[r['period']]={f:r[f] for f in fields}
            if any(r[f]>r['total'] for f in fields):return None
        return result
    def proposal(id,title,reason,measure,kpi,baseline):
        rec.append({'id':id,'action':title,'reason':reason,'measure':measure,'kpi':kpi,'baseline':baseline,'status':'proposal','attribution':'Изменение показателя не доказывает причинный эффект.'})
    b=cohort('bookingCohort',('total','active','cancelled','pending'))
    if b and all(r['active']+r['cancelled']+r['pending']<=r['total'] for r in b.values()):
        c,p=b['current'],b['previous'];out['bookingCohort']={'counts':b,'change':compare(c['total'],p['total']),'activeShare':pair(c['active'],c['total']),'cancelledShare':pair(c['cancelled'],c['total']),'definition':'Статусы созданных за окно заявок на момент снимка; не оплаченные продажи и не конверсия.'}
        if c['total']>=5 and c['pending']>=3 and c['pending']*2>=c['total']:
            proposal('pending','Проверить вручную заявки, ожидающие наличия или оплаты.',f"{c['pending']} из {c['total']} новых заявок всё ещё ожидают проверки/оплаты. Причина неизвестна.",'Через неделю сравнить количество новых заявок в ожидании; проверить причины вручную.','bookingPending',c['pending'])
    care=cohort('careCohort',('total','familyKnown','family'))
    if care and all(r['family']<=r['familyKnown']<=r['total'] for r in care.values()):
        c,p=care['current'],care['previous'];out['careCohort']={'counts':care,'change':compare(c['total'],p['total']),'partyShare':pair(c['family'],c['familyKnown']),'definition':'Группа от 3 путешественников, не доказанное родство; записи заявок, не уникальные клиенты.'}
        if c['familyKnown']>=5 and c['family']>=3 and c['family']*2>=c['familyKnown']:
            proposal('family','Протестировать публикацию о поездке на 3–4 человек с прозрачным расчётом.',f"{c['family']} из {c['familyKnown']} заявок с известным составом — группы от трёх человек; гипотеза о семейном спросе.",'Через 7 дней сравнить новые заявки групп от трёх; отдельно спросить об источнике обращения.','careFamily',c['family'])
    for key,allowed,base in [('bookingOrigins',{'TAS','FEG','NMA','AZN','SKD','BHK','KSQ','TMJ','UGC','NCU','other'},b if 'bookingCohort' in out else None),('bookingTiers',{'economy','standard','comfort','luxury','other'},b if 'bookingCohort' in out else None),('careMonths',None,care if 'careCohort' in out else None),('careHotelClasses',{'3','4','5','other'},care if 'careCohort' in out else None)]:
        rr=rows(key)
        if rr is None or base is None:continue
        dist={'current':{},'previous':{}};valid=True
        for r in rr:
            if not isinstance(r,dict):valid=False;break
            d=r.get('dimension');p=r.get('period');n=r.get('total')
            if p not in dist or not isinstance(d,str) or not integer(n) or d in dist[p] or (d not in allowed if allowed is not None else not (d=='other' or re.fullmatch(r'20\d{2}-(?:0[1-9]|1[0-2])',d))):valid=False;break
            if key=='careMonths' and (not integer(r.get('family')) or r['family']>n):valid=False;break
            dist[p][d]={'count':n,**({'group3Plus':r['family']} if key=='careMonths' else {})}
        if not valid or any(sum(v['count'] for v in dist[p].values())!=base[p]['total'] for p in dist):continue
        out[key]={'counts':dist,'denominator':{p:base[p]['total'] for p in dist}}
        if key=='careMonths' and care['current']['total']>=5:
            candidates=[(v['group3Plus'],d,v['count']) for d,v in dist['current'].items() if d!='other' and d>=now.strftime('%Y-%m') and v['group3Plus']>=3 and v['group3Plus']*2>=care['current']['total']]
            if candidates:
                n,d,total=max(candidates)
                proposal('month-'+d,'Проверить интерес к поездкам для группы 3+ на '+d+'.',f'{n} заявок групп 3+ на этот месяц из {care["current"]["total"]} всех новых заявок Care (в месяце всего {total}). Это намерение, не бронь.','Через неделю сравнить новые заявки групп 3+ на тот же месяц.','careMonth:'+d,n)
    a=cohort('appSessions',('total','checkout','submitted','both','errors','crashes'))
    if a and all(r['both']<=min(r['checkout'],r['submitted']) for r in a.values()):
        c,p=a['current'],a['previous'];out['appSessions']={'counts':a,'change':compare(c['total'],p['total']),'checkoutWithSubmit':pair(c['both'],c['checkout']),'definition':'Сессии с обоими событиями, не последовательная воронка и не оплаченные заказы.'}
        if c['checkout']>=10 and c['both']*2<c['checkout']:
            proposal('checkout','Проверить сценарий оформления на реальном устройстве.',f"Лишь {c['both']} из {c['checkout']} сессий с началом оформления содержат также событие отправки заявки. Возможны пропуски телеметрии.",'Сравнить долю сессий с обоими событиями в следующем непересекающемся окне.','checkoutBoth',pair(c['both'],c['checkout']))
    due=rows('careDue')
    if due and len(due)==1 and isinstance(due[0],dict) and integer(due[0].get('due')) and integer(due[0].get('total')) and due[0]['due']<=due[0]['total']:
        out['careDue']={'due':due[0]['due'],'total':due[0]['total']}
        if due[0]['due']>=1:proposal('care-due','Проверить просроченные обращения Care.',f"{due[0]['due']} из {due[0]['total']} открытых записей прошли срок ответа; контакт вне системы неизвестен.",'После ручной проверки сверить число открытых просроченных записей.','careDue',due[0]['due'])
    for key,metric in out.items():
        metric['source']=str(raw[key].get('source',''))[:100] if key!='careDue' else 'HOTELS_DB.iumrah_care_package_requests'
    priority={'care-due':0,'pending':1,'checkout':4,'family':3}
    rec.sort(key=lambda r:(priority.get(r['id'],2),r['id']))
    return {'available':bool(out),'asOf':s['asOf'],'windows':w,'metrics':out,'recommendations':rec,'limitations':['Нет проверенной выручки, прибыли, причин отказов и атрибуции рекламы.','Не объединять заявки Care, бронирования и сессии. Периоды — 7 суток UTC, статусы текущие.','Пороговые сигналы — эвристики для проверки, не статистически доказанные выводы.']}

def kpi(report,key):
    m=report['metrics']
    try:
        if key=='careFamily':return m['careCohort']['counts']['current']['family']
        if key=='bookingPending':return m['bookingCohort']['counts']['current']['pending']
        if key=='careDue':return m['careDue']['due']
        if key=='checkoutBoth':
            v=m['appSessions']['checkoutWithSubmit'];return v if v and v['denominator'] else None
        if key.startswith('careMonth:'):
            return m['careMonths']['counts']['current'].get(key.split(':',1)[1],{'group3Plus':0})['group3Plus']
    except KeyError:pass
    return None

def latest_decisions(records):
    """Only explicit owner records; newest decision per proposal wins."""
    out={}
    for record in sorted(eligible(records),key=lambda r:(r.get('created_at',r.get('updated_at',0)),r['id']),reverse=True):
        if record['kind']!='decision' or not record['id'].startswith('strategy-'):continue
        try:
            d=json.loads(record['content']); ident=d['proposal'];base=d['baseline']
            if d['schema']!=1 or d['status'] not in ('accept','defer','reject') or not isinstance(ident,str) or not re.fullmatch(r'(?:family|pending|checkout|care-due|month-20\d{2}-(?:0[1-9]|1[0-2]))',ident):continue
            expected={'family':'careFamily','pending':'bookingPending','checkout':'checkoutBoth','care-due':'careDue'}.get(ident,'careMonth:'+ident[6:])
            if d['kpi']!=expected or not time_value(d['baselineEnd']):continue
            if expected=='checkoutBoth':
                if not isinstance(base,dict) or pair(base.get('numerator'),base.get('denominator'))!=base or not base.get('denominator'):continue
            elif not integer(base):continue
            if ident not in out:out[ident]=d
        except (ValueError,TypeError,KeyError,AttributeError):continue
    return out


def decision_reviews(records,analysis,now=None):
    now=now or dt.datetime.now(UTC);out=[]
    for ident,d in latest_decisions(records).items():
        if d['status']!='accept':continue
        end=time_value(d['baselineEnd']);current_start=time_value(analysis.get('windows',{}).get('current',{}).get('start'));value=kpi(analysis,d['kpi'])
        ready=value is not None and now>=end+dt.timedelta(days=7) and (d['kpi']=='careDue' or (current_start is not None and current_start>=end))
        out.append({'proposal':ident,'baseline':d['baseline'],'current':value if ready else None,'state':'ready_for_review' if ready else 'awaiting_comparable_data','baselineEnd':d['baselineEnd'],'note':'Решение владельца, выполнение и причинный эффект не подтверждены.'})
    return out[:10]


def fresh_proposals(analysis,records):
    statuses=latest_decisions(records)
    return [r for r in analysis.get('recommendations',[]) if r['id'] not in statuses]

def render(analysis,records=()):
    if not analysis.get('available'):return 'Стратегическая аналитика пока недоступна: нет актуального снимка backend.'
    lines=['iumrah · последние 7 суток (UTC), на '+analysis['asOf'][:16]+'Z']
    for key in ('bookingCohort','careCohort','appSessions'):
        if key not in analysis['metrics']:continue
        x=analysis['metrics'][key]['change'];lines.append(f"{NAMES[key]}: {x['current']} (предыдущие 7 суток: {x['previous']}).")
    statuses=latest_decisions(records)
    for r in analysis['recommendations'][:5]:lines+=['',r['action'],r['reason'],r['measure'],'ID: '+r['id']+(' · ранее: '+statuses[r['id']]['status'] if r['id'] in statuses else '')]
    if not analysis['recommendations']:lines.append('Нет сигнала выше порогов для конкретной рекомендации.')
    lines.append('Это анализ записей, не выручка и не доказательство конверсии.')
    return '\n'.join(lines)

def command(bridge,job,payload):
    text=job['prompt'].strip()
    # Commands work in both Telegram and the app; optional Telegram bot suffix.
    text=re.sub(r'^(/(?:strategy|decisions|decision))@[A-Za-z0-9_]+(?= |$)',r'\1',text)
    if job.get('source') not in ('telegram','app'):return None
    if text not in ('/strategy','/decisions','/decision') and not text.startswith('/decision '):return None
    analysis=report(payload.get('snapshot',{}));records=payload.get('typedMemory',[])
    if text=='/strategy':return render(analysis,records)
    if text=='/decisions':
        rev=decision_reviews(records,analysis)
        return '\n'.join(f"{r['proposal']}: {'можно сверить' if r['state']=='ready_for_review' else 'ждём сопоставимые данные'}; базовый показатель {r['baseline']}; текущий {r['current'] if r['current'] is not None else 'недоступен'}. {r['note']}" for r in rev) or 'Нет принятых стратегических решений для сверки.'
    m=re.fullmatch(r'/decision ([a-z0-9-]{1,60}) (accept|defer|reject)',text)
    if not m:return '/decision ID accept|defer|reject — записать твоё решение, не выполнить операцию.'
    # One canonical memory record per explicit owner message; no automatic approval.
    ident='strategy-'+hashlib.sha256(job['id'].encode()).hexdigest()[:32]
    old=next((x for x in eligible(records) if x['id']==ident),None)
    if old:return 'Решение уже сохранено. Операций не выполнял.'
    r=next((x for x in analysis['recommendations'] if x['id']==m[1]),None)
    if r:
        d={'schema':1,'proposal':r['id'],'status':m[2],'kpi':r['kpi'],'baseline':r['baseline'],'baselineEnd':analysis['asOf'],'action':r['action']}
    elif m[2] in ('reject','defer'):
        # A decision may be withdrawn even when the initial signal disappeared.
        old=latest_decisions(records).get(m[1])
        if old is None:return 'Решение не найдено. Посмотри /strategy.'
        d={**old,'status':m[2]}
    else:return 'Рекомендация больше не подтверждается текущим снимком. Посмотри /strategy.'
    bridge.call('records',{'action':'save','id':ident,'kind':'decision','content':json.dumps(d,ensure_ascii=False),'job':job['id'],'lease':job['lease']})
    return 'Решение сохранено. Никаких бизнес-операций не выполнял. '+('Через 7 дней можно сверить показатель в /decisions.' if m[2]=='accept' else '')


def research_context(reports,analysis,now=None):
    """Select dated, previously validated evidence; never claim independent verification.
    No new external fetch or model invocation, no business data leaves for search.
    """
    now=now or dt.datetime.now(UTC);result=[];seen=set()
    matches={'family':{'demand','customer','marketing','market'},'checkout':{'platforms','customer'},'pending':{'customer','risks'},'care-due':{'customer'}}
    for item in reports[:10]:
        try:
            sources=item['sources'];validated=validate_report(item['report'],sources);by_id={s['id']:s for s in sources}
            for f in validated['findings']:
                src=by_id[f['source_id']];at=time_value(src['observed_at']);topic=src['topic']
                if not at or not dt.timedelta(0)<=now-at<=dt.timedelta(days=7) or src['id'] in seen or topic not in TOPICS or not public_url(src['url']) or not host_allowed(src['url'],topic):continue
                related=[r['id'] for r in analysis.get('recommendations',[]) if topic in matches.get(r['id'],{'market','demand','customer'} if r['id'].startswith('month-') else set())]
                seen.add(src['id']);result.append({'source_id':src['id'],'url':src['url'],'observedAt':src['observed_at'],'quote':f['quote'],'hypothesis':f['implication'],'relatedProposals':related,'verification':'search_excerpt_only; topical relationship, not proof of the proposal'})
                if len(result)>=5:return result
        except (ValueError,TypeError,KeyError,AttributeError):continue
    return result
