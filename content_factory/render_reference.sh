#!/bin/bash
# Render an existing approved-style component with the installed studio toolchain.
set -euo pipefail
studio=${IUMRAH_STUDIO:-"$HOME/Documents/IUMRAH-CONTENT"}
destination=${1:?Usage: render_reference.sh /absolute/path/to/new.mp4}
[[ "$destination" = /* && "$destination" = *.mp4 && ! -e "$destination" ]] || { echo "Use a new absolute .mp4 path" >&2; exit 2; }
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
cd "$studio/tools/remotion"
# Limit the bundle to the brand assets required by this composition.
mkdir -p "$scratch/public/fonts"
cp public/header-wordmark-dark.png public/header-wordmark-light.png "$scratch/public/"
cp public/fonts/Inter-opsz-wght.ttf public/fonts/Nunito-wght.ttf "$scratch/public/fonts/"
nice -n 10 node_modules/.bin/remotion render src/index.ts FEM-8-BrandOutro "$scratch/render.mp4" --public-dir="$scratch/public" --concurrency=1 --codec=h264 --pixel-format=yuv420p --log=error
ffmpeg -nostdin -v error -xerror -i "$scratch/render.mp4" -f null -
# Exclusive destination creation, including concurrent invocations.
python3 - "$scratch/render.mp4" "$destination" <<'PY'
import os, shutil, sys, tempfile
from pathlib import Path
target = Path(sys.argv[2])
with tempfile.NamedTemporaryFile(dir=target.parent) as temp, open(sys.argv[1], 'rb') as source:
    shutil.copyfileobj(source, temp)
    temp.flush()
    os.fsync(temp.fileno())
    os.link(temp.name, target)
PY
