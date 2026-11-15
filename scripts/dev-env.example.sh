export XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 XAUTHORITY=$(ls /run/user/1000/xauth_* | head -1)
export ES_USERDATA=$HOME/rbl/test/userdata ES_SHARE=$HOME/rbl/test/share
export ES_DBUS=session DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
export PATH=$HOME/rbl/project/compat/bin:$PATH
export ES_ETC=$HOME/rbl/test/etc ES_RUN=$XDG_RUNTIME_DIR/rbl
mkdir -p $ES_RUN
