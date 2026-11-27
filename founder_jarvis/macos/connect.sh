#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
PY="$HOME/Library/Application Support/Kelvin/telegram-venv/bin/python"
exec "$PY" -m founder_jarvis.integrations "$@"
