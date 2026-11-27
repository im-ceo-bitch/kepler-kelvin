"""Scoped recall projection and explicit memory commands; no model writes.
Canonical records are supplied by the authenticated existing iumrah backend.
A transient FTS5 index is rebuilt from the current snapshot, so removed records
cannot survive in an on-disk cache. Native Rust index is optional, not assumed.
"""
import hashlib, json, re, sqlite3
from contextlib import closing

KINDS={'personal','business','episodic','decision','task','research'}
SECRET=re.compile(r'\b\d{6,}:[A-Za-z0-9_-]{20,}|sk-(?:ant-)?[A-Za-z0-9_-]{16,}|github_pat_[A-Za-z0-9_]+|gh[pousr]_[A-Za-z0-9_]+|\b[a-f0-9]{64}\b|-----BEGIN [A-Z ]*PRIVATE KEY-----',re.I)

def safe_text(s):
    return isinstance(s,str) and not SECRET.search(s)

def eligible(records):
    return [r for r in records if isinstance(r,dict) and r.get('kind') in KINDS and r.get('trust')=='owner' and not r.get('deleted') and isinstance(r.get('id'),str) and safe_text(r.get('content'))]

def query_words(query):
    # Quote all input; no FTS operators, wildcard expressions or SQL from model.
    # Prefix lookup helps RU/UZ inflected terms; exact numerals/IDs preserved.
    words=list(dict.fromkeys(re.findall(r'[^\W_]+',query.lower(),re.UNICODE)))
    return [w for w in words if len(w)>=3 and w not in {'что','как','это','меня','мои','мне','the','kelvin','келвин','какой','какие','расскажи','помнишь','remember'}][:24]

def recall(records, query, limit=12):
    records=eligible(records)
    if not records:return []
    words=query_words(query)
    matches=[]
    if words:
        with closing(sqlite3.connect(':memory:')) as db:
            db.execute("CREATE VIRTUAL TABLE recall USING fts5(content, tokenize='unicode61')")
            db.executemany('INSERT INTO recall(rowid,content) VALUES(?,?)',[(i+1,r['id']+' '+r['kind']+' '+r['content']) for i,r in enumerate(records)])
            q=' OR '.join('"'+w+'"*' for w in words)
            matches=[records[i-1] for (i,) in db.execute('SELECT rowid FROM recall WHERE recall MATCH ? ORDER BY bm25(recall),rowid LIMIT ?',(q,limit))]
    # Exact ID first; then relevant matches; then bounded recent owner decisions.
    exact=[r for r in records if r['id'] in query]
    decisions=sorted((r for r in records if r['kind']=='decision'),key=lambda r:(r.get('updated_at',0),r['id']),reverse=True)[:3]
    seen=set(); result=[]; size=0
    for r in exact+matches+decisions:
        if r['id'] in seen:continue
        view={k:r.get(k) for k in ('id','kind','content','source','updated_at','version','trust')}
        size+=len(json.dumps(view,ensure_ascii=False))
        if size>14000 or len(result)>=limit:break
        seen.add(r['id']);result.append(view)
    return result

def parse_command(text):
    text=text.strip()
    m=re.fullmatch(r'(?:kelvin[,! ]+|келвин[,! ]+)?(?:/remember|запомни)[,: ]+(.+)',text,re.I|re.S)
    if m:
        value=m[1].strip(); kind,sep,content=value.partition(':')
        if sep and kind.lower() in KINDS:return ('save',{'kind':kind.lower(),'content':content.strip()})
        return ('save',{'kind':'personal','content':value})
    m=re.fullmatch(r'/extract\s+([a-z]+):\s*(.+)',text,re.I|re.S)
    if m and m[1].lower() in KINDS:return ('extract',{'kind':m[1].lower(),'content':m[2].strip()})
    m=re.fullmatch(r'/correct\s+(\S+)\s+(\d+)\s+([a-z]+):\s*(.+)',text,re.I|re.S)
    if m:return ('correct',{'id':m[1],'version':int(m[2]),'kind':m[3].lower(),'content':m[4].strip()})
    m=re.fullmatch(r'/confirm_memory\s+(\S+)\s+(\d+)',text)
    if m:return ('confirm',{'id':m[1],'version':int(m[2])})
    m=re.fullmatch(r'/forget\s+(\S+)(?:\s+(\d+))?',text)
    if m:return ('delete',{'id':m[1],**({'version':int(m[2])} if m[2] else {})})
    m=re.fullmatch(r'/memory(?:\s+(\S+))?',text)
    if m:return ('list',{'after':m[1] or ''})
    if text.startswith(('/correct','/forget','/remember','/memory','/confirm_memory','/extract')):return ('help',{})
    return None

