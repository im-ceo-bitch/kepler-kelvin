#!/bin/bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/../.."
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
[[ "$(uname -s)" == Darwin && "$(id -u)" != 0 ]] || { echo 'Run on macOS as normal user, not sudo.'; exit 1; }
BASE="$HOME/Library/Application Support/Kelvin"
mkdir -p "$BASE"; chmod 700 "$BASE"
stage() { printf '%s\n' "$1" > "$BASE/install-status.txt"; echo "Kelvin Strategic Advisor: $1"; }
trap 'stage "Installation failed at line $LINENO; see terminal."' ERR
export KELVIN_CLAUDE_BIN="$(command -v claude)"
[[ -x "$KELVIN_CLAUDE_BIN" ]] || { echo 'Claude Code not found in PATH'; exit 1; }
stage 'Preparing Telegram environment'
uv venv --allow-existing --python 3.11 "$BASE/telegram-venv"
PY="$BASE/telegram-venv/bin/python"
uv pip install --python "$PY" 'python-telegram-bot==22.8' 'python-dotenv>=1,<2'
"$PY" -m unittest founder_jarvis.test_runtime founder_jarvis.test_macos founder_jarvis.test_recovery founder_jarvis.test_claude founder_jarvis.test_v4 founder_jarvis.test_v5 founder_jarvis.test_shared_business founder_jarvis.test_thinking founder_jarvis.test_advisor -v
stage 'Verifying original OpenJarvis agent'
CORE="$PWD/.venv/bin/python"
if [[ ! -x "$CORE" ]]; then uv venv --allow-existing --python 3.11 "$PWD/.venv"; fi
if ! PYTHONPATH="$PWD/src:$PWD" "$CORE" -c 'import httpx; from founder_jarvis.native_advisor import answer'; then
    uv pip install --python "$CORE" 'httpx>=0.27,<1'
fi
PYTHONPATH="$PWD/src:$PWD" "$CORE" -m unittest founder_jarvis.test_native_advisor -v
"$PY" founder_jarvis/macos/service.py config "$PY"
stage 'Starting Telegram service with Claude Code'
"$PY" founder_jarvis/macos/service.py runtime "$PY"
stage 'Telegram service registered; verify Claude and voice via Telegram /health and /voice'
echo 'See KELVIN-STRATEGIC-ADVISOR.md. No secret re-entry required for private Telegram.'
echo 'Existing local model and speech dependencies retained. No Ollama download required.'
echo 'Keep Mac logged in, connected to AC, lid open; sudo pmset -c sleep 0 displaysleep 5'
