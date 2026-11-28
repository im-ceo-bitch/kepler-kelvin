"""Build an offline inventory of the studio and explicitly named brand exports."""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

AV = set('mp4 mov m4v webm mkv mp3 m4a wav aac ogg flac'.split())
IMAGE = set('png jpg jpeg webp gif svg heic'.split())
FONT = {'ttf', 'otf', 'woff', 'woff2'}
PROJECT = set('tsx ts jsx js css html json prproj aep fcpxml drp srt vtt zip'.split())
SKIP = {'node_modules', '.git', '.hyperframes', '.cache', 'dist', 'build', '__pycache__'}
TOP = {'01','02','03','04','05','06','07','08'}
PURPOSE = {'01':'Founder camera original', '02':'Brand asset or composition demonstration',
           '03':'B-roll or UI insert', '04':'Actual application capture', '05':'Visual reference',
           '06':'Edit project or intermediate', '07':'Delivered cut or review export',
           '08':'Script timing or transcript', 'tools':'Studio composition or renderer dependency',
           'downloads':'Additional branded export or import archive'}

def files(studio, downloads):
    for folder in sorted(studio.iterdir()):
        group = folder.name[:2]
        if group not in TOP and folder.name != 'tools':
            continue
        group = 'tools' if folder.name == 'tools' else group
        for current, dirs, names in os.walk(folder):
            dirs[:] = sorted(d for d in dirs if d not in SKIP and not d.startswith('.'))
            for name in sorted(names):
                path = Path(current) / name
                if not name.startswith('.') and not path.is_symlink():
                    yield 'studio', path.relative_to(studio), path, group
    if downloads:
        patterns = ('iumrah-premium-motion/*', 'iumrah_*Premium*.mp4', 'RPReplay_Final1795269661*.MP4',
                    'iumrah-reel*.zip', 'iumrah-video-references.zip', 'iumrah-studio-update.zip',
                    'iumrah*Play*Screenshot*/*.png', 'iumrah*play*feature*.png')
        for path in sorted({p for pattern in patterns for p in downloads.glob(pattern) if p.is_file() and not p.is_symlink()}):
            yield 'downloads', path.relative_to(downloads), path, 'downloads'

# Verified by decoded frames or the studio's timecode catalog.
LABELS = {
    '-1646620594894889871': 'Kaaba and minarets framed by an arch; review-only B-roll',
    '-949025199128262000': 'Makkah clock tower and pilgrims outdoors; embedded title',
    'RPReplay_Final1795269661': 'App itinerary builder: flights, Makkah/Madinah hotels, transfer, guide and historical estimate',
    'B_009.80-013.50_flight-select': 'Actual flight selection UI; selection checkmark at source time 11.43 s',
    'iumrah_premium_reels': 'Brand reference: masked letter reveal, real product cards, dot-to-wordmark outro',
    'direction_reference_7949719995088283542': 'Talking-head direction reference: shot-size changes, UI cutaway and timed emphasis',
    'reel-002-claude-v2': 'Previous edit: founder in car, service names in split frame, Makkah road cutaway',
    'iumrah-world-dots': 'Original iumrah dot world map',
    'Inter-opsz-wght': 'Inter variable optical size and weight; approved display settings in studio tokens',
}

def media_info(path):
    result = subprocess.run(['ffprobe','-v','error','-show_entries',
        'format=duration:stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels',
        '-of','json',str(path)], capture_output=True, timeout=15)
    if result.returncode:
        return {'probe':'unreadable'}
    return json.loads(result.stdout)

def index(studio, downloads, observations):
    rows = []
    for root, relative, path, group in files(studio, downloads):
        ext = path.suffix.lower().lstrip('.')
        if ext not in AV | IMAGE | FONT | PROJECT or path.name in {'package-lock.json','gallery.js'}:
            continue
        use = 'Internal review; confirm source rights and exact version before external use'
        if group == '05':
            use = 'Study direction only; third-party footage, graphics and audio require a separate licence'
        if ext in FONT:
            use = 'Check adjacent font licence; studio selects Inter Display for editorial graphics'
        row = {'root':root, 'path':relative.as_posix(), 'format':ext, 'bytes':path.stat().st_size,
               'content_label':LABELS.get(path.stem, path.stem),
               'description_source':'review or studio catalog' if path.stem in LABELS else 'filename only',
               'purpose':PURPOSE[group], 'usage':use}
        if ext in AV or ext in IMAGE - {'svg'}:
            try:
                row['technical'] = media_info(path)
            except (subprocess.TimeoutExpired, ValueError):
                row['technical'] = {'probe':'inconclusive'}
        note = observations.get(root + '/' + relative.as_posix())
        if note:
            digest = hashlib.sha256()
            with path.open('rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(block)
            if digest.hexdigest() == note['sha256']:
                row['sample'] = note
                row['description_source'] = 'decoded frame'
        rows.append(row)
    return {'schema':1,'roots':{'studio':'~/Documents/IUMRAH-CONTENT','downloads':'~/Downloads'},
            'rows':rows,'counts':dict(collections.Counter(r['format'] for r in rows))}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--studio',type=Path,default=Path.home()/'Documents/IUMRAH-CONTENT')
    parser.add_argument('--downloads',type=Path,default=Path.home()/'Downloads')
    args=parser.parse_args()
    source = Path(__file__).resolve().parents[1]/'docs/content-factory/evidence/video-observations.local.json'
    observations = json.loads(source.read_text()) if source.is_file() else {}
    inventory=index(args.studio,args.downloads,observations)
    inventory['roots']={k:str(p.resolve()).replace(str(Path.home())+'/', '~/',1) for k,p in [('studio',args.studio),('downloads',args.downloads)]}
    with tempfile.NamedTemporaryFile('w',dir=args.output.parent,delete=False,encoding='utf-8') as tmp:
        json.dump(inventory,tmp,ensure_ascii=False,indent=1)
    os.replace(tmp.name,args.output)
    print('Indexed', len(inventory['rows']), 'assets')

if __name__=='__main__':
    main()
