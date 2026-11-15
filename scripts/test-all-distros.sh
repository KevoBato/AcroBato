#!/bin/bash
cd ~/rbl/project
: # ES already built
distrobox enter esbuild -- bash -c "cd ~/rbl/project && bash scripts/build-appdir.sh" > ~/rbl/appdir.log 2>&1 || { echo "APPDIR FAILED"; echo ALLDONE; exit 1; }
ls ~/rbl/AppDir/usr/lib | grep -i -E "glew|sdl3"; for f in $(find ~/rbl/AppDir/usr/python -name "*.so*"); do readelf -d $f 2>/dev/null | grep -q "(RELR)" && echo "still RELR: $f"; done
bash scripts/pack-appimage.sh > /tmp/pack.log 2>&1; tail -1 /tmp/pack.log | cut -c1-16
rm -rf ~/rbl/test/ext && mkdir -p ~/rbl/test/ext && cd ~/rbl/test/ext && ~/rbl/out/AcroBato-x86_64.AppImage --appimage-extract >/dev/null
D="libpulse0 libopengl0 libgl1 libegl1 libgl1-mesa-dri libwayland-cursor0 libwayland-egl1 libfontconfig1 libxi6 libxrender1 libdbus-1-3"
declare -A INST=(
 [t-ubuntu2204]="sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $D libasound2"
 [t-ubuntu2404]="sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $D libasound2t64"
 [t-debian12]="sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $D libasound2"
 [t-mint22]="sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $D libasound2t64"
 [t-fedora]="sudo dnf install -y -q pulseaudio-libs alsa-lib libglvnd-opengl libglvnd-glx libglvnd-egl mesa-dri-drivers libwayland-cursor libwayland-egl fontconfig libXi libXrender dbus-libs"
 [t-arch]="sudo pacman -Sy --noconfirm --needed libpulse alsa-lib libglvnd mesa wayland fontconfig libxi libxrender"
 [t-tumbleweed]="sudo zypper -n -q in libpulse0 alsa libglvnd Mesa-dri libwayland-cursor0 libwayland-egl1 fontconfig libXi6 libXrender1 gawk"
)
for n in ${ONLY:-t-ubuntu2204 t-ubuntu2404 t-debian12 t-fedora t-arch t-tumbleweed t-mint22}; do
  distrobox enter "$n" -- bash -c "${INST[$n]}" > ~/rbl/test/inst-$n.log 2>&1 || echo "$n: desktop libs install FAILED (see inst-$n.log)"
  distrobox enter "$n" -- bash ~/rbl/project/scripts/test-distro.sh ~/rbl/test/ext/squashfs-root "$n" 2>&1 | grep -v -E "LD_PRELOAD|^Starting container|Setting up|Installing basic|Integrating|Container Setup|^\S*\s*$"
  echo
done
echo ALLDONE
