#!/usr/bin/env bash
# Stage batocera-launch's data files into $SHARE (what ES_SHARE points at),
# mirroring the install steps in python-src/batocera-launch/batocera-launch.mk
# and batocera-launch-libretro.mk for an x86_64 target.
# Usage: stage-launcher-data.sh <batocera.linux checkout> <share dir> [etc dir, default <share>/../etc]
set -euo pipefail
SRC="$1/python-src"
SHARE="$2"
L="$SHARE/batocera/launch"

install -D -m 0644 "$SRC/batocera-launch/resources/defaults/config.yml" "$L/defaults/config.yml"
install -D -m 0644 "$SRC/batocera-launch/resources/defaults/config-x86_64.yml" "$L/defaults/config-arch.yml"
install -D -m 0644 -t "$L/data" "$SRC/batocera-launch/resources/data/gamesbuttonsdb.xml"
install -D -m 0644 -t "$L/data/special" "$SRC"/batocera-launch/resources/data/special/*.toml
# MAME (libretro and standalone): ROM and control data (batocera-launch-mame-common.mk)
install -D -m 0644 -t "$L/data/mame" "$SRC"/batocera-launch-mame-common/resources/*.toml
install -D -m 0644 -t "$SHARE/evmapy" "$SRC/batocera-launch/resources/hotkeys.keys"
install -D -m 0755 -t "$L" "$SRC/batocera-launch-libretro/resources/scripts/call_achievements_hooks.sh"
echo x86_64 > "$SHARE/batocera/batocera.arch"
# shader set definitions (batocera-shaders.mk, BATOCERA_GPU=x86). The actual
# .slangp/.glslp shader files come from libretro's slang/glsl shader packs and
# are bundled separately (TODO for the AppImage).
SH="$1/package/batocera/emulators/retroarch/shaders/batocera-shaders"
C="$SHARE/batocera/shaders/configs"
mkdir -p "$C" "$SHARE/batocera/shaders/bezel/Mega_Bezel/Presets"
cp -R "$SH"/presets-batocera/* "$SHARE/batocera/shaders/bezel/Mega_Bezel/Presets/"
cp "$SH/configs/rendering-defaults.yml" "$C/"
[ -e "$SH/configs/rendering-defaults-x86.yml" ] && cp "$SH/configs/rendering-defaults-x86.yml" "$C/rendering-defaults-arch.yml"
for set in "$SH"/configs/*/; do
  set=$(basename "$set"); mkdir -p "$C/$set"
  cp "$SH/configs/$set/rendering-defaults.yml" "$C/$set/"
  [ -e "$SH/configs/$set/rendering-defaults-x86.yml" ] && cp "$SH/configs/$set/rendering-defaults-x86.yml" "$C/$set/rendering-defaults-arch.yml"
done

# hotkeygen daemon config (hotkeygen.mk); ETC is what ES_ETC points at
HK="$1/package/batocera/utils/hotkeygen/resources/config"
ETC="${3:-$SHARE/../etc}"
install -D -m 0644 -t "$ETC/hotkeygen" "$HK/default_context.conf" "$HK/common_context.conf" "$HK/default_mapping.conf"
install -D -m 0644 -t "$SHARE/hotkeygen" "$HK"/specific/*.mapping

# system-wide defaults (read-only) and the template for the user's batocera.conf
SYS="$1/package/batocera/core/batocera-system"
# sysconfigs/x86_64/batocera.conf.<DMI product name> are per-device overrides
# (Jupiter = Steam Deck LCD, Galileo = OLED). Shipped as-is; choosing one at
# runtime from /sys/class/dmi/id/product_name is still TODO, so the active
# sysconfig starts empty.
mkdir -p "$SHARE/batocera/sysconfigs"
cp "$SYS"/sysconfigs/x86_64/batocera.conf.* "$SHARE/batocera/sysconfigs/"
: > "$SHARE/batocera/sysconfigs/batocera.conf"
install -D -m 0644 "$SYS/batocera.conf" "$SHARE/batocera/datainit/system/batocera.conf"
echo "staged launcher data into $SHARE"
