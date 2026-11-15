#!/usr/bin/env bash
# Dev loop for the launcher: relocate Batocera's sources, (re)install them into
# a venv, and stage their data files. Run inside the "pydev" distrobox (Arch,
# Python 3.14):   distrobox enter pydev -- bash scripts/dev-setup-launcher.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${WORK:-$HOME/rbl}"
BL="$WORK/src/batocera.linux"
VENV="$WORK/venv"
TEST="$WORK/test"
HK=package/batocera/utils/hotkeygen

if [ ! -d "$BL" ]; then
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/batocera-linux/batocera.linux.git "$BL"
  git -C "$BL" sparse-checkout set python-src $HK package/batocera/core/batocera-system \
    package/batocera/emulators/retroarch/shaders
fi

cd "$BL"
git checkout -q -- python-src $HK
python3 "$HERE/scripts/relocate-launcher.py" python-src $HK | grep -vE '^\s+TODO' || true

[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --ignore-requires-python \
  ./python-src/python-batocera-common ./$HK ./python-src/batocera-launch ./python-src/batocera-launch-libretro
# reinstall our own packages even when the version number didn't change
"$VENV/bin/pip" install -q --ignore-requires-python --force-reinstall --no-deps \
  ./python-src/python-batocera-common ./$HK ./python-src/batocera-launch ./python-src/batocera-launch-libretro

bash "$HERE/scripts/stage-launcher-data.sh" "$BL" "$TEST/share" "$TEST/etc"
mkdir -p "$TEST/userdata/system"
[ -f "$TEST/userdata/system/batocera.conf" ] || cp "$TEST/share/batocera/datainit/system/batocera.conf" "$TEST/userdata/system/"
echo "launcher ready in $VENV"
