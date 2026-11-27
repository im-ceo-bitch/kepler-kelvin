"""Isolated speech subprocess for the optional local speech environment."""
import json
import os
import sys
from faster_whisper import WhisperModel

if __name__ == '__main__':
    model = WhisperModel(os.getenv('JARVIS_WHISPER_MODEL','base'), device='cpu', compute_type='int8', cpu_threads=2)
    segments, _ = model.transcribe(sys.argv[1], language=sys.argv[2] or None, vad_filter=True)
    print(json.dumps({'text': ' '.join(s.text.strip() for s in segments).strip()}, ensure_ascii=False))
