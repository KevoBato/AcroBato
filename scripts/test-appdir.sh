#!/usr/bin/env bash
# Test the AppDir directly on the host (outside any container), like a user would run it:
#  1. fresh data folder, no games  -> ES must start (not crash) and list systems
#  2. add the test ROM, restart, launch it through ES's HTTP API with bundled RetroArch
# Screenshots in /tmp/shots. Run on the Deck desktop session.
export XDG_RUNTIME_DIR=/run/user/$(id -u) WAYLAND_DISPLAY=wayland-0 DISPLAY=:0
export XAUTHORITY=$(ls /run/user/$(id -u)/xauth_* 2>/dev/null | head -1)
export PATH=/usr/local/bin:/usr/bin:/bin
unset ES_USERDATA ES_SHARE ES_ETC ES_RUN ES_DBUS ES_BIN ES_USR APPDIR
APP="${1:-$HOME/rbl/AppDir/AppRun}"
D="$HOME/.local/share/rbl"
S=/tmp/shots; rm -rf "${S:?}"; mkdir -p "$S"
stop() { pkill -x retroarch; pkill -x emulationstatio; sleep 2; }

stop; rm -rf "${D:?}"
(setsid "$APP" --windowed --resolution 1280 800 </dev/null >/tmp/apprun1.log 2>&1 &)
sleep 20; spectacle -b -n -f -o "$S/1-empty.png"
echo "1. empty library: ES running = $(pgrep -x emulationstatio >/dev/null && echo yes || echo NO)"
grep -c "SIGSEGV" "$D/system/configs/emulationstation/es_log.txt" 2>/dev/null | sed 's/^/   crashes in log: /'
stop

python3 "$HOME/rbl/project/scripts/make-test-rom.py" "$D/roms/nes/Blue Screen Test.nes"
(setsid "$APP" --windowed --resolution 1280 800 </dev/null >/tmp/apprun2.log 2>&1 &)
sleep 20
curl -s -m 5 -X POST --data-binary "$D/roms/nes/Blue Screen Test.nes" -H "Content-Type: text/plain" http://127.0.0.1:1234/launch >/dev/null
sleep 15; spectacle -b -n -f -o "$S/2-game.png"
echo "2. game: retroarch running = $(pgrep -x retroarch >/dev/null && echo yes || echo NO)"
pgrep -a retroarch | grep -o -- "-L [^ ]*" | sed 's/^/   core: /'
pkill -x retroarch; sleep 6; spectacle -b -n -f -o "$S/3-back.png"
echo "3. after game: ES running = $(pgrep -x emulationstatio >/dev/null && echo yes || echo NO)"
echo "   launcher errors:"; grep "ERROR" "$D/system/logs/"*.log 2>/dev/null | grep -vE "\[(INFO|WARN)\]|niceness|libretro INFO" | cut -c1-180 | tail -5
stop
