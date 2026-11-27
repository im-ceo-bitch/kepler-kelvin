"""Owner-only local voice setting. Independent of model and shared chat memory."""
import json
import os
import tempfile
from pathlib import Path

class VoicePreferences:
    def __init__(self, path):
        self.path = Path(path)

    def load(self, default='ru'):
        default = default if default in ('ru', 'uz') else 'ru'
        try:
            value = json.loads(self.path.read_text())['language']
            return value if value in ('ru', 'uz') else default
        except (OSError, ValueError, KeyError, TypeError):
            return default

    def save(self, language):
        if language not in ('ru', 'uz'):
            raise ValueError('Unsupported voice language')
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.voice-language-', dir=self.path.parent)
        tmp = Path(name)
        try:
            with os.fdopen(fd, 'w') as file:
                json.dump({'language': language}, file)
                file.flush(); os.fsync(file.fileno())
            tmp.replace(self.path)
        finally:
            tmp.unlink(missing_ok=True)
