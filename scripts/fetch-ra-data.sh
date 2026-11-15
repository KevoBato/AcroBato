#!/usr/bin/env bash
# Fetch RetroArch data at the versions Batocera pins: slang/glsl shader packs
# and the menu assets (Ozone). Output under $WORK/deps/ra-data.
set -euo pipefail
WORK="${WORK:-$HOME/rbl}"
BL="$WORK/src/batocera.linux"
SH="$BL/package/batocera/emulators/retroarch/shaders"
OUT="$WORK/deps/ra-data"
mkdir -p "$OUT"

fetch() {  # dir url commit
  if [ ! -d "$1/.git" ]; then git init -q "$1"; git -C "$1" remote add origin "$2"; fi
  git -C "$1" fetch -q --depth 1 origin "$3" && git -C "$1" checkout -q -f FETCH_HEAD
}
ver() { sed -n "s/^$1_VERSION = //p" "$2"; }

fetch "$OUT/slang-shaders" https://github.com/libretro/slang-shaders.git "$(ver SLANG_SHADERS "$SH/slang-shaders/slang-shaders.mk")"
fetch "$OUT/glsl-shaders"  https://github.com/libretro/glsl-shaders.git  "$(ver GLSL_SHADERS "$SH/glsl-shaders/glsl-shaders.mk")"

# Menu assets: Batocera's retroarch-assets recipe pins the version (read straight from git)
AV=$(git -C "$BL" show HEAD:package/batocera/emulators/retroarch/retroarch-assets/retroarch-assets.mk \
     | sed -n 's/^RETROARCH_ASSETS_VERSION = //p')
[ -n "$AV" ] || { echo "retroarch-assets version not found" >&2; exit 1; }
fetch "$OUT/retroarch-assets" https://github.com/libretro/retroarch-assets.git "$AV"
echo "fetched into $OUT"
