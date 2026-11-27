"""Local acceptance checks without consuming Telegram messages."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
from dotenv import dotenv_values
from founder_jarvis.runtime import config_file, execute_agent, Voice

def main():
    values=dotenv_values(Path.home()/'Library/Application Support/Kelvin/runtime.env')
    # Do not load the bot token into model/voice test process environment.
    for key in ('JARVIS_WHISPER_MODEL','JARVIS_MAC_VOICE'):
        if values.get(key): os.environ[key]=values[key]
    with TemporaryDirectory() as tmp:
        base=Path(tmp); work=base/'work'; work.mkdir(); home=base/'core'; home.mkdir()
        cfg=base/'agent.toml'; config_file(cfg,work)
        reply=execute_agent('ollama',values.get('JARVIS_MODEL','qwen2.5:3b'),'chat','Ответь: сколько будет 7 умножить на 8?',[],work,cfg,home)
        if '56' not in reply: raise SystemExit('Inference test failed; see model configuration.')
        print('PASS: OpenJarvis + Ollama inference',flush=True)
        v=Voice(values.get('JARVIS_LANGUAGE','ru'))
        p=v.speak('Привет. Проверка голосового сообщения.',base)
        if not v.transcribe(p).strip(): raise SystemExit('Speech test failed.')
        print('PASS: local TTS and nonempty speech recognition',flush=True)

if __name__=='__main__': main()
