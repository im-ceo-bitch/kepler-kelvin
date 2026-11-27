"""Local operational safeguards. No network, model calls or secret export."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, logging, os, re, shutil, sqlite3, tempfile
from contextlib import closing
from logging.handlers import RotatingFileHandler
from pathlib import Path

DBS=('jobs.sqlite3','autonomy.sqlite3','advisor-scheduler.sqlite3')
PREF='voice-language.json'
SECRET=re.compile(r'(?i)(?:\b[0-9]{5,}:[A-Za-z0-9_-]{8,}|\bsk-(?:ant-)?[A-Za-z0-9_-]{12,}|\bgh[pousr]_[A-Za-z0-9_]{8,}|\bgithub_pat_[A-Za-z0-9_]+|\bBearer\s+[^\s,;]+|\b[a-f0-9]{64}\b)')

def redact_log(text):
    for k in ('TELEGRAM_BOT_TOKEN','ANTHROPIC_API_KEY','OPENAI_API_KEY'):
        v=os.environ.get(k)
        if v:text=text.replace(v,'[SECRET]')
    return SECRET.sub('[SECRET]',text)

class PrivateFormatter(logging.Formatter):
    def format(self,record):return redact_log(super().format(record))

def configure_logging(folder):
    folder=Path(folder);folder.mkdir(mode=0o700,parents=True,exist_ok=True)
    h=RotatingFileHandler(folder/'runtime.log',maxBytes=2*1024*1024,backupCount=3,encoding='utf-8')
    h.setFormatter(PrivateFormatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    root=logging.getLogger();root.setLevel(logging.WARNING)
    for old in list(root.handlers):root.removeHandler(old);old.close()
    root.addHandler(h)
    for name in ('httpx','httpcore','telegram','urllib3'):logging.getLogger(name).setLevel(logging.ERROR)

def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def integrity(path):
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=10)) as db:
        return db.execute('PRAGMA quick_check').fetchall()==[('ok',)]

def snapshot(data,backups,now=None):
    """Online SQLite backup per database; not a cross-DB atomic snapshot."""
    data=Path(data);backups=Path(backups);backups.mkdir(mode=0o700,parents=True,exist_ok=True)
    stamp=(now or dt.datetime.now(dt.timezone.utc)).strftime('%Y%m%dT%H%M%S%fZ')
    temp=Path(tempfile.mkdtemp(prefix='.partial-',dir=backups))
    try:
        files={}
        for name in (*DBS,PREF):
            src=data/name;dst=temp/name
            if not src.is_file():continue
            if src.is_symlink():raise RuntimeError('Refusing symlink in data directory')
            if name in DBS:
                with closing(sqlite3.connect(src.resolve().as_uri()+'?mode=ro',uri=True,timeout=10)) as a, closing(sqlite3.connect(dst,timeout=10)) as b:a.backup(b)
                if not integrity(dst):raise RuntimeError('Database backup failed integrity check')
            else:
                if src.stat().st_size>4096:raise RuntimeError('Invalid voice preferences size')
                shutil.copyfile(src,dst)
            dst.chmod(0o600);files[name]={'sha256':digest(dst),'bytes':dst.stat().st_size}
        if not files:return None
        (temp/'manifest.json').write_text(json.dumps({'version':1,'files':files},indent=2));(temp/'manifest.json').chmod(0o600)
        dest=backups/('snapshot-'+stamp);temp.rename(dest)
        return dest
    finally:
        if temp.exists():shutil.rmtree(temp)

def verify(source):
    source=Path(source);m=json.loads((source/'manifest.json').read_text())
    if m.get('version')!=1 or not isinstance(m.get('files'),dict) or not m['files']:raise RuntimeError('Invalid backup manifest')
    for name,info in m['files'].items():
        if name not in (*DBS,PREF):raise RuntimeError('Invalid backup entry')
        p=source/name
        if p.is_symlink() or not p.is_file() or p.stat().st_size!=info['bytes'] or digest(p)!=info['sha256']:raise RuntimeError('Backup checksum mismatch')
        if name in DBS and not integrity(p):raise RuntimeError('Backup database invalid')
    return m

def restore_to(source,dest):
    """Restore only into a new directory. Never overwrite live data or replay jobs."""
    source=Path(source);dest=Path(dest);m=verify(source)
    if dest.exists() or dest.is_symlink():raise RuntimeError('Restore target must not exist')
    dest.mkdir(mode=0o700,parents=False)
    try:
        for name in m['files']:
            shutil.copyfile(source/name,dest/name);(dest/name).chmod(0o600)
        verify_restored=all(integrity(dest/n) for n in DBS if n in m['files'])
        if not verify_restored:raise RuntimeError('Restore integrity failed')
    except BaseException:
        shutil.rmtree(dest);raise
    return dest

def daily_backup(data,backups,now=None,keep=7):
    now=now or dt.datetime.now(dt.timezone.utc);backups=Path(backups)
    existing=sorted(p for p in backups.glob('snapshot-*') if p.is_dir() and not p.is_symlink() and re.fullmatch(r'snapshot-\d{8}T\d{12}Z',p.name))
    if existing and existing[-1].name.startswith('snapshot-'+now.strftime('%Y%m%d')):
        verify(existing[-1]);return None
    new=snapshot(data,backups,now)
    if new:
        verify(new)
        for p in (existing+[new])[:-keep]:shutil.rmtree(p)
    return new

def check_local(data):
    data=Path(data)
    result={}
    for n in DBS:
        try:result[n]='missing' if not (data/n).is_file() else 'ok' if integrity(data/n) else 'corrupt'
        except sqlite3.DatabaseError:result[n]='corrupt'
    return result

def main():
    os.umask(0o077)
    p=argparse.ArgumentParser();p.add_argument('action',choices=['backup','verify','restore','check']);p.add_argument('path',nargs='?');p.add_argument('destination',nargs='?');a=p.parse_args()
    from dotenv import dotenv_values
    from founder_jarvis.shared_business import BASE
    cfg=dotenv_values(BASE/'runtime.env');data=Path(cfg.get('JARVIS_DATA_DIR') or BASE/'data').expanduser()
    if a.action=='backup':print(snapshot(data,BASE/'backups') or 'No local state yet')
    elif a.action=='verify':verify(Path(a.path));print('Backup verified')
    elif a.action=='restore':restore_to(Path(a.path),Path(a.destination));print('Restored for offline inspection. Do not start this copy without reconciling queues.')
    else:
        result=check_local(data);print(json.dumps(result));raise SystemExit(1 if 'corrupt' in result.values() else 0)
if __name__=='__main__':main()
