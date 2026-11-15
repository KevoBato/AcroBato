#!/usr/bin/env bash
# Build batocera-emulationstation with our patches inside the "esbuild"
# distrobox (Ubuntu 22.04). Run on the build host (the Steam Deck):
#   distrobox create -Y -n esbuild -i docker.io/library/ubuntu:22.04   # once
#   distrobox enter esbuild -- bash scripts/build-es.sh
set -euo pipefail

ES_REPO=https://github.com/batocera-linux/batocera-emulationstation.git
ES_COMMIT=b722aa988afb2c661e0eaaa7e6971707395ba9fc
SDL_VERSION=2.32.10   # = Batocera's buildroot (package/sdl2/sdl2.hash)
SDL_SHA256=5f5993c530f084535c65a6879e9b26ad441169b3e25d789d83287040a9ca5165
SDL_MIXER_TAG=release-2.8.0

HERE="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${WORK:-$HOME/rbl}"
DEPS="$WORK/deps/usr"

sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  git build-essential cmake pkg-config python3 \
  libfreeimage-dev libfreetype6-dev libcurl4-openssl-dev rapidjson-dev \
  libasound2-dev libpulse-dev libgl1-mesa-dev libvlc-dev libvlccore-dev vlc-plugin-base \
  libudev-dev libfribidi-dev gettext \
  libx11-dev libxext-dev libxrandr-dev libxcursor-dev libxi-dev libxss-dev libxkbcommon-dev \
  libwayland-dev wayland-protocols libegl1-mesa-dev libdrm-dev libgbm-dev libdbus-1-dev \
  libibus-1.0-dev libpipewire-0.3-dev \
  libvorbis-dev libopusfile-dev libflac-dev libmpg123-dev libxmp-dev libfluidsynth-dev
# Ubuntu 22.04's SDL2 (2.0.20) is too old for ES; make sure its headers can't be picked up.
sudo DEBIAN_FRONTEND=noninteractive apt-get remove -y -qq libsdl2-dev libsdl2-mixer-dev || true

# --- SDL2 + SDL2_mixer (also bundled into the AppImage later) ---
# SDL2 as Batocera builds it: same version, its joystick/input patches, no HIDAPI and no
# virtual joysticks. Batocera's controller database (es_input.cfg, ~330 pads) and its
# launcher assume exactly this view of controllers: evdev devices, Batocera's button
# numbering, GUIDs without the name CRC, and SDL_Joystick*ById (device path, event codes).
# Display/build patches for Batocera's own boards (KMS/DRM, Mali, Pi, X11 modes) are left out.
SDL_PATCHES="005-crc-is-zero 006-disablegamedb sdl2_accelerometers_are_not_joysticks
  sdl2_buttons_doesnt_make_joysticks sdl2_disable_blacklists_joysticks sdl2_disable_gamepadmapping
  sdl2_disable_joystickShouldIgnoreEvent sdl2_fix_pad_name sdl2_input_add_invert_trigger_support
  sdl2_input_as_retroarch_udev sdl2_input_evdev_at_first_unrelease_button sdl2_input_p003_extra_functions
  sdl2_input_p005_limit_ABS_max sdl2_input_p006_sort_devices sdl2_input_p006_sort_devices_force_udev_sorting
  sdl2_input_p007_udev_buttons sdl2_input_p008_disable_internal_mappings sdl2_input_p009_hat_definition
  sdl2_vidpidwith0"
BL="$WORK/src/batocera.linux"
mkdir -p "$WORK/deps/src"; cd "$WORK/deps/src"
[ -f "SDL2-$SDL_VERSION.tar.gz" ] || curl -sL -o "SDL2-$SDL_VERSION.tar.gz" "https://www.libsdl.org/release/SDL2-$SDL_VERSION.tar.gz"
echo "$SDL_SHA256  SDL2-$SDL_VERSION.tar.gz" | sha256sum -c --quiet -
# SDL3 for batocera-launch's controller hotplug watcher, as Batocera builds it (3.4.14, its input
# patches minus the display one, no HIDAPI). Most distros don't ship SDL3, so it is bundled.
SDL3_VERSION=3.4.14
SDL3_SHA256=30d4aa2b3037718142b32dffd4e72f917ebb6cc5227150e7bb9c45efb2153aeb  # GitHub release digest
[ -f "SDL3-$SDL3_VERSION.tar.gz" ] || curl -sL -o "SDL3-$SDL3_VERSION.tar.gz" \
  "https://github.com/libsdl-org/SDL/releases/download/release-$SDL3_VERSION/SDL3-$SDL3_VERSION.tar.gz"
