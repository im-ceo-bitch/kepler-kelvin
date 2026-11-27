"""Generate owner-only local configuration and LaunchAgents; no secrets in plists."""
from pathlib import Path
import getpass, os, plistlib, re, sys, shutil, subprocess, time
ROOT=Path(__file__).resolve().parents[2]
BASE=Path.home()/'Library'/'Application Support'/'Kelvin'
LABEL='com.kelvin.manager'
OLLAMA='com.kelvin.ollama'

def secure_directory(p):
    p.mkdir(parents=True,exist_ok=True); p.chmod(0o700)

def write_config():
    secure_directory(BASE)
    for name in ('logs','data','workspace'): secure_directory(BASE/name)
    p=BASE/'runtime.env'
    if p.exists():
        p.chmod(0o600); print('Using existing private configuration.'); return
    token=getpass.getpass('Telegram bot token (hidden): ').strip()
    owner=input('Numeric Telegram owner ID: ').strip()
    if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]+',token) or not re.fullmatch(r'[1-9][0-9]*',owner):
        raise SystemExit('Invalid token or ID; configuration not saved.')
    # dotenv double quoted values; paths are escaped explicitly.
    def quote(s): return '"'+str(s).replace('\\','\\\\').replace('"','\\"')+'"'
    values={'TELEGRAM_BOT_TOKEN':token,'JARVIS_OWNER_ID':owner,'JARVIS_ENGINE':'ollama','JARVIS_MODEL':'qwen2.5:3b','JARVIS_LANGUAGE':'ru','JARVIS_WHISPER_MODEL':'base','JARVIS_MAC_VOICE':'Milena','JARVIS_DATA_DIR':BASE/'data','JARVIS_WORKSPACE':BASE/'workspace'}
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f: f.write(''.join(f'{k}={quote(v)}\n' for k,v in values.items()))
    print('Private configuration saved outside Git.')

def plist(label, args, path, repo=ROOT, env=None):
    return {'Label':label,'ProgramArguments':[str(x) for x in args],'WorkingDirectory':str(repo),'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':30,'ExitTimeOut':30,'Umask':0o077,'EnvironmentVariables':{'PATH':path, **(env or {})},'StandardOutPath':str(BASE/'logs'/f'{label}.out.log'),'StandardErrorPath':str(BASE/'logs'/f'{label}.err.log')}

def install_plist(label, data):
    folder=Path.home()/'Library'/'LaunchAgents'; folder.mkdir(parents=True,exist_ok=True)
    target=folder/(label+'.plist'); tmp=folder/(label+'.plist.tmp')
    with tmp.open('wb') as f: plistlib.dump(data,f)
    tmp.chmod(0o600); tmp.replace(target)
    subprocess.run(['/usr/bin/plutil','-lint',str(target)],check=True)
    return target

def main():
    if len(sys.argv)!=3: raise SystemExit('service.py config|ollama|runtime executable')
    mode, executable=sys.argv[1:]; secure_directory(BASE); secure_directory(BASE/'logs')
    if mode=='config': write_config(); return
    path=os.pathsep.join(dict.fromkeys([str(Path(executable).parent),str(Path.home()/'.local/bin'),'/usr/local/bin','/opt/homebrew/bin','/usr/bin','/bin','/usr/sbin','/sbin',os.environ.get('PATH','')]))
    if mode=='ollama':
        label=OLLAMA; args=['/bin/bash',ROOT/'founder_jarvis/macos/ollama-service.sh',executable]; env={'OLLAMA_HOST':'127.0.0.1:11434','OLLAMA_NUM_PARALLEL':'1','OLLAMA_MAX_LOADED_MODELS':'1'}
    elif mode=='runtime':
        label=LABEL; args=['/usr/bin/caffeinate','-s',executable,'-m','founder_jarvis.runtime']; env={'KELVIN_ENV_FILE':str(BASE/'runtime.env'),'PYTHONUNBUFFERED':'1','OLLAMA_HOST':'127.0.0.1:11434','KELVIN_AGENT_PYTHON':str(ROOT/'.venv/bin/python'),'KELVIN_SPEECH_PYTHON':str(BASE/'speech-venv/bin/python'),'KELVIN_INSTALL_STATUS':str(BASE/'install-status.txt'),'HOME':str(Path.home()),'JARVIS_ENGINE':'claude','JARVIS_MODEL':'default','KELVIN_CLAUDE_BIN':os.environ['KELVIN_CLAUDE_BIN'],'KELVIN_LOCAL_MODEL':'qwen2.5:3b'}
        if not (BASE/'speech-venv/bin/python').is_file(): env['KELVIN_SPEECH_PYTHON']=str(ROOT/'.venv/bin/python')
    else: raise SystemExit('Unknown service')
    target=install_plist(label,plist(label,args,path,env=env))
    domain=f'gui/{os.getuid()}'
    register(domain,label,target)
    print(f'Started {label}; inspect launchctl and logs for actual runtime status.')

def register(domain,label,target):
    ctl='/bin/launchctl'; job=f'{domain}/{label}'
    def call(*args): return subprocess.run([ctl,*args],capture_output=True,text=True)
    def loaded(): return call('print',job).returncode==0
    # bootout is asynchronous; wait for the previous registration to disappear.
    if loaded():
        result=call('bootout',job)
        for _ in range(30):
            if not loaded(): break
            time.sleep(1)
        else: raise SystemExit(f'Old service still registered: {job}. {result.stderr}')
    result=call('enable',job)
    if result.returncode: raise SystemExit(result.stderr or 'launchctl enable failed')
    for attempt in range(6):
        result=call('bootstrap',domain,str(target))
        if loaded():
            result=call('kickstart',job)
            if result.returncode: raise SystemExit(result.stderr or 'launchctl kickstart failed')
            return
        time.sleep(2)
    raise SystemExit(f'LaunchAgent registration failed: {result.stderr}. Run launchctl print {domain} and inspect launchd logs. Do not use sudo.')

if __name__=='__main__': main()
