#!/usr/bin/env bash
# DEV ONLY: bridge from EmulationStation (in the "esbuild" Ubuntu distrobox)
# to batocera-launch (in the "pydev" Arch distrobox). In the AppImage both
# live together and ES calls batocera-launch directly.
#
# es_systems.cfg command:
#   distrobox-host-exec /home/deck/rbl/project/scripts/dev-launch.sh %CONTROLLERSCONFIG% -system %SYSTEM% -rom %ROM% ...
if [ -z "$IN_PYDEV" ]; then
  exec distrobox enter pydev -- env IN_PYDEV=1 "$0" "$@"
fi
. "$HOME/rbl/dev-env.sh"
. "$HOME/rbl/venv/bin/activate"
exec batocera-launch "$@" >> "$ES_USERDATA/system/logs/es_launch_stdout.log" 2>&1
