#!/bin/bash
set -euo pipefail
DOMAIN="gui/$(id -u)"; LABEL=com.kelvin.manager
case "${1:-status}" in
  status) launchctl print "$DOMAIN/$LABEL"; launchctl print "$DOMAIN/com.kelvin.ollama" 2>/dev/null || true ;;
  restart) launchctl kickstart -k "$DOMAIN/$LABEL" ;;
  stop) launchctl bootout "$DOMAIN/$LABEL" ;;
  start) launchctl enable "$DOMAIN/$LABEL"; launchctl bootstrap "$DOMAIN" "$HOME/Library/LaunchAgents/$LABEL.plist" ;;
  logs) BASE="$HOME/Library/Application Support/Kelvin"
    LOG="$("$BASE/telegram-venv/bin/python" -c 'from pathlib import Path; from dotenv import dotenv_values; b=Path.home()/"Library/Application Support/Kelvin"; c=dotenv_values(b/"runtime.env"); print(Path(c.get("JARVIS_DATA_DIR") or b/"data").expanduser()/"logs/runtime.log")')"
    tail -n 80 -F "$LOG" ;;
  *) echo 'Usage: control.sh status|restart|stop|start|logs'; exit 1 ;;
esac
