#!/usr/bin/env bash
# Assemble the AppDir (the tree that becomes the AppImage).
# Run inside the "esbuild" distrobox (Ubuntu 22.04) after build-es.sh:
#   distrobox enter esbuild -- bash scripts/build-appdir.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${WORK:-$HOME/rbl}"
A="${APPDIR_OUT:-$WORK/AppDir}"
ES_SRC="$WORK/src/es"
BL="$WORK/src/batocera.linux"
DEPS="$WORK/deps"
PY_TGZ="$DEPS/cpython-3.14.10+20261110-x86_64-unknown-linux-gnu-install_only.tar.gz"
PY_SHA=3fe0d7c0538eb5d190c34582992d26230532551355cbd789fabc6591621cfc07
HK=package/batocera/utils/hotkeygen

command -v patchelf >/dev/null || sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq patchelf
# Windows Arcade Loader: cabextract, unzip for winetricks (its Wine prefix; few distros ship
# cabextract), squashfuse and fuse-overlayfs to mount .squashfs games without root
for t in cabextract unzip squashfuse fuse-overlayfs; do
  command -v $t >/dev/null || sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $t
done
echo "$PY_SHA  $PY_TGZ" | sha256sum -c --quiet -

rm -rf "$A"; mkdir -p "$A/usr/bin" "$A/usr/lib" "$A/usr/share" "$A/etc"

# Libraries every desktop provides, or that must match the host's GPU driver /
# sound server / C++ runtime. Never bundled (after the AppImage project's excludelist).
EXCLUDE='^(linux-vdso|ld-linux|libc\.|libm\.|libdl\.|libpthread|librt\.|libresolv|libutil\.|libmvec\.|libGL\.so|libGLX|libGLdispatch|libEGL|libOpenGL|libdrm|libgbm|libX11|libxcb|libXau|libXdmcp|libXext|libXrender|libXfixes|libXi\.|libasound|libpulse|libdbus-1|libudev|libsystemd|libstdc\+\+|libgcc_s|libfontconfig|libexpat|libwayland|libvulkan|libharfbuzz)'

bundle_deps() {  # copy the non-excluded shared-library deps of "$@" into usr/lib
  for f in "$@"; do
    # deps/ffmpeg first: minimal FFmpeg (build-ffmpeg-min.sh) replaces Ubuntu's codec-heavy one
    LD_LIBRARY_PATH="$DEPS/ffmpeg/lib:$DEPS/usr/lib" ldd "$f" 2>/dev/null | awk '$3 ~ /^\// {print $1, $3}'
  done | sort -u | while read -r name path; do
    [[ "$name" =~ $EXCLUDE ]] && continue
    [ -e "$A/usr/lib/$name" ] || cp -L "$path" "$A/usr/lib/$name"
  done
}

# --- tools the Windows Arcade Loader runs (winetricks, .squashfs games) ---
for t in cabextract unzip squashfuse fuse-overlayfs; do
  cp -L "$(command -v $t)" "$A/usr/bin/"
  bundle_deps "$A/usr/bin/$t"
  patchelf --set-rpath '$ORIGIN/../lib' "$A/usr/bin/$t"
done

# --- EmulationStation ---
cp "$ES_SRC/emulationstation" "$A/usr/bin/"
strip "$A/usr/bin/emulationstation"
bundle_deps "$A/usr/bin/emulationstation"
# SDL3 for the launcher's controller hotplug watcher (loaded by batocera_common/sdl3.py)
cp -L "$DEPS/usr/lib/libSDL3.so.0" "$A/usr/lib/"
bundle_deps "$A/usr/lib/libSDL3.so.0"
# VLC (video previews): plugins + whatever they link against
VLC_PLUGINS=/usr/lib/x86_64-linux-gnu/vlc/plugins
mkdir -p "$A/usr/lib/vlc/plugins"
# only what playing a video preview needs (local file -> demux -> decode -> GL/audio out)
for g in audio_filter audio_mixer audio_output packetizer video_chroma video_output demux logger; do
  cp -r "$VLC_PLUGINS/$g" "$A/usr/lib/vlc/plugins/"
done
mkdir -p "$A/usr/lib/vlc/plugins/access" "$A/usr/lib/vlc/plugins/codec"
cp "$VLC_PLUGINS/access/libfilesystem_plugin.so" "$A/usr/lib/vlc/plugins/access/"
for c in avcodec vorbis opus mpg123 flac a52 lpcm araw rawvideo theora; do
  cp "$VLC_PLUGINS/codec/lib${c}_plugin.so" "$A/usr/lib/vlc/plugins/codec/" 2>/dev/null || true
