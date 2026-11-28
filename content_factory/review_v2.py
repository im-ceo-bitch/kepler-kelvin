"""Separate deterministic integrity checks from human/creative review evidence.
An advisory gate only: this module cannot approve publication.
"""
import hashlib,json,subprocess
from pathlib import Path

RUBRICS={
 'video':{'strategy':20,'offer':20,'hook':15,'type_brand':15,'direction':15,'language_audio':10,'cta':5},
 'carousel':{'strategy':20,'offer':20,'cover':15,'layout_brand':20,'sequence':15,'language':5,'cta':5},
 'talking_head_script':{'strategy':20,'offer':20,'hook':20,'spoken_flow':20,'language':15,'cta':5},
}


def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def manifest_digest(manifest):
    return hashlib.sha256(json.dumps(manifest,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def check_media(path,fmt):
    if fmt=='talking_head_script':
        if path.suffix.lower() not in {'.md','.txt'} or not path.read_text(encoding='utf8').strip():raise ValueError('Require nonempty UTF-8 script')
        return {'kind':'text'}
    allowed={'.mp4'} if fmt=='video' else {'.png','.jpg','.jpeg','.webp'}
    if path.suffix.lower() not in allowed:raise ValueError('Wrong media format')
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],timeout=25))
    stream=next((s for s in data['streams'] if s.get('codec_type')=='video'),None)
    if not stream or not stream.get('width') or not stream.get('height'):raise ValueError('No visual stream')
    subprocess.run(['ffmpeg','-nostdin','-v','error','-xerror','-i',str(path),'-f','null','-'],check=True,timeout=180,capture_output=True)
    if fmt=='video':
        duration=float(data['format'].get('duration',0))
        if duration<=0 or (stream['width'],stream['height'])!=(1080,1920):raise ValueError('Require vertical 1080x1920 video with duration')
        return {'width':stream['width'],'height':stream['height'],'duration':duration,'audio':any(s.get('codec_type')=='audio' for s in data['streams'])}
    if (stream['width'],stream['height'])!=(1080,1350):raise ValueError('Require 1080x1350 carousel')
    return {'width':1080,'height':1350}


def validate_manifest(manifest,root,probe=check_media):
    fmt=manifest['format'];RUBRICS[fmt]
    if not isinstance(manifest.get('version'),str) or not manifest['version'].strip():raise ValueError('Missing version')
    files=manifest['files']; root=Path(root).resolve()
    if not isinstance(files,list) or not files or (fmt!='carousel' and len(files)!=1) or (fmt=='carousel' and len(files)<2):raise ValueError('Wrong number of deliverables')
    result={};seen=set()
    for item in files:
        path=(root/item['path']).resolve()
        if not path.is_relative_to(root) or path in seen or not path.is_file() or digest(path)!=item['sha256']:raise ValueError('Invalid path, duplicate or changed file')
        seen.add(path);result[item['path']]=probe(path,fmt)
    return {'manifest_sha256':manifest_digest(manifest),'files':result,'technical':'pass'}


def evaluate_review(manifest,review,root,probe=check_media):
    technical=validate_manifest(manifest,root,probe)
    if review.get('manifest_sha256')!=technical['manifest_sha256']:raise ValueError('Review is for another version')
    fmt=manifest['format'];weights=RUBRICS[fmt]
    if set(review['scores'])!=set(weights):raise ValueError('Incorrect rubric for format')
    total=0
    for k,maximum in weights.items():
        s=review['scores'][k]
        if type(s['points']) is not int or not 0<=s['points']<=maximum or not isinstance(s.get('observation'),str) or not s['observation'].strip():raise ValueError('Invalid score or observation')
        total+=s['points']
    examined=review['examined']
    if not isinstance(examined,list) or len(examined)!=len(manifest['files']) or {x['path'] for x in examined}!=set(technical['files']):raise ValueError('Review must cover every deliverable')
    for item in examined:
        if not isinstance(item.get('observation'),str) or not item['observation'].strip() or not isinstance(item.get('location'),str) or not item['location'].strip():raise ValueError('Missing location or observation')
    critical=review['critical']
    if not isinstance(critical,list) or any(not isinstance(s,str) or not s.strip() for s in critical):raise ValueError('Invalid critical findings')
    for key in ('rights_verified','claims_verified','language_verified'):
        if type(review.get(key)) is not bool:raise ValueError('Explicit review check required: '+key)
    # No score or identity string proves actual independent review. Always requires
    # independent human/authorized reviewer and owner approval outside this module.
    blocked=bool(critical) or total<85 or not all(review[k] for k in ('rights_verified','claims_verified','language_verified'))
    return {**technical,'score':total,'decision':'revise' if blocked else 'independent_review_required','publication_authorized':False,'creative_independence_verified':False}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--review',type=Path)
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text(encoding='utf8'))
    if args.review:
        result=evaluate_review(manifest,json.loads(args.review.read_text(encoding='utf8')),args.manifest.parent)
    else:
        result=validate_manifest(manifest,args.manifest.parent)
    print(json.dumps(result,ensure_ascii=False,indent=2))
