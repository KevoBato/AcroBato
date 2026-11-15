#!/usr/bin/env bash
# Launch the first game of each given system through ES's HTTP API and report
# which emulator process started. Usage: test-launches.sh <AppImage> system...
export XDG_RUNTIME_DIR=/run/user/$(id -u) WAYLAND_DISPLAY=wayland-0 DISPLAY=:0
export XAUTHORITY=$(ls /run/user/$(id -u)/xauth_* 2>/dev/null | head -1)
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus" PATH=/usr/local/bin:/usr/bin:/bin
unset ES_USERDATA ES_SHARE ES_ETC ES_RUN ES_DBUS ES_BIN ES_USR APPDIR
APP="$1"; shift
API=http://127.0.0.1:1234
LOG="$HOME/.local/share/acrobato/system/logs/batocera-launch.log"
pkill -x retroarch; pkill -x emulationstatio; sleep 1
(setsid "$APP" --windowed --resolution 1280 800 </dev/null >/tmp/test-launches.log 2>&1 &)
t=0; until curl -s -m 2 "$API/caps" >/dev/null 2>&1 || [ $t -ge 60 ]; do sleep 1; t=$((t+1)); done
sleep 3
for sys in "$@"; do
  rom=$(curl -s "$API/systems/$sys/games" | python3 -c 'import json,sys; g=json.load(sys.stdin); print(g[0]["path"] if g else "")')
  [ -n "$rom" ] || { echo "$sys: no game"; continue; }
  : > "$LOG"
  curl -s -X POST --data-binary "$rom" "$API/launch" >/dev/null
  t=0; until grep -q "Running command" "$LOG" 2>/dev/null || [ $t -ge 25 ]; do sleep 1; t=$((t+1)); done
  sleep 8
  cmd=$(grep -m1 "Running command" "$LOG" | sed 's/.*Running command: //' | cut -c1-150)
  alive=$(pgrep -fa "retroarch|dolphin|flatpak run" | grep -v pgrep | head -1 | cut -c1-60)
  echo "$sys: $(basename "$rom")"
  echo "   command: ${cmd:-NONE}"
  echo "   running after 8s: ${alive:-nothing}"
  grep -E "acrobato:|ERROR  \]" "$LOG" | grep -v "Environ\]" | cut -c1-160 | head -3 | sed 's/^/   /'
  pkill -x retroarch; pkill -f "flatpak run.*dolphin"; pkill -f "dolphin-emu"; sleep 5
done
pkill -x emulationstatio
