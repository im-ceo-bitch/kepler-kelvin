#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
BASE="$HOME/Library/Application Support/Kelvin"
PY="$BASE/telegram-venv/bin/python"
[[ "$(uname -s)" == Darwin && "$(id -u)" != 0 ]] || { echo 'Run as your normal Mac user.'; exit 1; }
[[ -x "$PY" ]] || { echo 'Kelvin is not installed: bash founder_jarvis/macos/install.sh'; exit 1; }
"$PY" -m unittest founder_jarvis.test_shared_business -q
"$PY" -m founder_jarvis.shared_business
DOMAIN="gui/$(id -u)"
if launchctl print "$DOMAIN/com.kelvin.manager" >/dev/null 2>&1; then
    launchctl kickstart -k "$DOMAIN/com.kelvin.manager"
else
    bash founder_jarvis/macos/install.sh
fi
echo 'Check Kelvin in iumrah Business and Telegram /health.'
