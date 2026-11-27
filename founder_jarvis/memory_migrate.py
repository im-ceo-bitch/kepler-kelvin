"""Backup / consented migration of old local notes (no automatic history export)."""
import argparse, hashlib, os, sqlite3, datetime
from pathlib import Path
from contextlib import closing
from founder_jarvis.shared_business import Bridge, BASE
from founder_jarvis.persistent_memory import safe_text

def backup(dbpath,dest):
    if not dbpath.exists():return None
    dest.mkdir(mode=0o700,parents=True,exist_ok=True);dest.chmod(0o700)
    name=dest/(dbpath.stem+'-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.sqlite3')
    with closing(sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True)) as src, closing(sqlite3.connect(name)) as dst:
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Backup integrity failed')
    name.chmod(0o600);return name

def load_records(dbpath,owner,include_history=False):
    if not dbpath.exists():return []
    result=[]
    with closing(sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True)) as db:
        def add(kind,identity,text):
            if safe_text(text) and 1<=len(text.encode())<=2000:
                # Owner-scoped deterministic id: importing again cannot revive a tombstone.
                key='import-'+hashlib.sha256(f'{owner}:{identity}'.encode()).hexdigest()[:32]
                result.append({'id':key,'kind':kind,'content':text,'action':'save'})
        for ident,text in db.execute('SELECT id,text FROM memory WHERE chat=? ORDER BY id',(owner,)):add('personal','note:'+str(ident),text)
        if include_history:
            for ident,text in db.execute("SELECT id,prompt FROM jobs WHERE chat=? AND mode='chat' AND state='done' ORDER BY id",(owner,)):add('episodic','turn:'+str(ident),text)
    return result

def main():
    os.umask(0o077)
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--include-history',action='store_true');p.add_argument('--preflight',action='store_true');a=p.parse_args()
    from dotenv import dotenv_values
    cfg=dotenv_values(BASE/'runtime.env');owner=int(cfg.get('JARVIS_OWNER_ID') or 0)
    dbpath=(Path(cfg.get('JARVIS_DATA_DIR') or str(BASE/'data')).expanduser().resolve()/'jobs.sqlite3')
    if a.preflight:
        backup(dbpath.with_name('autonomy.sqlite3'),BASE/'backups')
        out=backup(dbpath,BASE/'backups');print('Local backup verified.' if out else 'No local DB to back up.')
        bridge=Bridge.load()
        if bridge:
            report=bridge.call('diagnostics')
            if report.get('protocol')!=7:raise SystemExit('Backend Kelvin protocol 7 required before installing this release.')
            bridge.call('records',{'action':'list'});bridge.call('autonomy',{'action':'snapshot'});print('Backend protocol 7, typed shared memory and autonomy API reachable.')
        else:print('Unpaired: local compatibility mode only; shared memory requires iumrah pairing.')
        return
    if owner<=0:raise SystemExit('Owner not configured')
    records=load_records(dbpath,owner,a.include_history);print(f'Eligible owner records: {len(records)}. History included: {a.include_history}. No text printed.')
    if not a.apply:return
    bridge=Bridge.load()
    if not bridge:raise SystemExit('Pair iumrah first')
    backup(dbpath,BASE/'backups');count=0
    for r in records:
        try:bridge.call('records',r);count+=1
        except RuntimeError as e:print(f'Import stopped after {count}; {e}. Existing imports are idempotent. Review conflicts manually.');raise SystemExit(1)
    print(f'Imported or previously present: {count}')
if __name__=='__main__':main()
