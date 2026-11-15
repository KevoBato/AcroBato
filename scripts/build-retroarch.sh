#!/usr/bin/env bash
# Build RetroArch at the commit Batocera pins, with Batocera's patches, for a
# generic x86_64 desktop. Run inside the "esbuild" distrobox.
# Output: $WORK/deps/retroarch/retroarch
set -euo pipefail
WORK="${WORK:-$HOME/rbl}"
BL="$WORK/src/batocera.linux"
PKG="$BL/package/batocera/emulators/retroarch/retroarch"
VER=$(sed -n 's/^RETROARCH_VERSION = //p' "$PKG/retroarch.mk")
SRC="$WORK/deps/src/retroarch"
OUT="$WORK/deps/retroarch"

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  libudev-dev libdrm-dev libgbm-dev libegl1-mesa-dev libgl1-mesa-dev libvulkan-dev \
  libwayland-dev wayland-protocols libxkbcommon-dev libx11-dev libxext-dev libxinerama-dev \
  libxrandr-dev libxxf86vm-dev libpulse-dev libasound2-dev libfreetype6-dev zlib1g-dev \
  glslang-dev spirv-tools libx11-xcb-dev libxcb1-dev >/dev/null

if [ ! -d "$SRC/.git" ]; then
  git init -q "$SRC"; git -C "$SRC" remote add origin https://github.com/libretro/RetroArch.git
fi
cd "$SRC"
git fetch -q --depth 1 origin "$VER"
git checkout -q -f FETCH_HEAD && git clean -qfdx

failed=()
for p in "$PKG"/*.patch; do
  # 025 adapts linking to Batocera's system glslang; we use RetroArch's vendored copy instead
  case "$(basename "$p")" in 025-fix-glslang-linking.patch) continue ;; esac
  if ! patch -p1 --forward --silent < "$p" >/dev/null 2>&1; then failed+=("$(basename "$p")"); fi
done
[ ${#failed[@]} -eq 0 ] || echo "patches that did not apply (board-specific are expected): ${failed[*]}"

PKG_CONFIG_PATH="$WORK/deps/usr/lib/pkgconfig" ./configure --prefix=/usr \
  --disable-oss --disable-qt --enable-threads --enable-ozone --enable-xmb --enable-rgui \
  --disable-discord --enable-flac --enable-lua --enable-networking --enable-translate --disable-cdrom \
  --enable-zlib --disable-builtinzlib --disable-ffmpeg --enable-freetype \
  --enable-alsa --enable-pulse --enable-sdl2 --enable-udev \
  --disable-pipewire \
  --enable-x11 --enable-wayland --enable-kms --enable-egl --enable-opengl --enable-vulkan \
  --enable-builtinglslang --enable-glslang --enable-slang --enable-spirv_cross >/dev/null
make -j"$(nproc)" >/dev/null
mkdir -p "$OUT"; cp retroarch "$OUT/"; strip "$OUT/retroarch"
echo "retroarch $VER built: $(du -h "$OUT/retroarch" | cut -f1)"
