"""Calculate the technical review decision for one immutable creative version."""
import argparse
import hashlib
import json
from pathlib import Path

WEIGHTS = {'strategy':20,'offer':20,'hook':15,'type_brand':15,
           'direction':15,'language_audio':10,'cta':5}

def evaluate(review, root):
    """Review is an advisory record. Publishing is a separate owner action."""
    if review['format'] not in {'video','carousel','talking_head_script'}:
        raise ValueError('Unknown review format')
    if not all(isinstance(review[k],str) and review[k].strip()
               for k in ('creator','reviewer','version')):
        raise ValueError('Require creator, reviewer and version')
    if review['creator'].strip().casefold() == review['reviewer'].strip().casefold():
        raise ValueError('An independent reviewer is required')
    if not isinstance(review['critical'],list) or not all(isinstance(x,str) and x.strip() for x in review['critical']):
        raise ValueError('Invalid critical findings')
    if set(review['scores']) != set(WEIGHTS):
        raise ValueError('Supply all seven sections')
    total = 0
    for key, maximum in WEIGHTS.items():
        item = review['scores'][key]
        points = item['points']
        if type(points) is not int or not 0 <= points <= maximum or not isinstance(item['observation'],str) or not item['observation'].strip():
            raise ValueError('Invalid score or missing observation: ' + key)
        total += points
    assets = review['examined']
    if not isinstance(assets,list) or not assets:
        raise ValueError('Supply examined deliverables')
    suffixes = {'video':{'.mp4'}, 'carousel':{'.png','.jpg','.jpeg','.webp'},
                'talking_head_script':{'.md','.txt','.pdf','.docx'}}
    seen = set()
    for item in assets:
        path = (root/item['path']).resolve()
        if not path.is_relative_to(root.resolve()) or path in seen or not path.is_file():
            raise ValueError('Invalid or duplicate deliverable path')
        if path.suffix.lower() not in suffixes[review['format']]:
            raise ValueError('Examined deliverable does not match review format')
        seen.add(path)
        with path.open('rb') as source:
            digest = hashlib.file_digest(source,'sha256').hexdigest()
        if digest != item['sha256'] or not isinstance(item['location'],str) or not item['location'].strip():
            raise ValueError('Verify the file, digest and reviewed timecodes/pages')
    return {'version':review['version'],'score':total,
            'decision':'submit_to_founder' if total>=85 and not review['critical'] else 'revise'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record',type=Path)
    args=parser.parse_args()
    print(json.dumps(evaluate(json.loads(args.record.read_text()),args.record.parent)))
