#!/usr/bin/env python3
"""Make Batocera's python-src launcher relocatable.

Rewrites every literal Path('/userdata/...'), Path('/usr/share/...'),
Path('/usr/bin/...'), Path('/usr/lib/...') and Path('/var/run/...') in the
given python-src tree into relocate('...'), and adds relocate() to
batocera_common.paths. relocate() maps each prefix to an environment variable:

    /userdata          -> ES_USERDATA
    /usr/share         -> ES_SHARE
    /usr/lib/libretro  -> ES_LIBRETRO_CORES
    /usr/lib           -> ES_LIB
    /usr/bin           -> ES_BIN   (only if the file exists there, else the host's /usr/bin)
    /var/run           -> ES_RUN
    /etc               -> ES_ETC   (only if the file exists there, else the host's /etc)
    /usr/<other>       -> ES_USR   (downloaded emulators, e.g. /usr/pcsx2/bin)

Each variable may list several folders separated by ':'. Plain '/usr/bin/x'
strings (emulator command lines) are rewritten to str(relocate('/usr/bin/x')).

With no variables set, every path is unchanged, so stock Batocera behaviour is kept.
Safe to run more than once.
Usage: relocate-launcher.py <batocera.linux>/python-src [extra package dirs, e.g. package/batocera/utils/hotkeygen]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HELPER = '''
# --- relocatable paths (added by relocate-launcher.py) ---
import os as _os

_RELOCATIONS: Final = (
    # (prefix, env var, use relocated path only if it exists, else keep the host path)
    ('/userdata', 'ES_USERDATA', False),
    ('/usr/share', 'ES_SHARE', True),
    ('/usr/lib/libretro', 'ES_LIBRETRO_CORES', True),
    ('/usr/lib', 'ES_LIB', True),
    ('/usr/bin', 'ES_BIN', True),
    ('/var/run', 'ES_RUN', False),
    ('/etc', 'ES_ETC', True),
    # any other /usr/<emulator>/... (e.g. /usr/pcsx2/bin): downloaded emulators
    ('/usr', 'ES_USR', True),
)


def relocate(path: str, /) -> Path:
    """Map a Batocera system path onto the relocated layout (see _RELOCATIONS).

    An env var may list several folders separated by ':' (like PATH); for
    read-only prefixes the first one containing the file wins, otherwise the
    host path is kept.
    """
    for prefix, env, only_if_exists in _RELOCATIONS:
        if path == prefix or path.startswith(prefix + '/'):
            for base in filter(None, _os.environ.get(env, '').split(':')):
                candidate = Path(base + path[len(prefix):])
                if not only_if_exists or candidate.exists():
                    return candidate
            break
    return Path(path)
# --- end relocatable paths ---
'''

LITERAL = re.compile(r"""Path\((['"])(/(?:userdata|usr|var/run|etc)(?:/[^'"]*)?)\1\)""")
# plain executable strings, e.g. args = ['/usr/bin/PPSSPP', rom]  (not f-strings, not already wrapped)
BINSTR = re.compile(r"""(?<!Path\()(?<!relocate\()(?<![\w(])(['"])(/usr/bin/[A-Za-z0-9._+-]+(?:/[A-Za-z0-9._+-]+)*)\1""")
# config writers: something.set('key', '/userdata/...')  ->  something.set('key', str(relocate('/userdata/...')))
SETTER = re.compile(r"""(\.set\(\s*['"][^'"]*['"]\s*,\s*['"][^'"]*['"]\s*,\s*|\.set\(\s*['"][^'"]*['"]\s*,\s*)(['"])(/(?:userdata|usr/share)/[^'"{}]*)\2\s*\)""")


def rewrite(src: str) -> tuple[str, int]:
    src, a = LITERAL.subn(lambda m: f"relocate('{m.group(2)}')", src)
    src, b = SETTER.subn(lambda m: f"{m.group(1)}str(relocate('{m.group(3)}')))", src)
    src, c = BINSTR.subn(lambda m: f"str(relocate('{m.group(2)}'))", src)
    return src, a + b + c
IMPORT = 'from batocera_common.paths import relocate\n'


def tweak(roots: list[Path], rel: str, old: str, new: str) -> None:
    """Exact-text replacement in the first root containing <rel>; warns if upstream changed."""
    for r in roots:
        for f in r.rglob(Path(rel).name):
            if str(f).endswith(rel):
                src = f.read_text()
                if old in src:
                    f.write_text(src.replace(old, new))
                    print(f'  1  {rel} (desktop tweak)')
                elif new not in src:
                    print(f'  WARN {rel}: upstream text changed, tweak not applied')
                return
    print(f'  WARN {rel}: not found, tweak not applied')


def add_import(src: str) -> str:
    if IMPORT in src:
        return src
    lines = src.splitlines(keepends=True)
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith('from __future__'):
            insert_at = i + 1
            break
    else:
        # after the leading comment/licence block and module docstring
        i = 0
        while i < len(lines) and (lines[i].startswith('#') or not lines[i].strip()):
            i += 1
        if i < len(lines) and lines[i].lstrip().startswith(('"""', "'''")):
            quote = lines[i].lstrip()[:3]
            if lines[i].count(quote) >= 2:
                i += 1
            else:
                i += 1
                while i < len(lines) and quote not in lines[i]:
                    i += 1
                i += 1
        insert_at = i
    lines.insert(insert_at, IMPORT)
    return ''.join(lines)


def main() -> int:
    root = Path(sys.argv[1]).resolve()
    common = root / 'python-batocera-common' / 'batocera_common' / 'paths.py'
    if not common.is_file():
        sys.exit(f'not a python-src tree: {root}')

    # 1. helper in batocera_common.paths, placed before the first constant
    src = common.read_text()
    if 'def relocate(' not in src:
        anchor = src.index('BATOCERA_SHARE_DIR: Final')
        src = src[:anchor] + HELPER.lstrip('\n') + '\n\n' + src[anchor:]
    src, _ = rewrite(src)
    common.write_text(src)

    # 2. every other module, in python-src and any extra package folders given
    roots = [root] + [Path(p).resolve() for p in sys.argv[2:]]

    def modules():
        for r in roots:
            for py in sorted(r.rglob('*.py')):
                if not {'tests', 'stubs'} & set(py.relative_to(r).parts):
                    yield r, py

    changed = 0
    for r, py in modules():
        if py == common:
            continue
        src = py.read_text()
        new, n = rewrite(src)
        if n:
            py.write_text(add_import(new))
            changed += 1
            print(f'{n:3d}  {py.relative_to(r)}')

    # 3. desktop tweaks
    # Batocera owns names on the D-Bus *system* bus, which a desktop user may not do.
    # ES_DBUS=session switches the launcher to the user's session bus.
    bus = root / 'python-batocera-common' / 'batocera_common' / 'dbus' / 'bus.py'
    src = bus.read_text()
    old = 'bus_type: BusType = field(default=BusType.SYSTEM, kw_only=True)'
    new = ("bus_type: BusType = field(default_factory=lambda: BusType.SESSION if "
           "__import__('os').environ.get('ES_DBUS') == 'session' else BusType.SYSTEM, kw_only=True)")
    if old in src:
        bus.write_text(src.replace(old, new))
        print('  1  python-batocera-common/batocera_common/dbus/bus.py (ES_DBUS)')
    elif new not in src:
        print('  WARN bus.py layout changed; ES_DBUS tweak not applied')

    # Batocera runs as root and opens every /dev/input device. A desktop user can
    # only read some (controllers, keyboards), so skip the rest instead of crashing.
    tweak(
        roots,
        'hotkeygen/utils.py',
        '        input_device = evdev.InputDevice(udev_device.device_node)\n        returned = False\n',
        '        try:\n'
        '            input_device = evdev.InputDevice(udev_device.device_node)\n'
        '        except PermissionError:\n'
        '            return None  # desktop: not every input device is readable by the user\n'
        '        returned = False\n',
    )

    # The controller hotplug watcher blocks in monitor.poll(None) on a worker
    # thread; at exit asyncio waits for that thread forever, so batocera-launch
    # never returns to ES after the game closes. Poll with a timeout instead.
    tweak(
        roots,
        'batocera_launch/devices/evmapy.py',
        '                device = await loop.run_in_executor(None, monitor.poll, None)\n'
        '                if device is None:\n'
        '                    break\n',
        '                device = await loop.run_in_executor(None, monitor.poll, 1.0)\n'
        '                if device is None:\n'
        '                    continue  # timeout: lets the executor thread end at shutdown\n',
    )

    # The in-game controller watcher must see the same devices the players were matched to
    # (acrobato_launch.py: /dev/input devices, incl. Steam's virtual pad under Steam). By
    # default SDL3 reads a Steam Deck/Steam Controller directly (HIDAPI) and hides Steam's
    # virtual pad, so any hotplug event made it drop player 1 and wipe the hotkey config.
    # --- Hotkeys without keyboard permissions -------------------------------------------
    # Batocera: hotkeygen (root) types e.g. Shift+Esc on a virtual keyboard and RetroArch reads
    # it from /dev/input. A desktop user often can't create that keyboard (/dev/uinput) and
    # RetroArch can't read keyboards from /dev/input (only SteamOS grants that), so RetroArch
    # hotkeys go through its network command interface instead (UDP, this machine only).
    tweak(
        roots,
        'batocera_launch_libretro/emulator.py',
        "        custom_config.set('quit_press_twice', False)\n",
        "        custom_config.set('quit_press_twice', False)\n"
        "        custom_config.set('network_cmd_enable', True)  # AcroBato: hotkeys as RetroArch commands\n"
        "        custom_config.set('network_cmd_port', 55355)\n",
    )
    tweak(
        roots,
        'hotkeygen/daemon.py',
        '@dataclass(slots=True)\nclass HotkeyActivation:\n',
        "# AcroBato: RetroArch hotkeys as network commands (see relocate-launcher.py)\n"
        "_RA_COMMANDS = {\n"
        "    'exit': 'QUIT', 'menu': 'MENU_TOGGLE', 'pause': 'PAUSE_TOGGLE', 'save_state': 'SAVE_STATE',\n"
        "    'restore_state': 'LOAD_STATE', 'previous_slot': 'STATE_SLOT_MINUS', 'next_slot': 'STATE_SLOT_PLUS',\n"
        "    'fastforward': 'FAST_FORWARD', 'reset': 'RESET', 'screenshot': 'SCREENSHOT', 'next_disk': 'DISK_NEXT',\n"
        "}\n\n\n"
        "def _ra_command(command: str) -> None:\n"
        "    import socket\n"
        "    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:\n"
        "        s.sendto(command.encode(), ('127.0.0.1', 55355))\n\n\n"
        '@dataclass(slots=True)\nclass HotkeyActivation:\n',
    )
    tweak(
        roots,
        'hotkeygen/daemon.py',
        '    async def __begin_hotkey(self, hotkey: str, /) -> HotkeyActivation | None:\n',
        '    async def __begin_hotkey(self, hotkey: str, /) -> HotkeyActivation | None:\n'
        "        if self.context.get('name') == 'retroarch' and hotkey in _RA_COMMANDS:\n"
        '            ra_command = _RA_COMMANDS[hotkey]\n\n'
        '            async def ra_send() -> None:\n'
        '                _ra_command(ra_command)\n\n'
        '            async def ra_nothing() -> None:\n'
        '                pass\n\n'
        '            return HotkeyActivation(ra_send, ra_nothing)\n\n',
    )
    # hotkeygen without /dev/uinput access: keep running (commands, D-Bus, RetroArch hotkeys)
    tweak(
        roots,
        'hotkeygen/daemon.py',
        '        self.target = evdev.UInput(\n'
        '            name=DEVICE_NAME, events={ecodes.EV_KEY: keys_list, ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y]}\n'
        '        )\n',
        '        try:\n'
        '            self.target = evdev.UInput(\n'
        '                name=DEVICE_NAME, events={ecodes.EV_KEY: keys_list, ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y]}\n'
        '            )\n'
        '        except OSError as e:\n'
        "            print(f'no virtual keyboard (/dev/uinput: {e}); key-based hotkeys disabled')\n"
        '            self.target = None\n',
    )
    tweak(
        roots,
        'hotkeygen/daemon.py',
        'def _send_keys(target: evdev.UInput, keys: int | list[int], begin: bool, debug: bool) -> None:\n',
        'def _send_keys(target: evdev.UInput, keys: int | list[int], begin: bool, debug: bool) -> None:\n'
        '    if target is None:\n'
        '        return\n',
    )
    tweak(
        roots,
        'hotkeygen/daemon.py',
        '        await reset_pointer_position(self.target)\n',
        '        if self.target is not None:\n'
        '            await reset_pointer_position(self.target)\n',
    )
    tweak(
        roots,
        'hotkeygen/daemon.py',
        '            self.target.close()\n',
        '            if self.target is not None:\n'
        '                self.target.close()\n',
    )

    # SDL3 (controller hotplug watcher) is bundled: most distros don't install it, and without
    # it the launcher hung before starting the game. Same build as Batocera's (build-es.sh).
    tweak(
        roots,
        'batocera_common/sdl3.py',
        "_sdl3 = ctypes.CDLL(ctypes.util.find_library('SDL3') or 'libSDL3.so')\n",
        "_bundled = os.path.join(os.environ.get('APPDIR', ''), 'usr/lib/libSDL3.so.0')  # AcroBato\n"
        "_sdl3 = ctypes.CDLL(_bundled if os.path.exists(_bundled) else (ctypes.util.find_library('SDL3') or 'libSDL3.so'))\n",
    )

    # ES's SDL (Batocera's patches) reports GUIDs without the name CRC (bytes 2-3); the host's
    # SDL3 used by the hotplug watcher includes it. Compare without it, or every hotplug event
    # looks like player 1 went away and the hotkey config is wiped.
    tweak(
        roots,
        'batocera_launch/devices/evmapy.py',
        '                        if guid and path:\n'
        '                            online_controllers_map[guid].append(str(path))\n',
        '                        if guid and path:\n'
        '                            guid = guid[:4] + "0000" + guid[8:] if len(guid) == 32 else guid\n'
        '                            online_controllers_map[guid].append(str(path))\n',
    )

    # "exit" = Alt+F4 for most standalone emulators: Batocera's window manager closes the
    # window. Gamescope (Steam Game Mode) doesn't, and the emulator may half-quit and stop
    # taking input. Close the game's processes instead (compat/bin/acrobato-emukill).
    tweak(
        roots,
        'hotkeygen/daemon.py',
        "        if (keys := self.context['keys'].get(hotkey)) is None:\n            return None\n",
        "        if (keys := self.context['keys'].get(hotkey)) is None:\n            return None\n\n"
        "        if hotkey == 'exit' and isinstance(keys, list) and {ecodes.ecodes.get(k, k) if isinstance(k, str) else k for k in keys} == {ecodes.KEY_LEFTALT, ecodes.KEY_F4}:\n"
        "            keys = 'acrobato-emukill'\n",
    )

    # The hints only work as environment variables (SDL reads them at init); they are
    # removed again right away so the emulator doesn't inherit them.
    tweak(
        roots,
        'batocera_launch/devices/evmapy.py',
        '                sdl3.init(sdl3.InitFlags.JOYSTICK)\n',
        "                _env = __import__('os').environ\n"
        "                _hints = {'SDL_JOYSTICK_HIDAPI': '0', 'SDL_GAMECONTROLLER_ALLOW_STEAM_VIRTUAL_GAMEPAD': '1'}\n"
        '                _saved = {k: _env.get(k) for k in _hints}\n'
        '                _env.update(_hints)\n'
        '                try:\n'
        '                    sdl3.init(sdl3.InitFlags.JOYSTICK)\n'
        '                finally:\n'
        '                    for _k, _v in _saved.items():\n'
        '                        if _v is None:\n'
        '                            _env.pop(_k, None)\n'
        '                        else:\n'
        '                            _env[_k] = _v\n',
    )

    # 4. report plain-string paths that still need a manual look
    leftovers = re.compile(r"""['"]/(?:userdata|usr/share)/""")
    for r, py in modules():
        for no, line in enumerate(py.read_text().splitlines(), 1):
            if leftovers.search(line) and 'relocate(' not in line and '_RELOCATIONS' not in line:
                print(f'  TODO {py.relative_to(r)}:{no}: {line.strip()[:110]}')
    print(f'rewrote {changed} files')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
