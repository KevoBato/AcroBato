#!/usr/bin/env bash
# DEV: start EmulationStation on the Deck desktop, launch a ROM through ES's
# HTTP API (POST /launch), and take screenshots: menu, in game, back in menu.
# Usage: dev-test-es-launch.sh "<rom path>"   (screenshots in /tmp/shots)
. "$HOME/rbl/dev-env.sh"
ROM="$1"
S=/tmp/shots; rm -rf "$S"; mkdir -p "$S"
pkill -x emulationstatio; pkill -x retroarch; sleep 2
: > "$ES_USERDATA/system/logs/es_launch_stdout.log"

(cd "$HOME/rbl/src/es" && setsid distrobox enter esbuild -- env ES_USERDATA="$ES_USERDATA" ES_SHARE="$ES_SHARE" \
   LD_LIBRARY_PATH="$HOME/rbl/deps/usr/lib" ./emulationstation --windowed --resolution 1280 800 \
   </dev/null > "$HOME/rbl/test/es-run.log" 2>&1 &)
sleep 15; spectacle -b -n -f -o "$S/1-es.png"

reply=$(curl -s -m 5 -X POST --data-binary "$ROM" -H "Content-Type: text/plain" http://127.0.0.1:1234/launch)
echo "launch reply: '$reply'"
sleep 14; spectacle -b -n -f -o "$S/2-game.png"
echo "retroarch running: $(pgrep -x retroarch >/dev/null && echo yes || echo no)"

pkill -x retroarch; t0=$(date +%s)
# wait for the launch chain to finish (bridge + batocera-launch cleanup)
while pgrep -f "bin/batocera-launch" >/dev/null && [ $(( $(date +%s) - t0 )) -lt 30 ]; do sleep 1; done
echo "launcher exited after $(( $(date +%s) - t0 ))s"
sleep 4; spectacle -b -n -f -o "$S/3-back.png"
echo "ES still running after game: $(pgrep -x emulationstatio >/dev/null && echo yes || echo no)"
echo "launcher errors:"; grep "ERROR" "$ES_USERDATA/system/logs/es_launch_stdout.log" | grep -vE "\[(INFO|WARN)\]" | cut -c1-200 | head -5
pkill -x emulationstatio
