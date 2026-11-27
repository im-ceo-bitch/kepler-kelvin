#!/bin/bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/../.."
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
[[ "$(uname -s)" == Darwin ]] || { echo 'This installer requires macOS.'; exit 1; }
[[ "$(id -u)" != 0 ]] || { echo 'Run as your normal Mac user, not sudo.'; exit 1; }
major="$(sw_vers -productVersion | cut -d. -f1)"
[[ "$major" -ge 14 ]] || { echo 'Ollama requires macOS 14 or newer.'; exit 1; }
for cmd in uv ffmpeg git; do
  command -v "$cmd" >/dev/null || { echo "Missing $cmd. Install uv and ffmpeg (brew install uv ffmpeg), and Xcode Command Line Tools (xcode-select --install) if needed."; exit 1; }
done
OLLAMA="$(command -v ollama || true)"
if [[ -z "$OLLAMA" && -x /Applications/Ollama.app/Contents/Resources/ollama ]]; then OLLAMA=/Applications/Ollama.app/Contents/Resources/ollama; fi
[[ -n "$OLLAMA" ]] || { echo 'Install Ollama for macOS from https://ollama.com/download/mac then rerun.'; exit 1; }
# Stop on any failed dependency installation; do not enable a broken service.
uv sync --python 3.11 --extra speech --no-dev
uv pip install python-dotenv
PY="$PWD/.venv/bin/python"
"$PY" -m unittest founder_jarvis.test_runtime founder_jarvis.test_macos -v
"$PY" -c 'import telegram, dotenv, faster_whisper, openjarvis'
"$PY" founder_jarvis/macos/service.py config "$PY"
"$PY" founder_jarvis/macos/service.py ollama "$OLLAMA"
for i in $(seq 1 45); do
  if /usr/bin/curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then break; fi
  sleep 2
done
/usr/bin/curl -fsS --max-time 5 http://127.0.0.1:11434/api/tags >/dev/null
MODEL="$("$PY" -c 'from dotenv import dotenv_values; from pathlib import Path; print(dotenv_values(Path.home()/"Library/Application Support/Kelvin/runtime.env").get("JARVIS_MODEL","qwen2.5:3b"))')"
OLLAMA_HOST=127.0.0.1:11434 "$OLLAMA" pull "$MODEL"
# Real inference and speech round-trip before enabling the Telegram process.
"$PY" -m founder_jarvis.macos.smoke
"$PY" founder_jarvis/macos/service.py runtime "$PY"
echo 'Kelvin LaunchAgent installed. Send /start and /health to the bot, then test text and voice.'
echo 'For AC idle sleep prevention, run: sudo pmset -c sleep 0 displaysleep 5'
echo 'Leave the lid open, power connected, and your macOS user logged in.'
