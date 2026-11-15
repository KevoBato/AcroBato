#!/usr/bin/env bash
# Pack the AppDir into an AppImage with appimagetool (official release, checked
# against the sha256 digest GitHub publishes for it).
# Run on the build host after build-appdir.sh. Output: $WORK/out/AcroBato-x86_64.AppImage
set -euo pipefail
WORK="${WORK:-$HOME/rbl}"
TOOL="$WORK/deps/appimagetool-x86_64.AppImage"
TOOL_SHA=e8c1169c4af66c3184d7ee110713d4be04befe671fa358e2c1591ee840553b03
echo "$TOOL_SHA  $TOOL" | sha256sum -c --quiet -
mkdir -p "$WORK/out"
OUT="$WORK/out/AcroBato-x86_64.AppImage"
rm -f "$OUT"
ARCH=x86_64 "$TOOL" --no-appstream "$WORK/AppDir" "$OUT" >/dev/null
ls -la "$OUT"; sha256sum "$OUT"
