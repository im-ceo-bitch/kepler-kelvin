"""Mac integration around the original OpenJarvis agent and scheduler."""
import asyncio, datetime as dt, json, os, re, signal, subprocess, sys, time
from pathlib import Path
from zoneinfo import ZoneInfo
from founder_jarvis import integrations as tools
ROOT=Path(__file__).resolve().parents[1]
ZONE=ZoneInfo('Asia/Tashkent')
REPORTS={8:('morning','Утренний стратегический доклад: показатели iumrah, новости рынка, предложения конкурентов, три приоритета, конкретная рекомендация и вопрос основателю.'),12:('market','Дневной доклад: исследуй рынок умры, конкурентов, тренды маркетинга и новые возможности. Дай ссылки, отличай факты от гипотез, предложи одно проверяемое действие.'),21:('evening','Вечерний доклад: сверка предыдущих рекомендаций с известными результатами, нерешённые вопросы и план на завтра. Не придумывай результаты, спроси владельца о неизвестном.')}

def respond(prompt,history,workspace):
    binary=os.getenv('KELVIN_AGENT_PYTHON',str(ROOT/'.venv/bin/python'))
    if not Path(binary).is_file(): raise RuntimeError('OpenJarvis Python отсутствует. Запусти установщик Kelvin.')
    env=tools.clean_env(); env.update(PYTHONPATH=os.pathsep.join([str(ROOT/'src'),str(ROOT)]),KELVIN_CLAUDE_BIN=os.getenv('KELVIN_CLAUDE_BIN',''),OPENJARVIS_HOME=str(Path(workspace)/'.advisor'))
    if os.getenv('ANTHROPIC_API_KEY'): env['ANTHROPIC_API_KEY']=os.environ['ANTHROPIC_API_KEY']
    p=subprocess.Popen([binary,'-m','founder_jarvis.native_advisor'],cwd=workspace,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    try: out,err=p.communicate(json.dumps({'prompt':prompt,'history':history},ensure_ascii=False),timeout=720)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid,signal.SIGKILL);p.communicate();raise RuntimeError('Тайм-аут OpenJarvis. Повтори запрос позже.') from None
    if p.returncode:
        import logging
        logging.getLogger('kelvin.advisor').warning('Native agent exit %s; %s',p.returncode,tools.redact((err or '')[-700:]))
        raise RuntimeError('OpenJarvis Orchestrator завершился с ошибкой. Проверь локальный журнал /health.')
    try: return tools.redact(json.loads(out)['answer'])
    except (ValueError,KeyError,TypeError): raise RuntimeError('Некорректный ответ OpenJarvis') from None

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
    class Enqueue:
        def ask(self,prompt,**kwargs):
            f=asyncio.run_coroutine_threadsafe(dispatch(),loop)
            return f.result(timeout=45)
    db=SchedulerStore(home/'advisor-scheduler.sqlite3'); sched=TaskScheduler(db,Enqueue(),poll_interval=10)
    if not any(t.prompt=='kelvin-advisor-tick' and t.status=='active' for t in sched.list_tasks()):
        task=sched.create_task('kelvin-advisor-tick','interval','60',agent='orchestrator'); d=task.to_dict();d['next_run']=dt.datetime.now(dt.timezone.utc).isoformat();db.update_task(d)
    sched.start();return sched,db
