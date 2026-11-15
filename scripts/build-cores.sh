#!/usr/bin/env bash
# Build the bundled libretro cores from source at the versions Batocera pins
# (VERSION/SITE, *.patch and the installed file name come from
#  package/batocera/emulators/retroarch/libretro/libretro-<pkg>/libretro-<pkg>.mk).
# Run inside the "esbuild" distrobox. Output: $WORK/deps/libretro/{cores,info}
# Usage: build-cores.sh [pkg ...]   (default: every core in the table)
set -uo pipefail
WORK="${WORK:-$HOME/rbl}"
BL="$WORK/src/batocera.linux"
L="$BL/package/batocera/emulators/retroarch/libretro"
SRC="$WORK/deps/src/cores"
OUT="$WORK/deps/libretro"
mkdir -p "$SRC" "$OUT/cores" "$OUT/info"

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nasm libpcap-dev libevdev-dev libbluetooth-dev \
  libusb-1.0-0-dev libenet-dev libcurl4-openssl-dev libboost-dev libzstd-dev liblzma-dev libgl1-mesa-dev \
  libegl1-mesa-dev libvulkan-dev libx11-dev libxrandr-dev libxi-dev libudev-dev zlib1g-dev \
  gcc-12 g++-12 libglew-dev >/dev/null

# Ubuntu 22.04's CMake (3.22) is too old for Dolphin (needs 3.25+): use Kitware's PyPI build
[ -x "$HOME/.local/bin/cmake" ] || { sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-pip >/dev/null;
                                     python3 -m pip install -q --user cmake==3.31.6; }
CMAKE="$HOME/.local/bin/cmake"

# pkg | build dir | Makefile name or CMAKE | .so the build produces | extra make args
TABLE='
fceumm          | .                            | Makefile.libretro | fceumm_libretro.so            |
nestopia        | libretro                     | Makefile          | nestopia_libretro.so          |
snes9x          | libretro                     | Makefile          | snes9x_libretro.so            |
genesisplusgx   | .                            | Makefile.libretro | genesis_plus_gx_libretro.so   |
picodrive       | .                            | Makefile.libretro | picodrive_libretro.so         |
gambatte        | .                            | Makefile          | gambatte_libretro.so          |
mgba            | .                            | CMAKE             | mgba_libretro.so              |
pcsx            | .                            | Makefile.libretro | pcsx_rearmed_libretro.so      |
stella2014      | .                            | Makefile          | stella2014_libretro.so        |
handy           | .                            | Makefile          | handy_libretro.so             |
beetle-ngp      | .                            | Makefile          | mednafen_ngp_libretro.so      |
beetle-wswan    | .                            | Makefile          | mednafen_wswan_libretro.so    |
beetle-pce-fast | .                            | Makefile          | mednafen_pce_fast_libretro.so |
prosystem       | .                            | Makefile          | prosystem_libretro.so         |
vecx            | .                            | Makefile          | vecx_libretro.so              |
melonds         | .                            | Makefile          | melonds_libretro.so           | LDFLAGS=-lrt
desmume         | desmume/src/frontend/libretro| Makefile          | desmume_libretro.so           |
dolphin         | .                            | CMAKE             | dolphin_libretro.so           |
mupen64plus-next| .                            | Makefile          | mupen64plus_next_libretro.so  |
parallel-n64    | .                            | Makefile          | parallel_n64_libretro.so      |
ppsspp          | .                            | CMAKE             | ppsspp_libretro.so            |
flycast         | .                            | CMAKE             | flycast_libretro.so           |
swanstation     | .                            | CMAKE             | swanstation_libretro.so       |
fbneo           | src/burner/libretro          | Makefile          | fbneo_libretro.so             |
beetle-saturn   | .                            | Makefile          | mednafen_saturn_hw_libretro.so| HAVE_OPENGL=1
dosbox-pure     | .                            | Makefile          | dosbox_pure_libretro.so       |
opera           | .                            | Makefile          | opera_libretro.so             |
neocd           | .                            | Makefile          | neocd_libretro.so             |
bluemsx         | .                            | Makefile.libretro | bluemsx_libretro.so           |
puae            | .                            | Makefile          | puae_libretro.so              |
'

