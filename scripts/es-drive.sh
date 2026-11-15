#!/usr/bin/env bash
# Drive a running ES through its HTTP API with keyboard inputs and screenshots.
# Usage: es-drive.sh start|stop|key <name> [n]|shot <file>|wait <secs>
# Key names come from the keyboard entry in es_input.cfg (up, down, left, right, a, b, start, select, ...).
export XDG_RUNTIME_DIR=/run/user/$(id -u) WAYLAND_DISPLAY=wayland-0 DISPLAY=:0
export XAUTHORITY=$(ls /run/user/$(id -u)/xauth_* 2>/dev/null | head -1)
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
export PATH=/usr/local/bin:/usr/bin:/bin
unset ES_USERDATA ES_SHARE ES_ETC ES_RUN ES_DBUS ES_BIN ES_USR APPDIR
API=http://127.0.0.1:1234
case "$1" in
  start)
    pkill -x retroarch; pkill -x emulationstatio; sleep 1
    kscreen-doctor --dpms on >/dev/null 2>&1
    (setsid "${2:-$HOME/rbl/AppDir/AppRun}" --windowed --resolution 1280 800 </dev/null >/tmp/es-drive.log 2>&1 &)
    t=0; until curl -s -m 2 "$API/caps" >/dev/null 2>&1 || [ $t -ge 60 ]; do sleep 1; t=$((t+1)); done
    sleep 3; echo "ES up after ${t}s" ;;
  stop) pkill -x retroarch; pkill -x emulationstatio ;;
  key)
    for _ in $(seq "${3:-1}"); do
      code=$(curl -s -o /tmp/es-input.out -w '%{http_code}' -X POST --data "$2" "$API/input")
      [ "$code" = 200 ] || { echo "input $2 -> $code $(cat /tmp/es-input.out)"; }
      sleep 0.6
    done ;;
  shot) kscreen-doctor --dpms on >/dev/null 2>&1; sleep 0.5; spectacle -b -n -f -o "$2" ;;
  wait) sleep "$2" ;;
esac
