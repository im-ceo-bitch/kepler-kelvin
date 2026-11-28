"""Mac integration around the original OpenJarvis agent and scheduler."""
import asyncio, datetime as dt, json, os, re, signal, subprocess, sys, time
from pathlib import Path
from zoneinfo import ZoneInfo
from founder_jarvis import integrations as tools
ROOT=Path(__file__).resolve().parents[1]
ZONE=ZoneInfo('Asia/Tashkent')
REPORTS={8:('morning','Утренний стратегический доклад: показатели iumrah, новости рынка, предложения конкурентов, три приоритета, конкретная рекомендация и вопрос основателю.'),12:('market','Дневной доклад: исследуй рынок умры, конкурентов, тренды маркетинга и новые возможности. Дай ссылки, отличай факты от гипотез, предложи одно проверяемое действие.'),21:('evening','Вечерний доклад: сверка предыдущих рекомендаций с известными результатами, нерешённые вопросы и план на завтра. Не придумывай результаты, спроси владельца о неизвестном.')}

def _invoke(prompt,history,workspace,operation="answer",cancel=None):
    binary=os.getenv('KELVIN_AGENT_PYTHON',str(ROOT/'.venv/bin/python'))
    if not Path(binary).is_file(): raise RuntimeError('OpenJarvis Python отсутствует. Запусти установщик Kelvin.')
    env=tools.clean_env(); env.update(KELVIN_CHILD_PROCESS_GROUP='1',PYTHONPATH=os.pathsep.join([str(ROOT/'src'),str(ROOT)]),KELVIN_CLAUDE_BIN=os.getenv('KELVIN_CLAUDE_BIN',''),OPENJARVIS_HOME=str(Path(workspace)/'.advisor'),KELVIN_PROVIDER=os.getenv('KELVIN_PROVIDER','claude'),KELVIN_LOCAL_MODEL=os.getenv('KELVIN_LOCAL_MODEL','qwen2.5:3b'),KELVIN_PERSONA_ROOT=os.getenv('KELVIN_PERSONA_ROOT',str(Path.home()/'.openjarvis'/'personas'/'kelvin')))
    if operation == 'answer' and os.getenv('KELVIN_LOCAL_ON_CLAUDE_LIMIT') == '1':
        env['KELVIN_LOCAL_ON_CLAUDE_LIMIT'] = '1'
    if os.getenv('ANTHROPIC_API_KEY'):
        if operation=='research' and os.getenv('KELVIN_ALLOW_PAID_BACKGROUND','0')!='1':raise RuntimeError('Платные фоновые запросы не разрешены')
        env['ANTHROPIC_API_KEY']=os.environ['ANTHROPIC_API_KEY']
    p=subprocess.Popen([binary,'-m','founder_jarvis.native_advisor'],cwd=workspace,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    request=json.dumps({'prompt':prompt,'history':history,'operation':operation},ensure_ascii=False)
    deadline=time.monotonic()+(180 if operation=='research' else 720)
    try:
        if cancel is None:out,err=p.communicate(request,timeout=max(1,deadline-time.monotonic()))
        else:
            while True:
                if cancel.is_set() or time.monotonic()>=deadline:raise subprocess.TimeoutExpired(p.args,180)
                try:out,err=p.communicate(request,timeout=1);break
                except subprocess.TimeoutExpired:request=None
    except subprocess.TimeoutExpired:
        try:os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        p.communicate();raise RuntimeError('Тайм-аут или остановка OpenJarvis. Повтори запрос позже.') from None
    if p.returncode:
        if p.returncode==75:
            try: limited=json.loads(out).get('error')=='CLAUDE_RATE_LIMIT'
            except (ValueError,AttributeError): limited=False
            if limited:raise RuntimeError('Claude временно недоступен: лимит запросов (HTTP 429). Профессиональные задачи не передаются локальной модели.')
        import logging
        logging.getLogger('kelvin.advisor').warning('Native agent exit %s',p.returncode)
        raise RuntimeError('OpenJarvis Orchestrator завершился с ошибкой. Проверь локальный журнал /health.')
    try: return json.loads(out)
    except (ValueError,TypeError): raise RuntimeError('Некорректный ответ OpenJarvis') from None

def respond(prompt,history,workspace):
    result=_invoke(prompt,history,workspace)
    if not isinstance(result.get('answer'),str):raise RuntimeError('Некорректный ответ OpenJarvis')
    return tools.redact(result['answer'])

def research(topic,workspace,prior=(),cancel=None):
    return _invoke(topic,list(prior),workspace,"research",cancel)

def extract(prompt,workspace):
    result=_invoke(prompt,[],workspace,'extract')
    if not isinstance(result.get('candidates'),list):raise RuntimeError('Некорректное извлечение памяти')
    return result['candidates']

def due_reports(now):
    # One catch-up slot per day, no flood when Mac resumes late. Subsequent slots run normally.
    hours=[h for h in REPORTS if h<=now.hour]
    if not hours:return []
    h=max(hours);name,prompt=REPORTS[h]
    return [(f'advisor-{now.date()}-{name}',prompt)]

def reminder(text,now=None):
    """Explicit natural-language reminder only; no model-generated schedules."""
    now=now or dt.datetime.now(ZONE)
    m=re.fullmatch(r'(?:kelvin[,! ]+|келвин[,! ]+)?напомни(?: мне)? через (\d{1,4})\s*(минут[уы]?|мин|час(?:а|ов)?)[,: ]+(.+)',text.strip(),re.I|re.S)
    if m:
        minutes=int(m[1])*(60 if m[2].lower().startswith('час') else 1)
        if 1<=minutes<=43200:return (now.timestamp()+minutes*60,'Напоминание владельцу: '+m[3].strip())
    m=re.fullmatch(r'(?:kelvin[,! ]+|келвин[,! ]+)?напомни(?: мне)? завтра в (\d{1,2})(?::(\d{2}))?[,: ]+(.+)',text.strip(),re.I|re.S)
    if m and int(m[1])<24 and int(m[2] or 0)<60:
        target=dt.datetime.combine(now.date()+dt.timedelta(days=1),dt.time(int(m[1]),int(m[2] or 0)),ZONE)
        return target.timestamp(),'Напоминание владельцу: '+m[3].strip()
    return None

def scheduler(home,loop,dispatch):
    # Upstream scheduler is pure Python; import it from the original source tree.
    sys.path.insert(0,str(ROOT/'src'))
    from openjarvis.scheduler import SchedulerStore,TaskScheduler
    from openjarvis.core.events import EventBus
    class Enqueue:
        def ask(self,prompt,**kwargs):
            if prompt!='kelvin-advisor-tick':return 'Unknown schedule ignored'
            f=asyncio.run_coroutine_threadsafe(dispatch(),loop)
            return f.result(timeout=45)
    db=SchedulerStore(home/'advisor-scheduler.sqlite3'); sched=TaskScheduler(db,Enqueue(),poll_interval=10,bus=EventBus())
    matching=[t for t in sched.list_tasks() if t.status=='active' and t.prompt=='kelvin-advisor-tick']
    for duplicate in matching[1:]:sched.pause_task(duplicate.id)
    if not any(t.prompt=='kelvin-advisor-tick' and t.status=='active' for t in sched.list_tasks()):
        task=sched.create_task('kelvin-advisor-tick','interval','60',agent='orchestrator'); d=task.to_dict();d['next_run']=dt.datetime.now(dt.timezone.utc).isoformat();db.update_task(d)
    sched.start();return sched,db