# CMake options per core (from each recipe, desktop x86_64 branches chosen)
declare -A CMAKE_OPTS=(
  [mgba]="-DBUILD_LIBRETRO=ON -DSKIP_LIBRARY=ON -DBUILD_QT=OFF -DBUILD_SDL=OFF -DUSE_DISCORD_RPC=OFF"
  [dolphin]="-DBUILD_SHARED_LIBS=OFF -DCMAKE_CXX_FLAGS=-fpermissive -DLIBRETRO=ON -DLINUX=ON -DENABLE_NOGUI=OFF -DENABLE_QT=OFF -DENABLE_TESTS=OFF -DUSE_DISCORD_PRESENCE=OFF -DUSE_SYSTEM_XXHASH=OFF -DUSE_SYSTEM_SPNG=OFF -DUSE_SYSTEM_HIDAPI=OFF -DENABLE_X11=ON"
  [ppsspp]="-DBUILD_SHARED_LIBS=OFF -DLIBRETRO=ON -DANDROID=OFF -DWIN32=OFF -DUSING_X11_VULKAN=ON -DUSE_DISCORD=OFF"
  [flycast]="-DBUILD_SHARED_LIBS=OFF -DLIBRETRO=ON -DUSE_OPENMP=ON -DBUILD_EXTERNAL=OFF -DUSE_DX9=OFF -DUSE_VULKAN=ON"
  [swanstation]="-DBUILD_SHARED_LIBS=FALSE -DUSE_WAYLAND=ON -DUSE_X11=ON -DUSE_GLX=ON -DUSE_EGL=ON"
)

# compilers per core (default: the distro's GCC 11). Dolphin requires GCC 12; Ubuntu
# 22.04's libstdc++ is already from GCC 12, so this doesn't raise the runtime requirement.
declare -A CMAKE_ENV=(
  [dolphin]="CC=gcc-12 CXX=g++-12"
)