def command_reply(bridge,job,records,extract=None):
    cmd=parse_command(job['prompt'])
    if not cmd or job.get('source') not in ('telegram','app'):return None
    action,args=cmd
    if action=='help':return '/remember decision: текст · /memory · /correct ID версия decision: новый текст · /forget ID версия'
    if action=='extract':
        if extract is None:return 'Извлечение фактов недоступно.'
        content=args['content'];kind=args['kind']
        if not safe_text(content) or len(content.encode())>6000:return 'Текст не подходит для извлечения памяти.'
        count=0
        for quote in extract(content)[:5]:
            if not safe_text(quote) or quote not in content or not 12<=len(quote.encode())<=1000:continue
            ident='candidate-'+hashlib.sha256((kind+'\0'+quote).encode()).hexdigest()[:32]
            bridge.call('records',{'action':'candidate','id':ident,'kind':kind,'content':quote,'job':job['id'],'lease':job['lease']});count+=1
        return f'Извлечено для проверки: {count}. /memory candidates — посмотреть и подтвердить.'
    if action=='list':
        # Show a short page, using a stable ID cursor; no full memory dump.
        candidates=args['after']=='candidates'
        ordered=sorted((r for r in records if r.get('trust')=='candidate' and safe_text(r.get('content'))) if candidates else (r for r in eligible(records) if r['id']>args['after']),key=lambda r:r['id'])
        page=ordered[:8]
        lines=[f"{r['id']} v{r['version']} [{r['kind']}] {r['content'][:200]}" for r in page]
        if candidates:
            lines.extend(['Подтвердить: /confirm_memory ID версия']) if page else None
        elif len(ordered)>8:lines.append('/memory '+page[-1]['id'])
        return '\n'.join(lines) or 'Нет записей.'
    if action=='save':args['id']='note-'+hashlib.sha256(job['id'].encode()).hexdigest()[:32]
    if action=='delete' and 'version' not in args:
        r=next((r for r in records if r['id']==args['id']),None)
        if not r:return 'Запись не найдена.'
        args['version']=r['version']
    if 'content' in args and (not safe_text(args['content']) or not args['content'] or len(args['content'].encode())>2000):return 'Запись не сохранена: секрет, пустой или слишком длинный текст.'
    result=bridge.call('records',dict(args,action=action,job=job['id'],lease=job['lease']))
    if action=='delete':return 'Запись исключена из памяти. История чата сохранена для просмотра, предыдущие сообщения больше не подаются модели.'
    return f"Сохранено: {result['id']} v{result['version']}."


# Candidate capture is intentionally conservative. It preserves the exact owner
# statement, never an assistant assertion or a search result, and costs no model call.
DECLARATIONS=(('decision',r'^(?:мы решили|я решил[аи]?|решение:|утверждаю:)\s*.+'),('personal',r'^(?:моя цель|я предпочитаю|мой приоритет|mening maqsadim)\s*.+'),('business',r'^(?:наша стратегия|стратегия iumrah|наша миссия|bizning maqsadimiz)\s*.+'),('task',r'^(?:моя задача|наш план|задача:)\s*.+'))

def capture_candidate(bridge,job):
    if job.get('source') not in ('telegram','app'):return None
    text=job['prompt'].strip()
    if not safe_text(text) or not 12<=len(text.encode())<=6000:return None
    result=None;count=0
    # Each candidate is an exact substring of the owner's message, not a model paraphrase.
    for part in re.split(r'(?<=[.!?])\s+|\n+',text):
        part=part.strip()
        if not 12<=len(part.encode())<=1000 or '?' in part:continue
        for kind,pattern in DECLARATIONS:
            if re.fullmatch(pattern,part,re.I):
                ident='candidate-'+hashlib.sha256((kind+'\0'+part).encode()).hexdigest()[:32]
                result=bridge.call('records',{'action':'candidate','id':ident,'kind':kind,'content':part,'job':job['id'],'lease':job['lease']})
                count+=1;break
        if count>=3:break
    return result
