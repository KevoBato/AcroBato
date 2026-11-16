#!/usr/bin/env bash
# Generate es_systems.cfg, es_features.cfg and the default roms/ tree with
# Batocera's own generator (python-src/batocera-es-system), limited to the
# emulators this app ships or can download.
# Usage: gen-es-data.sh <batocera.linux checkout> <python with batocera-launch installed> <share dir>
set -euo pipefail
BL="$(cd "$1" && pwd)"; PY="$2"; SHARE="$3"
ESS="$BL/package/batocera/emulationstation/batocera-es-system"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

# Emulators offered: RetroArch (bundled) + the standalone ones in the downloader.
STANDALONE="pcsx2 dolphin-emu duckstation-common rpcs3 ppsspp cemu-common xemu azahar flycast melonds shadps4 vita3k
  supermodel hypseus-singe sm2-emu odin xemu-chihiro pcsx2x6 linuxloader"
# RetroArch cores bundled in the AppImage (build-cores.sh, last column of its table)
CORES="${CORES:-fceumm nestopia snes9x genesisplusgx picodrive gambatte mgba pcsx_rearmed stella2014 handy mednafen_ngp mednafen_wswan pce_fast prosystem vecx
  melonds desmume dolphin mupen64plus-next parallel_n64 ppsspp flycast swanstation fbneo beetle-saturn dosbox_pure opera neocd bluemsx puae
  vice_x64 vice_xplus4 vice_x128 vice_xvic vice_xpet tgbdual vb gearsystem mednafen_supergrafx pcfx atari800 prboom tyrquake
  mrboom fake08 lowresnx freechaf lutro nxengine cap32 o2em 81 fuse virtualjaguar freeintv px68k x1 pokemini theodore quasi88
  np2kai potator pd777 emuscv superbroswar zc210 vemulator xrick reminiscence hatari tic80 wasm4 vircon32 arduous bennugd}"

# RetroArch cores offered in the Content Downloader (packaging/store/emulators.json, source type
# "libretro"): their systems are listed too. Also their variants (sega-arcade.mame for mame).
DOWNLOAD_CORES="$(python3 -c 'import json,sys; print(" ".join(e["source"]["core"] for e in json.load(open(sys.argv[1]))["emulators"] if e["source"]["type"] == "libretro"))' \
  "$(dirname "$0")/../packaging/store/emulators.json")"
echo "downloadable cores: $DOWNLOAD_CORES"

{
  for f in _shared _global sh tdp._shared hud._shared; do echo "$ESS/$f.emulator.yml"; done
  find "$BL/package/batocera/emulators/retroarch/retroarch" -name '*.emulator.yml'
  for c in $CORES; do find "$BL/package/batocera" -name "$c.libretro.core.yml"; done
  for c in $DOWNLOAD_CORES; do find "$BL/package/batocera" \( -name "$c.libretro.core.yml" -o -name "*.$c.libretro.core.yml" \); done
  for e in $STANDALONE; do find "$BL/package/batocera" -path "*/$e/*" -name '*.emulator.yml'; done
} | sort -u | tr '\n' ' ' > "$OUT/info_files.txt"
echo "using $(wc -w < "$OUT/info_files.txt") emulator definition files"

"$PY" -m pip install -q --ignore-requires-python --no-deps "$BL/python-src/batocera-es-system"
cp -pr "$ESS/locales" "$OUT/"
"$PY" -c 'import sys; from batocera_es_system.build_es_data import main; sys.argv[0]="batocera-build-es-data"; main()' \
  --es-systems-yml="$ESS/es_systems.yml" \
  --locales-dir="$ESS/locales" \
  --roms-dir="$ESS/roms" \
  --defaults="$SHARE/batocera/launch/defaults" \
  --keys-dir="$BL/package/batocera" \
  --output="$OUT" \
  --arch=x86_64 \
  "$OUT/info_files.txt"

install -D -m 0644 "$OUT/es_systems.cfg" "$SHARE/emulationstation/es_systems.cfg"
install -D -m 0644 "$OUT/es_features.cfg" "$SHARE/emulationstation/es_features.cfg"
rm -rf "$SHARE/batocera/datainit/roms"; mkdir -p "$SHARE/batocera/datainit"
cp -pr "$OUT/roms" "$SHARE/batocera/datainit/"
echo "systems: $(grep -c '<system>' "$SHARE/emulationstation/es_systems.cfg")"
