"""Block 01 owner-only acceptance. No deployment, client traffic, or new services.
Live mode enqueues two synthetic owner turns and verifies finish + Telegram API delivery.
"""
import argparse, hashlib, json, os, re, secrets, subprocess, sys, time
from pathlib import Path
from founder_jarvis import shared_business, operations


def configure_reserve(path):
    """Preserve other dotenv lines and create a private backup, atomically."""
    if not path.is_file() or path.is_symlink(): raise RuntimeError('Missing private runtime.env')
    raw=path.read_text(encoding='utf8')
    settings={'KELVIN_PROVIDER':'claude','KELVIN_LOCAL_ON_CLAUDE_LIMIT':'1'}
    updated=raw
    for key,value in settings.items():
        updated=re.sub(r'(?m)^\s*(?:export\s+)?'+key+r'\s*=.*(?:\n|$)','',updated)
    updated=updated.rstrip('\n')+'\n'+''.join(f'{k}={v}\n' for k,v in settings.items())
    if updated==raw:return False
    backup=path.with_name('runtime.env.block01-'+secrets.token_hex(6)+'.bak')
    fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf8') as f:f.write(raw)
    tmp=path.with_name('runtime.env.block01-'+secrets.token_hex(6)+'.tmp')
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf8') as f:f.write(updated);f.flush();os.fsync(f.fileno())
    tmp.replace(path)
    return True


def receipts(logfile,ident):
    found={}
    for path in [logfile,*[logfile.with_name(logfile.name+'.'+str(i)) for i in range(1,4)]]:
        if not path.is_file():continue
        # Bounded read; the service uses rotating logs.
        with path.open('rb') as f:
            f.seek(max(0,path.stat().st_size-2_500_000));data=f.read().decode('utf8',errors='replace')
        for match in re.finditer(r'Foundation receipt ('+re.escape(ident)+r'-[12]) (done|failed) ([0-9a-f]{64})',data):
            found[match[1]]=dict(status=match[2],sha256=match[3])
    return found


def live_probe(bridge,logfile,timeout=240):
    before=bridge.call('diagnostics')
    if before.get('protocol')!=7:raise RuntimeError('Backend protocol 7 required')
    if any(before.get('queue',{}).get(k,0) for k in ('queued','running')):
        raise RuntimeError('Existing queue is busy; no probe enqueued')
    ident='foundation-probe-'+secrets.token_hex(12)
    word=secrets.choice(['сапфир','изумруд','рубин','янтарь','лазурит','кварц'])
    expected=hashlib.sha256(word.encode()).hexdigest()
    checks=[]
    for index,prompt in enumerate(['Ответь только словом '+word+'.','Какое слово было в предыдущем ответе? Ответь тем же словом.'],1):
        key=f'{ident}-{index}'
        bridge.enqueue(key,prompt,False,'telegram')
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            result=receipts(logfile,ident).get(key)
            if result:break
            time.sleep(2)
        else:result=None
        ok=bool(result and result['status']=='done' and result['sha256']==expected)
        checks.append({'turn':index,'finish_and_telegram_ack':bool(result),'correct_answer':ok})
        if not ok:break
    after=bridge.call('diagnostics')
    return {'protocol':after.get('protocol'),'before':before.get('queue'),'after':after.get('queue'),'turns':checks,'passed':len(checks)==2 and all(c['correct_answer'] for c in checks),'scope':'Owner queue -> model -> finish -> Telegram send acknowledgement. Incoming Telegram update requires owner message.'}


def main():
    os.umask(0o077)
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--enable-reserve',action='store_true',help='Explicitly consent to Claude primary with narrow local fallback; backs up private config and restarts service')
    p.add_argument('--live',action='store_true',help='Explicitly enqueue at most two harmless synthetic owner messages')
    p.add_argument('--timeout',type=int,default=240)
    a=p.parse_args()
    if sys.platform!='darwin':raise SystemExit('Run on the Kelvin MacBook only')
    if not 30<=a.timeout<=900:raise SystemExit('Timeout must be 30–900 seconds')
    from dotenv import dotenv_values
    env=shared_business.BASE/'runtime.env'; cfg=dotenv_values(env)
    data=Path(cfg.get('JARVIS_DATA_DIR') or shared_business.BASE/'data').expanduser()
    bridge=shared_business.Bridge.load()
    if not bridge:raise SystemExit('Kelvin is not paired')
    checks=operations.check_local(data)
    if 'corrupt' in checks.values():raise SystemExit('Database integrity check failed')
    diagnostic=bridge.call('diagnostics')
    if diagnostic.get('protocol')!=7:raise SystemExit('Protocol mismatch; existing service not changed')
    if a.enable_reserve:
        if any(diagnostic.get('queue',{}).get(k,0) for k in ('queued','running')):raise SystemExit('Queue busy; service not restarted')
        configure_reserve(env)
        subprocess.run(['/bin/launchctl','kickstart','-k',f'gui/{os.getuid()}/com.kelvin.manager'],check=True,timeout=30)
    if a.live:
        result=live_probe(bridge,data/'logs/runtime.log',a.timeout)
    else:result={'protocol':7,'databases':checks,'queue':diagnostic.get('queue'),'passed':False,'scope':'Read-only preflight, live proof not run'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if not a.live or result['passed'] else 1

if __name__=='__main__':
    try:raise SystemExit(main())
    except RuntimeError as exc:raise SystemExit(str(exc)) from None
