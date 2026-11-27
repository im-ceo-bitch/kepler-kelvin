#!/bin/bash
set -euo pipefail
# Reuse Ollama.app if it is already running; take over if it shuts down.
while /usr/bin/curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; do /bin/sleep 15; done
exec "$1" serve
