#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v uv >/dev/null || { echo 'Install uv first'; exit 1; }
if [ ! -f .env ]; then echo 'Copy .env.example to .env and configure owner and bot token'; exit 1; fi
uv sync --python 3.11 --extra speech
uv pip install python-dotenv
exec uv run --no-sync python -m founder_jarvis.runtime
