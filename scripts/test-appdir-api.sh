#!/usr/bin/env bash
# Headless check of the AppDir on the host via ES's HTTP API (no screenshots):
# ES comes up, systems are listed, a launch runs bundled RetroArch, ES survives.
export XDG_RUNTIME_DIR=/run/user/$(id -u) WAYLAND_DISPLAY=wayland-0 DISPLAY=:0
export XAUTHORITY=$(ls /run/user/$(id -u)/xauth_* 2>/dev/null | head -1)
export PATH=/usr/local/bin:/usr/bin:/bin
unset ES_USERDATA ES_SHARE ES_ETC ES_RUN ES_DBUS ES_BIN ES_USR APPDIR
APP="${1:-$HOME/rbl/AppDir/AppRun}"
D="$HOME/.local/share/rbl"
API=http://127.0.0.1:1234
pkill -x retroarch; pkill -x emulationstatio; sleep 2
# ES only advances launches while it is rendering: make sure the display is on
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
kscreen-doctor --dpms on >/dev/null 2>&1
S=/tmp/shots; rm -rf "${S:?}"; mkdir -p "$S"
[ -f "$D/roms/nes/Blue Screen Test.nes" ] || { mkdir -p "$D/roms/nes"; python3 "$HOME/rbl/project/scripts/make-test-rom.py" "$D/roms/nes/Blue Screen Test.nes"; }

(setsid "$APP" --windowed --resolution 1280 800 </dev/null >/tmp/apprun-api.log 2>&1 &)
t=0; until curl -s -m 2 "$API/caps" >/dev/null 2>&1 || [ $t -ge 90 ]; do sleep 2; t=$((t+2)); done
echo "ES API up after ${t}s: $(curl -s -m 2 "$API/caps" >/dev/null && echo yes || echo NO)"
echo "systems visible: $(curl -s -m 5 "$API/systems" | python3 -c 'import json,sys; s=json.load(sys.stdin); print(len(s), [x["name"] for x in s][:8])' 2>/dev/null)"
echo "nes games: $(curl -s -m 5 "$API/systems/nes/games" | python3 -c 'import json,sys; print([g["name"] for g in json.load(sys.stdin)])' 2>/dev/null)"
curl -s -m 5 -X POST --data-binary "$D/roms/nes/Blue Screen Test.nes" -H 'Content-Type: text/plain' "$API/launch" >/dev/null
t=0; until pgrep -x retroarch >/dev/null || [ $t -ge 30 ]; do sleep 1; t=$((t+1)); done
echo "retroarch started: $(pgrep -x retroarch >/dev/null && echo "yes after ${t}s" || echo NO)"
pgrep -a retroarch | grep -o -- '-L [^ ]*' | sed 's/^/  core: /'
sleep 6; spectacle -b -n -f -o "$S/game.png"
pkill -x retroarch; sleep 6; spectacle -b -n -f -o "$S/back.png"
echo "ES alive after game: $(pgrep -x emulationstatio >/dev/null && echo yes || echo NO)"
echo "--- launcher log (errors):"
grep -h "ERROR" "$D"/system/logs/*.log 2>/dev/null | grep -vE '\[(INFO|WARN)\]|niceness|libretro INFO|core_info.cache' | cut -c1-200 | tail -6
pkill -x emulationstatio
