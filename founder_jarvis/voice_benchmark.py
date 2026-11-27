"""Opt-in local RU/UZ acceptance harness; no Telegram or Cloudflare calls.
Record 40 named WAVs from docs/kelvin/voice-benchmark-phrases.json.
Never treat missing recordings or synthetic loopback as a passing human-speech test.
"""
import argparse
import json
import os
import re
import resource
import sys
import tempfile
import time
import unicodedata
import wave
from pathlib import Path
from founder_jarvis.runtime import Voice

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs/kelvin/voice-benchmark-phrases.json'

def words(text):
    text=unicodedata.normalize('NFKC',text).casefold().translate(str.maketrans({'’':"'",'‘':"'",'ʻ':"'",'ʼ':"'",'`':"'",'ё':'е'}))
    return re.findall(r"[^\W_]+(?:'[^\W_]+)*",text,re.UNICODE)

def word_errors(reference, hypothesis):
    a,b=words(reference),words(hypothesis)
    prev=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        cur=[i]
        for j,y in enumerate(b,1): cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(x!=y)))
        prev=cur
    return prev[-1],len(a)

def benchmark(recordings, manifest, voice_factory=Voice):
    result=[]
    for row in manifest:
        item={'id':row['id'],'language':row['language']}
        path=recordings/(row['id']+'.wav')
        if not path.is_file(): result.append({**item,'status':'missing'});continue
        started=time.monotonic()
        try:
            if path.stat().st_size>15_000_000: raise ValueError('oversize')
            with wave.open(str(path),'rb') as wav:
                duration=wav.getnframes()/wav.getframerate()
                if not 0<duration<=45: raise ValueError('duration')
            text=voice_factory(row['language']).transcribe(path)
            elapsed=round(time.monotonic()-started,3); errors,count=word_errors(row['text'],text)
            result.append({**item,'status':'measured','errors':errors,'words':count,'seconds':elapsed,'audioSeconds':round(duration,3),'realTimeFactor':round(elapsed/duration,3)})
        except Exception as exc:
            result.append({**item,'status':'error','errorType':type(exc).__name__})
    return result

def summarize(results):
    report={}
    for lang in ('ru','uz'):
        rows=[r for r in results if r['language']==lang]; measured=[r for r in rows if r['status']=='measured']; n=sum(r['words'] for r in measured)
        times=sorted(r['seconds'] for r in measured)
        report[lang]={'expected':len(rows),'measured':len(measured),'wer':round(sum(r['errors'] for r in measured)/n,4) if n else None,'p50Seconds':times[len(times)//2] if times else None,'complete':bool(rows) and len(rows)==len(measured)}
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('recordings',type=Path);p.add_argument('--output',type=Path,default=Path('kelvin-voice-benchmark.json')); p.add_argument('--tts',action='store_true',help='also measure installed local TTS (synthetic output, not subjective quality)');args=p.parse_args()
    speech=Path.home()/'Library/Application Support/Kelvin/speech-venv/bin/python'
    if speech.is_file(): os.environ.setdefault('KELVIN_SPEECH_PYTHON',str(speech))
    manifest=json.loads(MANIFEST.read_text()); results=benchmark(args.recordings,manifest)
    summary=summarize(results); report={'recognition':summary,'cases':results,'tts':{},'note':'Human voice quality and audio latency on iPhone need a separate real-device test. Missing files are not passes.'}
    if args.tts:
        for lang in ('ru','uz'):
            try:
                with tempfile.TemporaryDirectory() as d:
                    t=time.monotonic(); path=Voice(lang).speak(next(x['text'] for x in manifest if x['language']==lang),Path(d)); report['tts'][lang]={'status':'generated','seconds':round(time.monotonic()-t,3),'bytes':path.stat().st_size}
            except Exception as exc: report['tts'][lang]={'status':'unavailable','errorType':type(exc).__name__}
    # macOS reports bytes; Linux reports KiB. This is peak per child, not total host memory.
    peak=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    report['peakChildRSSBytes']=int(peak if sys.platform=='darwin' else peak*1024)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0 if all(v['complete'] for v in summary.values()) else 2

if __name__=='__main__': raise SystemExit(main())
