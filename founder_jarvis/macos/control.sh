#!/bin/bash
set -euo pipefail
DOMAIN="gui/$(id -u)"; LABEL=com.kelvin.manager
case "${1:-status}" in
  status) launchctl print "$DOMAIN/$LABEL"; launchctl print "$DOMAIN/com.kelvin.ollama" ;;
  restart) launchctl kickstart -k "$DOMAIN/$LABEL" ;;
  stop) launchctl bootout "$DOMAIN/$LABEL" ;;
  start) launchctl enable "$DOMAIN/$LABEL"; launchctl bootstrap "$DOMAIN" "$HOME/Library/LaunchAgents/$LABEL.plist" ;;
  logs) tail -n 80 -F "$HOME/Library/Application Support/Kelvin/logs/$LABEL.err.log" ;;
  *) echo 'Usage: control.sh status|restart|stop|start|logs'; exit 1 ;;
esac
