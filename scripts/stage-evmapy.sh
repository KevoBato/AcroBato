#!/usr/bin/env bash
# evmapy: turns controller combos (Hotkey+Start = exit, Hotkey+Y = save state, ...) into
# key presses that hotkeygen passes on to the running emulator. Same commit and patches
# as Batocera (package/batocera/utils/evmapy), paths moved from /var/run and /etc to
# $ES_RUN and $ES_ETC. Pure Python, so it is copied straight into site-packages.
# Usage: stage-evmapy.sh <batocera.linux checkout> <site-packages dir>
set -euo pipefail
BL="$1"; DEST="$2"
WORK="${WORK:-$HOME/rbl}"
SRC="$WORK/src/evmapy"
REV=bd65338c236cd30b4f2d7835733ea5d6b108b75d
PKG=package/batocera/utils/evmapy

[ -d "$SRC/.git" ] || git clone -q https://github.com/kempniu/evmapy.git "$SRC"
git -C "$SRC" fetch -q origin "$REV" 2>/dev/null || true
git -C "$SRC" checkout -q -f "$REV"
git -C "$SRC" clean -qfdx
sed -i -e 's+Michał Kępień+Michal Kepien+' "$SRC"/*.py "$SRC"/evmapy/*.py
for p in $(git -C "$BL" ls-tree --name-only HEAD "$PKG/" | grep '\.patch$' | sort); do
  git -C "$BL" show "HEAD:$p" | patch -s -p1 -d "$SRC"
done
# /var/run/evmapy -> $ES_RUN/evmapy (where batocera-launch writes the per-pad configs)
sed -i -e 's|"/var/run/evmapy|os.environ.get("ES_RUN", "/var/run") + "/evmapy|g' \
       -e 's|"/etc/evmapy.json"|os.environ.get("ES_ETC", "/etc") + "/evmapy.json"|g' \
       "$SRC"/evmapy/*.py
if grep -n '"/var/run\|"/etc/' "$SRC"/evmapy/*.py | grep -v 'os.environ.get'; then echo "stage-evmapy: unrelocated path" >&2; exit 1; fi
# Hotkey keys (KEY_EXIT, KEY_SAVE, ...) go straight to hotkeygen over D-Bus. On Batocera
# hotkeygen (root) reads evmapy's virtual keyboard; a desktop user can't read that device
# (it doesn't get the seat ACL), so the combo would go nowhere. Other keys still use uinput.
python3 - "$SRC/evmapy/multiplexer.py" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
old = '        if not self._uinput:\n            return\n        keys = evmapy.util.as_list(action[\'target\'])\n'
new = ('        keys = evmapy.util.as_list(action[\'target\'])\n'
       '        if _send_hotkey(keys, press):\n'
       '            return\n'
       '        if not self._uinput:\n'
       '            return\n')
assert s.count(old) == 1, 'evmapy multiplexer layout changed'
s = s.replace(old, new)
helper = '''

_HOTKEYS = None


def _send_hotkey(keys, press):
    """AcroBato: hand hotkeygen's keys to hotkeygen directly (see stage-evmapy.sh)."""
    global _HOTKEYS
    if _HOTKEYS is None:
        import json
        try:
            path = os.environ.get("ES_ETC", "/etc") + "/hotkeygen/default_mapping.conf"
            with open(path) as f:
                _HOTKEYS = json.load(f)
        except (OSError, ValueError):
            _HOTKEYS = {}
    if len(keys) != 1 or keys[0] not in _HOTKEYS:
        return False
    if press:
        import subprocess
        subprocess.Popen(["hotkeygen", "--send", _HOTKEYS[keys[0]]],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True
'''
marker = '\nclass Multiplexer'
assert s.count(marker) == 1
s = s.replace(marker, helper + '\n' + marker, 1)
open(p, 'w').write(s)
PY
for f in "$SRC"/evmapy/*.py; do
  grep -q 'os.environ' "$f" && ! grep -q '^import os' "$f" && sed -i '0,/^import /s//import os\nimport /' "$f"
done
rm -rf "$DEST/evmapy"
cp -r "$SRC/evmapy" "$DEST/"
echo "evmapy $REV staged"
