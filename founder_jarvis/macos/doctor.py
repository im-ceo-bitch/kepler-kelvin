"""Non-mutating diagnostics by default. Optional live network checks never poll updates."""
import argparse, importlib.util, json, os, shutil, sqlite3, subprocess, sys, urllib.request
from pathlib import Path
from founder_jarvis import operations, shared_business


def run_check(name,fn,checks):
    try:
        result=fn();checks[name]=result
    except Exception as exc:checks[name]={'status':'error','type':type(exc).__name__}

def telegram_identity(token):
    if not token:return {'status':'not_configured'}
    req=urllib.request.Request('https://api.telegram.org/bot'+token+'/getMe',method='POST',data=b'{}',headers={'Content-Type':'application/json'})
    with urllib.request.build_opener(shared_business.NoRedirect()).open(req,timeout=15) as res:
        obj=json.loads(res.read(65536))
    return {'status':'ok' if obj.get('ok') is True and obj.get('result',{}).get('is_bot') else 'error'}

def backend():
    bridge=shared_business.Bridge.load()
    if bridge is None:return {'status':'unpaired'}
    r=bridge.call('diagnostics')
    return {'status':'ok' if r.get('protocol')==7 else 'version_mismatch','protocol':r.get('protocol'),'queue':r.get('queue')}

def probe_core(core,root):
    if not core.is_file():return {'status':'missing'}
    env={k:v for k,v in os.environ.items() if k in {'HOME','PATH','LANG','TMPDIR','SSL_CERT_FILE','SSL_CERT_DIR'}}
    env['PYTHONPATH']=os.pathsep.join([str(root/'src'),str(root)])
    p=subprocess.run([str(core),'-c','import croniter,ddgs,httpx; from founder_jarvis.native_advisor import provider_engine'],env=env,capture_output=True,timeout=30)
    return {'status':'ok' if p.returncode==0 else 'dependency_error'}

def main():
    os.umask(0o077)
    a=argparse.ArgumentParser();a.add_argument('--live',action='store_true',help='getMe and owner-scoped backend diagnostics only');args=a.parse_args()
    from dotenv import dotenv_values
    base=shared_business.BASE;root=Path(__file__).resolve().parents[2];cfg=dotenv_values(base/'runtime.env');data=Path(cfg.get('JARVIS_DATA_DIR') or base/'data').expanduser()
    checks={}
    checks['runtime']={'status':'ok' if sys.version_info[:2]==(3,11) else 'other_python','python':sys.version.split()[0]}
    checks['configuration']={'status':'ok' if cfg.get('TELEGRAM_BOT_TOKEN') and str(cfg.get('JARVIS_OWNER_ID','')).isdigit() else 'missing'}
    checks['claude']={'status':'found' if shutil.which('claude') else 'missing','inference':'not_tested'}
    checks['ffmpeg']={'status':'found' if shutil.which('ffmpeg') else 'missing'}
    run_check('local_databases',lambda:operations.check_local(data),checks)
    run_check('core_dependencies',lambda:probe_core(root/'.venv/bin/python',root),checks)
    if sys.platform=='darwin':
        def launch():
            p=subprocess.run(['/bin/launchctl','print',f'gui/{os.getuid()}/com.kelvin.manager'],capture_output=True,timeout=10)
            return {'status':'running' if p.returncode==0 and b'state = running' in p.stdout else 'not_confirmed'}
        run_check('launch_agent',launch,checks)
    if args.live:
        run_check('telegram',lambda:telegram_identity(cfg.get('TELEGRAM_BOT_TOKEN')),checks)
        run_check('backend',backend,checks)
    else:checks['network']={'status':'not_tested'}
    print(json.dumps(checks,ensure_ascii=False,indent=2))
    # Diagnostic report is not a claim of production readiness.
    return 1 if any(isinstance(v,dict) and v.get('status') in {'error','missing','version_mismatch','dependency_error'} for v in checks.values()) or 'corrupt' in checks.get('local_databases',{}).values() else 0
if __name__=='__main__':raise SystemExit(main())