want=("$@")
ok=(); failed=()
while IFS='|' read -r pkg dir mkf so extra; do
  pkg=$(echo $pkg); dir=$(echo $dir); mkf=$(echo $mkf); so=$(echo $so); extra=$(echo $extra)
  [ -z "$pkg" ] && continue
  if [ ${#want[@]} -gt 0 ] && [[ ! " ${want[*]} " =~ " $pkg " ]]; then continue; fi
  mk="$L/libretro-$pkg/libretro-$pkg.mk"
  [ -f "$mk" ] || { failed+=("$pkg(no recipe)"); continue; }
  var=$(echo "LIBRETRO_${pkg}" | tr 'a-z-' 'A-Z_')
  ver=$(sed -n "s/^${var}_VERSION *= *//p" "$mk")
  # SITE may continue on the next line ("_SITE = \"); only then join it
  site=$(awk -v v="${var}_SITE" '$1 == v && ($2 == "=" || $2 ~ /^=/) {
           line = $0; sub(/^[^=]*= */, "", line)
           if (line ~ /\\$/) { sub(/\\$/, "", line); getline nxt; line = line nxt }
           print line; exit }' "$mk")
  if [[ "$site" =~ github,([^,]+),([^,]+), ]]; then url="https://github.com/${BASH_REMATCH[1]}/${BASH_REMATCH[2]}.git"
  else url=$(echo "$site" | grep -oE 'https://[^ ]+' | head -1); fi
  # the name Batocera installs it under (what batocera-launch looks for)
  inst=$(grep -oE '/usr/lib/libretro/[^ ]+_libretro\.so' "$mk" | head -1 | xargs -r basename)
  inst=${inst:-$so}
  if [ -f "$OUT/cores/$inst" ] && [ "$(cat "$OUT/cores/$inst.version" 2>/dev/null)" = "$ver" ]; then ok+=("$pkg(cached)"); continue; fi
  echo ">>> $pkg $ver -> $inst"
  d="$SRC/$pkg"
  if [ ! -d "$d/.git" ] || [ "$(git -C "$d" remote get-url origin 2>/dev/null)" != "$url" ]; then
    rm -rf "$d"; git init -q "$d"; git -C "$d" remote add origin "$url"
  fi
  # submodules only when the recipe asks for them (others are built from the plain source tree)
  subs=no; grep -qE "^${var}_GIT_SUBMODULES *= *YES" "$mk" && subs=yes
  fetched=no
  for attempt in 1 2 3; do   # large submodules (e.g. PPSSPP's ffmpeg) sometimes stall
    if ( cd "$d" && G="git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=300" &&
         $G fetch -q --depth 1 origin "$ver" && git checkout -q -f FETCH_HEAD && git clean -qfdx &&
         { [ "$subs" = no ] || $G submodule -q update --init --depth 1 --recursive; } ); then fetched=yes; break; fi
    echo "    fetch attempt $attempt failed, retrying"
  done
  [ "$fetched" = yes ] || { failed+=("$pkg(fetch)"); continue; }
  for p in "$L/libretro-$pkg"/*.patch; do [ -f "$p" ] && (cd "$d" && patch -p1 --forward --silent < "$p" >/dev/null 2>&1); done
  if [ "$mkf" = CMAKE ]; then
    build() { env ${CMAKE_ENV[$pkg]:-} "$CMAKE" -S "$d/$dir" -B "$d/build" -DCMAKE_BUILD_TYPE=Release ${CMAKE_OPTS[$pkg]:-} >"$d/build.log" 2>&1 &&
              "$CMAKE" --build "$d/build" -j"$(nproc)" >>"$d/build.log" 2>&1; }
  else
    build() { make -C "$d/$dir" -f "$mkf" platform=unix $extra -j"$(nproc)" >"$d/build.log" 2>&1; }
  fi
  if build; then
    f=$(find "$d" -name "$so" -type f | head -1)
    if [ -n "$f" ]; then
      strip --strip-unneeded "$f"; cp "$f" "$OUT/cores/$inst"; echo "$ver" > "$OUT/cores/$inst.version"
      [ "$so" != "$inst" ] && rm -f "$OUT/cores/$so" "$OUT/cores/$so.version"
      ok+=("$pkg")
    else failed+=("$pkg(no .so)"); fi
  else
    failed+=("$pkg(build: see $d/build.log)")
  fi
done <<< "$TABLE"

# core .info files (display names, extensions, firmware lists), named like the installed cores
INFO="$SRC/libretro-core-info"
[ -d "$INFO" ] || git clone -q --depth 1 https://github.com/libretro/libretro-core-info.git "$INFO"
while IFS='|' read -r pkg dir mkf so extra; do
  so=$(echo $so); [ -z "$so" ] && continue
  pkg=$(echo $pkg); mk="$L/libretro-$pkg/libretro-$pkg.mk"
  inst=$(grep -oE '/usr/lib/libretro/[^ ]+_libretro\.so' "$mk" 2>/dev/null | head -1 | xargs -r basename); inst=${inst:-$so}
  [ -f "$OUT/cores/$inst" ] && [ -f "$INFO/${so%.so}.info" ] && cp "$INFO/${so%.so}.info" "$OUT/info/${inst%.so}.info"
done <<< "$TABLE"
[ -f "$SRC/nestopia/NstDatabase.xml" ] && cp "$SRC/nestopia/NstDatabase.xml" "$OUT/"

echo "built: ${ok[*]}"
[ ${#failed[@]} -eq 0 ] || echo "FAILED: ${failed[*]}"
du -sh "$OUT/cores"