echo "$SDL3_SHA256  SDL3-$SDL3_VERSION.tar.gz" | sha256sum -c --quiet -
SDL3_PATCHES=$(git -C "$BL" ls-tree --name-only HEAD board/batocera/patches/sdl3/ | grep '\.patch$' | grep -v SDL_SCREEN | sort)
STAMP3="$SDL3_VERSION $(git -C "$BL" rev-parse HEAD)"
if [ ! -f "$DEPS/lib/libSDL3.so.0" ] || [ "$(cat "$DEPS/.sdl3-stamp" 2>/dev/null)" != "$STAMP3" ]; then
  rm -rf "SDL3-$SDL3_VERSION" && tar xzf "SDL3-$SDL3_VERSION.tar.gz"
  for p in $SDL3_PATCHES; do
    git -C "$BL" show "HEAD:$p" | patch -s -p1 -d "SDL3-$SDL3_VERSION" || { echo "SDL3 patch $p failed" >&2; exit 1; }
  done
  cmake -S "SDL3-$SDL3_VERSION" -B "SDL3-$SDL3_VERSION/b" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$DEPS" \
    -DSDL_STATIC=OFF -DSDL_TEST_LIBRARY=OFF -DSDL_TESTS=OFF -DSDL_HIDAPI=OFF -DSDL_HIDAPI_LIBUSB=OFF -DSDL_JACK=OFF \
    -DSDL_VIDEO=OFF -DSDL_AUDIO=OFF -DSDL_RENDER=OFF -DSDL_GPU=OFF -DSDL_CAMERA=OFF \
    -DSDL_X11=OFF -DSDL_WAYLAND=OFF -DSDL_KMSDRM=OFF -DSDL_OPENGL=OFF -DSDL_OPENGLES=OFF -DSDL_VULKAN=OFF -DSDL_UNIX_CONSOLE_BUILD=ON  # joysticks only
  cmake --build "SDL3-$SDL3_VERSION/b" -j"$(nproc)" && cmake --install "SDL3-$SDL3_VERSION/b"
  echo "$STAMP3" > "$DEPS/.sdl3-stamp"
fi
[ -d SDL_mixer ] || git clone -q --depth 1 -b "$SDL_MIXER_TAG" https://github.com/libsdl-org/SDL_mixer.git
STAMP="$SDL_VERSION $(git -C "$BL" rev-parse HEAD) $SDL_PATCHES"
if [ ! -f "$DEPS/lib/libSDL2.so" ] || [ "$(cat "$DEPS/.sdl-stamp" 2>/dev/null)" != "$STAMP" ]; then
  rm -rf "SDL2-$SDL_VERSION" && tar xzf "SDL2-$SDL_VERSION.tar.gz"
  for p in $SDL_PATCHES; do
    git -C "$BL" show "HEAD:board/batocera/patches/sdl2/$p.patch" | patch -s -p1 -d "SDL2-$SDL_VERSION" \
      || { echo "SDL patch $p failed" >&2; exit 1; }
  done
  rm -rf "$DEPS"/lib/libSDL2* "$DEPS"/lib/cmake/SDL2 "$DEPS"/include/SDL2/SDL*.h
  cmake -S "SDL2-$SDL_VERSION" -B "SDL2-$SDL_VERSION/b" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$DEPS" \
    -DSDL_STATIC=OFF -DSDL_TEST=OFF -DSDL_HIDAPI=OFF -DSDL_HIDAPI_JOYSTICK=OFF -DSDL_VIRTUAL_JOYSTICK=OFF
  cmake --build "SDL2-$SDL_VERSION/b" -j"$(nproc)" && cmake --install "SDL2-$SDL_VERSION/b"
  echo "$STAMP" > "$DEPS/.sdl-stamp"
  rm -f "$DEPS/lib/libSDL2_mixer.so"   # rebuild against the new SDL
fi
if [ ! -f "$DEPS/lib/libSDL2_mixer.so" ]; then
  cmake -S SDL_mixer -B SDL_mixer/b -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$DEPS" \
    -DCMAKE_PREFIX_PATH="$DEPS" -DSDL2MIXER_VENDORED=OFF -DSDL2MIXER_SAMPLES=OFF \
    -DSDL2MIXER_WAVPACK=OFF -DSDL2MIXER_GME=OFF -DSDL2MIXER_MIDI_FLUIDSYNTH=OFF
  cmake --build SDL_mixer/b -j"$(nproc)" && cmake --install SDL_mixer/b
fi

# --- EmulationStation ---
mkdir -p "$WORK/src"; cd "$WORK/src"
if [ ! -d es ]; then
  git clone -q --recurse-submodules "$ES_REPO" es
fi
cd es
git checkout -q -- . && git checkout -q "$ES_COMMIT" && git submodule update -q --init
# Batocera's own ES patches (controller event codes and device paths need the SDL above).
# Not 002-quit-add-shift: it makes ES ignore window-close requests (kiosk behaviour).
for p in batocera-emulationstation-config-event-codes batocera-emulationstation-battery-event \
         001-no-next-slot 003-fix-sleep-theme-downloader 004-http-api-shutdown; do
  git -C "$BL" show "HEAD:package/batocera/emulationstation/batocera-emulationstation/$p.patch" | git apply \
    || { echo "ES patch $p failed" >&2; exit 1; }
done
for p in "$HERE"/patches/emulationstation/*.patch; do git apply "$p"; done
python3 "$HERE/scripts/apply-es-branding.py" .   # AcroBato name, window title, quit menu
python3 "$HERE/scripts/apply-es-fixes.py" .      # scraper crash without API keys

cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DGL=ON -DBATOCERA=ON -DENABLE_PULSE=ON -DCEC=OFF \
  -DCMAKE_PREFIX_PATH="$DEPS" \
  -DSDL2_INCLUDE_DIR="$DEPS/include/SDL2" -DSDL2_LIBRARY="$DEPS/lib/libSDL2.so" \
  -DSDLMIXER_INCLUDE_DIR="$DEPS/include/SDL2" -DSDLMIXER_LIBRARY="$DEPS/lib/libSDL2_mixer.so" \
  -DCMAKE_BUILD_RPATH="$DEPS/lib"
cmake --build build -j"$(nproc)"
git checkout -q -- locale   # the build rewrites translation files; keep the tree clean
echo "Built: $WORK/src/es/emulationstation"