done
rm -f "$A"/usr/lib/vlc/plugins/demux/lib{vobsub,mod,sid,gme,adaptive,real}_plugin.so
bundle_deps $(find "$A/usr/lib/vlc/plugins" -name '*.so')
find "$A/usr/lib" -name '*.so*' -type f -exec strip --strip-unneeded {} + 2>/dev/null || true
patchelf --set-rpath '$ORIGIN/../lib' "$A/usr/bin/emulationstation"
for l in "$A"/usr/lib/*.so*; do patchelf --set-rpath '$ORIGIN' "$l" 2>/dev/null || true; done
for l in $(find "$A/usr/lib/vlc/plugins" -name '*.so'); do patchelf --set-rpath '$ORIGIN/../../..' "$l" 2>/dev/null || true; done

mkdir -p "$A/usr/share/emulationstation/themes"
cp -r "$ES_SRC/resources" "$A/usr/share/emulationstation/"
# Batocera's controller database (Steam Deck, Steam Controller, keyboard, ~330 pads)
git -C "$BL" show HEAD:package/batocera/emulationstation/batocera-emulationstation/controllers/es_input.cfg \
  > "$A/usr/share/emulationstation/es_input.cfg"
# (packaging/es_input-extra.cfg, a remapped Steam Deck entry, is NOT merged: it made the
#  Deck's controls worse in testing on 2026-11-15. Batocera's mappings are used as-is.)
# Steam's virtual pads: under Steam (Game Mode, or any game Steam launches) every controller
# appears as "Microsoft X-Box 360 pad N" with Valve's ID 28de:11ff. Same buttons as an Xbox
# 360 pad, so Batocera's Xbox 360 mapping is reused; hotkey = Select, since Steam keeps the
# Guide/Steam button for itself.
python3 - "$A/usr/share/emulationstation/es_input.cfg" <<'PY'
import copy, sys, xml.etree.ElementTree as ET
path = sys.argv[1]
tree = ET.parse(path); root = tree.getroot()
src = root.find("inputConfig[@deviceGUID='030000005e0400008e02000014010000']")
assert src is not None, 'Xbox 360 mapping not found in es_input.cfg'
for n in range(8):
    c = copy.deepcopy(src)
    c.set('deviceName', f'Microsoft X-Box 360 pad {n}')
    c.set('deviceGUID', '03000000de280000ff11000001000000')
    hk = c.find("input[@name='hotkey']")
    hk.set('id', '6'); hk.set('code', '314')
    root.append(c)
tree.write(path, encoding='unicode', xml_declaration=True)
PY
THEME="$WORK/test/share/emulationstation/themes/es-theme-carbon"
[ -d "$THEME" ] || git clone -q --depth 1 https://github.com/fabricecaruso/es-theme-carbon.git "$THEME"
cp -r "$THEME" "$A/usr/share/emulationstation/themes/"
rm -rf "$A/usr/share/emulationstation/themes/es-theme-carbon/.git"
# AcroBato's additions to Carbon (art for systems it doesn't have: switch2 logo)
cp -r "$HERE/packaging/theme/es-theme-carbon/." "$A/usr/share/emulationstation/themes/es-theme-carbon/"

# --- Python + Batocera launcher ---
mkdir -p "$A/usr/python"
tar xzf "$PY_TGZ" -C "$A/usr/python" --strip-components=1
PY="$A/usr/python/bin/python3"
git -C "$BL" checkout -q -- python-src $HK
python3 "$HERE/scripts/relocate-launcher.py" "$BL/python-src" "$BL/$HK" | grep -E 'tweak|WARN|rewrote'
LAUNCH_PKGS=(python-batocera-common batocera-launch batocera-launch-libretro batocera-launch-libretro-mame
             batocera-launch-mame-common batocera-launch-mame batocera-launch-dolphin batocera-launch-pcsx2
             batocera-launch-rpcs3 batocera-launch-flycast)
# batocera-bezel-overlay (GTK bezels over standalone emulators) needs PyGObject: later.
# evdev from source with this system's gcc: PyPI's prebuilt evdev uses RELR relocations, which
# need glibc 2.36 and broke the launcher on Ubuntu 22.04 (our baseline, glibc 2.35).
# No pip cache: the home folder is shared with the build host, whose cached evdev was built
# by a newer compiler (same problem).
rm -rf "$HERE/packaging/systems/build" "$HERE"/packaging/systems/*.egg-info   # setuptools reuses stale builds
CC="gcc -pthread" LDSHARED="gcc -pthread -shared" "$PY" -m pip install -q --no-warn-script-location \
  --ignore-requires-python --no-binary evdev --no-cache-dir \
  "$BL/$HK" $(for p in "${LAUNCH_PKGS[@]}"; do echo "$BL/python-src/$p"; done) \
  "$HERE/packaging/systems"   # AcroBato's Switch / Switch 2 / PS5 emulators (acrobato_emulators)
find "$A/usr/python" -name '__pycache__' -prune -exec rm -rf {} +
P="$A/usr/python/lib"
rm -rf "$P"/python3.14/{test,idlelib,tkinter,turtledemo,ensurepip,lib2to3,config-3.14-*} \
       "$P"/{tcl*,tk*,itcl*,thread*,libtcl*,libtk*} "$P"/python3.14/lib-dynload/_tkinter* \
       "$A/usr/python/include" "$A/usr/python/share"
find "$A/usr/python" -name '*.so*' -exec strip --strip-unneeded {} + 2>/dev/null || true
strip --strip-unneeded "$A/usr/python/bin/python3.14"   # statically linked, ships unstripped (75 MB -> 30 MB)
rm -f "$A"/usr/python/bin/{idle3*,pydoc3*,2to3*}

# Launcher entry points as relocatable wrappers (pip's scripts have absolute shebangs).
mkwrap() {  # name module:function
  cat > "$A/usr/bin/$1" <<EOF
#!/bin/sh
exec "\$APPDIR/usr/python/bin/python3" -c 'import sys; from ${2%%:*} import ${2##*:} as m; sys.argv[0] = "$1"; sys.exit(m())' "\$@"
EOF
  chmod +x "$A/usr/bin/$1"
}
# ES runs batocera-launch for every game; ours first picks a bundled core when the
# default standalone emulator isn't downloaded (packaging/acrobato_launch.py)
cp "$HERE/packaging/acrobato_launch.py" "$("$PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')/"
mkwrap batocera-launch acrobato_launch:main
mkwrap hotkeygen hotkeygen.hotkeygen:main
mkwrap batocera-hotkeys hotkeygen.batocera_hotkeys:main
# controller combos (Hotkey+Start to quit, ...) -> hotkeygen; started per game by batocera-launch
bash "$HERE/scripts/stage-evmapy.sh" "$BL" "$("$PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
cp "$HERE/compat/bin/batocera-evmapy" "$HERE/compat/bin/acrobato-emukill" "$HERE/compat/bin/acrobato-watchdog" "$A/usr/bin/"

# --- data: launcher defaults, shaders, hotkeygen config, system list ---
bash "$HERE/scripts/stage-launcher-data.sh" "$BL" "$A/usr/share" "$A/etc"
# offer exactly the cores that were built (installed core name == Batocera's core definition name)
CORES="$(ls "$DEPS"/libretro/cores/*_libretro.so 2>/dev/null | xargs -rn1 basename | sed 's/_libretro\.so$//' | tr '\n' ' ')"
export CORES
bash "$HERE/scripts/gen-es-data.sh" "$BL" "$PY" "$A/usr/share"
"$PY" "$HERE/scripts/fix-defaults.py" "$A/usr/share"   # defaults -> bundled cores / downloadable emulators
"$PY" "$HERE/packaging/systems/add-systems.py" "$A/usr/share"   # Switch, Switch 2, PS5 (not in Batocera)
"$PY" -m pip uninstall -q -y batocera-es-system   # build-time only
"$PY" -m pip uninstall -q -y pip
find "$A/usr/python" -name '__pycache__' -prune -exec rm -rf {} +

# --- desktop stand-ins for Batocera OS commands ---
cp "$HERE/compat/bin/batocera-resolution" "$HERE/compat/bin/batocera-version" "$HERE/compat/bin/_noop" "$A/usr/bin/"
for c in batocera-flash-screen batocera-overlays batocera-mouse batocera-amd-tdp \
         batocera-services batocera-wheel-calibrator; do ln -sf _noop "$A/usr/bin/$c"; done
# emulator downloader (Updates & Downloads > Content Downloader)
cp "$HERE/compat/bin/batocera-store" "$A/usr/bin/"
install -D -m 0644 -t "$A/usr/share/acrobato" "$HERE/packaging/store/acrobato_store.py" "$HERE/packaging/store/emulators.json"
# scraper helper behind ES's LaunchBox / libretro / GameTDB scrapers (ExternalScraper.cpp)
install -D -m 0644 -t "$A/usr/share/acrobato" "$HERE/packaging/scraper/acrobato_scrape.py"
cat > "$A/usr/bin/acrobato-scrape" <<'EOF'
#!/bin/sh
exec "$APPDIR/usr/python/bin/python3" -I "$APPDIR/usr/share/acrobato/acrobato_scrape.py" "$@"
EOF
chmod +x "$A/usr/bin/acrobato-scrape"

# RetroArch (build-retroarch.sh) + cores (build-cores.sh), when built
if [ -x "$DEPS/retroarch/retroarch" ]; then
  cp "$DEPS/retroarch/retroarch" "$A/usr/bin/"
  bundle_deps "$A/usr/bin/retroarch"
  patchelf --set-rpath '$ORIGIN/../lib' "$A/usr/bin/retroarch"
fi
# RetroArch data (fetch-ra-data.sh): shaders Batocera's shader sets use, menu assets
RAD="$DEPS/ra-data"
if [ -d "$RAD/slang-shaders" ]; then
  SHP="$BL/package/batocera/emulators/retroarch/shaders"
  python3 "$HERE/scripts/stage-shaders.py" "$RAD/slang-shaders" "$RAD/glsl-shaders" \
    "$SHP/batocera-shaders/configs" "$A/usr/share/batocera/shaders" "$SHP/slang-shaders/presets"
fi
if [ -d "$RAD/retroarch-assets/ozone" ]; then
  # as retroarch-assets.mk, minus xmb (Batocera's config uses Ozone)
  mkdir -p "$A/usr/share/libretro/assets"
  cp -r "$RAD"/retroarch-assets/{ozone,rgui,glui,sounds} "$A/usr/share/libretro/assets/"
fi
if [ -d "$DEPS/libretro/cores" ]; then
  mkdir -p "$A/usr/lib/libretro" "$A/usr/share/libretro/info"
  cp "$DEPS"/libretro/cores/*_libretro.so "$A/usr/lib/libretro/"
  cp "$DEPS"/libretro/info/*.info "$A/usr/share/libretro/info/" 2>/dev/null || true
  bundle_deps "$A"/usr/lib/libretro/*.so
fi
# core data files (Batocera OS ships these in its image; AppRun links them into bios/)
CS="$DEPS/src/cores"
[ -d "$CS/dolphin/Data/Sys" ] && { mkdir -p "$A/usr/share/dolphin-emu"; cp -r "$CS/dolphin/Data/Sys" "$A/usr/share/dolphin-emu/"; }
[ -d "$CS/ppsspp/assets" ] && { mkdir -p "$A/usr/share/ppsspp"; cp -r "$CS/ppsspp/assets" "$A/usr/share/ppsspp/PPSSPP"; }
chmod +x "$A"/usr/bin/*

# final pass over everything bundled into usr/lib: strip, and find siblings via $ORIGIN
find "$A/usr/lib" -maxdepth 1 -name '*.so*' -type f -exec strip --strip-unneeded {} + 2>/dev/null || true
for l in "$A"/usr/lib/*.so* "$A"/usr/lib/libretro/*.so; do
  [ -f "$l" ] && [ ! -L "$l" ] && patchelf --set-rpath '$ORIGIN:$ORIGIN/..' "$l" 2>/dev/null || true
done

# --- AppRun, desktop entry, icon ---
cp "$HERE/packaging/AppRun" "$A/AppRun"; chmod +x "$A/AppRun"
cp "$HERE/packaging/app.desktop" "$A/acrobato.desktop"
bash "$HERE/packaging/branding/stage-branding.sh" "$A"

# No bundled games: Batocera's first-start homebrew is removed (redistribution permission isn't
# ours to assume). Each system folder keeps its _info.txt (file types, BIOS). ES shows all systems
# with a welcome message while the library is empty (apply-es-fixes.py).
find "$A/usr/share/batocera/datainit/roms" -mindepth 2 \( -type f ! -name '_info.txt' \) -delete
find "$A/usr/share/batocera/datainit/roms" -mindepth 2 -type d -empty -delete

# Third-party license texts + NOTICES.md (needs dpkg: run inside the build container)
python3 "$HERE/scripts/collect-licenses.py" "$A" "$WORK" "$BL" "$HERE"

du -sh "$A" "$A/usr/lib" "$A/usr/python" "$A/usr/share" | sed 's#'"$A"'#AppDir#'
