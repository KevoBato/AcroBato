#!/usr/bin/env bash
# Run inside a distro container (distrobox) to check the AppImage on that distro's libraries:
#   test-distro.sh <extracted AppImage dir (squashfs-root)> <label>
# Reports libraries the system lacks, whether ES starts (fresh data folder), and whether a
# RetroArch game launches. Uses the host's display (DISPLAY=:0).
R="$1"; LABEL="$2"
export XDG_RUNTIME_DIR=/run/user/$(id -u) DISPLAY=:0
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
export ES_USERDATA="/tmp/acrobato-test-$LABEL"
unset APPDIR APPIMAGE ES_SHARE ES_ETC ES_RUN ES_BIN ES_USR ES_DBUS
API=http://127.0.0.1:1234
[ -n "$KEEP" ] || rm -rf "$ES_USERDATA"; KEEP=
. /etc/os-release 2>/dev/null
echo "### $LABEL: $PRETTY_NAME, glibc $(getconf GNU_LIBC_VERSION | cut -d' ' -f2)"

missing=$(for f in "$R"/usr/bin/emulationstation "$R"/usr/bin/retroarch "$R"/usr/lib/*.so* "$R"/usr/lib/libretro/*.so; do
  [ -f "$f" ] && LD_LIBRARY_PATH="$R/usr/lib" ldd "$f" 2>/dev/null | grep "not found"; done | awk '{print $1}' | sort -u | tr '\n' ' ')
echo "missing system libraries: ${missing:-none}"
toonew=$(for f in "$R"/usr/bin/emulationstation "$R"/usr/bin/retroarch "$R"/usr/lib/libretro/*.so; do
  LD_LIBRARY_PATH="$R/usr/lib" ldd "$f" 2>&1 | grep -o "version .GLIBC[^ ]* not found" ; done | sort -u | tr '\n' ' ')
echo "library version errors: ${toonew:-none}"

pkill -x retroarch 2>/dev/null; pkill -x emulationstatio 2>/dev/null; sleep 1
"$R/AppRun" --windowed --resolution 1280 800 </dev/null >"/tmp/acrobato-test-$LABEL.log" 2>&1 &
t=0; until curl -s -m 2 "$API/caps" >/dev/null 2>&1 || [ $t -ge 60 ]; do sleep 1; t=$((t+1)); done
if ! curl -s -m 2 "$API/caps" >/dev/null 2>&1; then
  echo "ES: DID NOT START"; grep -v LD_PRELOAD "/tmp/acrobato-test-$LABEL.log" | tail -8
  exit 1
fi
echo "ES: started in ${t}s, $(curl -s $API/systems | "$R/usr/python/bin/python3" -I -c 'import json,sys; print(len(json.load(sys.stdin)))' 2>/dev/null) systems"
sleep 2
for sys in nes snes megadrive gba; do
  rom=$(curl -s "$API/systems/$sys/games" | "$R/usr/python/bin/python3" -I -c 'import json,sys; g=json.load(sys.stdin); print(g[0]["path"] if g else "")' 2>/dev/null)
  [ -n "$rom" ] && break
done
if [ -z "$rom" ]; then echo "game: no test game found"; else
  curl -s -X POST --data-binary "$rom" "$API/launch" >/dev/null
  sleep 10
  if pgrep -x retroarch >/dev/null; then echo "game: RetroArch running ($sys: $(basename "$rom"))"
  else echo "game: RetroArch NOT running ($sys)"; KEEP=1
    L="$ES_USERDATA/system/logs"; grep -h -E "ERROR|rror|Running command|terminated" "$L"/batocera-launch.log "$L"/es_launch_stderr.log 2>/dev/null       | grep -v -E "Environ|core-options" | tail -6 | cut -c1-220; fi
  pkill -x retroarch; sleep 4
fi
pkill -x emulationstatio; sleep 2
[ -n "$KEEP" ] || rm -rf "$ES_USERDATA"
