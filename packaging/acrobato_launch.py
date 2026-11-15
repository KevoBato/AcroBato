"""Entry point ES runs for every game (`batocera-launch ...`).

Before handing over to Batocera's launcher, picks a working emulator when the
system's default is a standalone emulator from the downloader that isn't
installed yet (e.g. GameCube defaults to standalone Dolphin, like Batocera):
the first bundled RetroArch core for that system is used instead. An emulator
chosen by the user (per game in ES, or per system in batocera.conf) is always
respected, and once the standalone emulator is downloaded it is used.
"""
from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _conf(path: Path) -> dict[str, str]:
    values = {}
    try:
        for line in path.read_text(errors='replace').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                values[k.strip()] = v.strip()
    except OSError:
        pass
    return values


def _fallback(args: list[str]) -> list[str]:
    if '-emulator' in args or '-system' not in args:
        return args
    system = args[args.index('-system') + 1]
    userdata = Path(os.environ.get('ES_USERDATA', Path.home() / '.local/share/acrobato'))
    share = Path(os.environ.get('ES_SHARE', ''))
    if _conf(userdata / 'system' / 'batocera.conf').get(f'{system}.emulator'):
        return args  # chosen by the user

    from batocera_launch.config.defaults import load_system_defaults
    default = load_system_defaults(system)
    emulator = default.get('emulator')
    if not emulator or emulator == 'libretro':
        return args
    catalog = json.loads((share / 'acrobato' / 'emulators.json').read_text()).get('emulators', [])
    if emulator not in {e['id'] for e in catalog}:
        return args  # not one of ours to download
    try:
        installed = json.loads((userdata / 'emulators' / 'installed.json').read_text())
    except (OSError, ValueError):
        installed = {}
    if emulator in installed:
        return args

    for s in ET.parse(share / 'emulationstation' / 'es_systems.cfg').getroot().findall('system'):
        if s.findtext('name') == system:
            for emu in s.iter('emulator'):
                if emu.get('name') == 'libretro':
                    core = next((c.text for c in emu.iter('core')), None)
                    if core:
                        print(f'acrobato: {emulator} is not installed, using RetroArch core {core}', file=sys.stderr)
                        return args + ['-emulator', 'libretro', '-core', core]
    return args


# --- controllers ---------------------------------------------------------------
# Batocera's ES (with Batocera's patched SDL) tells the launcher, for each player, the
# /dev/input device (-pNdevicepath) and stores each button's evdev code in the controller
# config. Stock SDL can do neither, and on a Steam Deck ES reads the built-in pad directly
# (SDL HIDAPI) while games under Steam see Steam's virtual pad. Without this, the launcher
# gets no players: no hotkeys (evmapy) and no per-player emulator controller setup.
# Here each player is matched to the evdev device emulators actually read, with that
# device's mapping from es_input.cfg and the codes worked out from its capabilities
# (same numbering as SDL's and RetroArch's Linux joystick drivers).
PLAYERS_CFG = Path('/tmp/es_input_players.cfg')  # what ES wrote; batocera-launch reads it first
STEAM_VID, STEAM_VIRTUAL_PID = 0x28DE, 0x11FF
IGNORED_PADS = ('evmapy', 'batocera hotkeys')


def _guid_ids(guid: str) -> tuple[int, int, bool]:
    """(vendor, product, is_hidapi) from an SDL2 GUID string."""
    try:
        b = bytes.fromhex(guid)
        return int.from_bytes(b[4:6], 'little'), int.from_bytes(b[8:10], 'little'), b[14] == ord('h')
    except (ValueError, IndexError):
        return 0, 0, False


def _evdev_pads() -> list:
    import evdev
    from evdev import ecodes as e
    pads = []
    for path in sorted(evdev.list_devices(), key=lambda p: int(p.rsplit('event', 1)[1])):
        try:
            d = evdev.InputDevice(path)
        except OSError:
            continue
        caps = d.capabilities()
        keys = set(caps.get(e.EV_KEY, []))
        if d.name not in IGNORED_PADS and any(e.BTN_JOYSTICK <= k < e.BTN_DIGI for k in keys):
            pads.append(d)
        else:
            d.close()
    return pads


def _codes(dev) -> tuple[list[int], list[int]]:
    """evdev codes in SDL/RetroArch order: (buttons, axes)."""
    from evdev import ecodes as e
    caps = dev.capabilities()
    keys = set(caps.get(e.EV_KEY, []))
    buttons = [k for k in range(e.BTN_JOYSTICK, e.KEY_MAX) if k in keys] + \
              [k for k in range(0, e.BTN_JOYSTICK) if k in keys]
    absc = {c for c, _ in caps.get(e.EV_ABS, [])}
    axes = [a for a in range(0, e.ABS_MISC) if a in absc and not e.ABS_HAT0X <= a <= e.ABS_HAT3Y]
    return buttons, axes


def _find_config(dev, roots) -> ET.Element | None:
    vid, pid = dev.info.vendor, dev.info.product
    for match_ids in (True, False):
        for root in roots:
            for c in root.findall('inputConfig'):
                if c.get('deviceName') == dev.name and (not match_ids or _guid_ids(c.get('deviceGUID', ''))[:2] == (vid, pid)):
                    return c
    return None


def _players(args: list[str]) -> list[str]:
    opt = {args[i][1:]: args[i + 1] for i in range(len(args) - 1) if args[i].startswith('-p') and args[i][2:3].isdigit()}
    players = sorted({int(''.join(ch for ch in k[1:3] if ch.isdigit())) for k in opt if k.endswith('guid')})
    if not players or any(f'p{p}devicepath' in opt for p in players):
        return args  # nothing to do, or ES already provides device paths
    userdata = Path(os.environ.get('ES_USERDATA', Path.home() / '.local/share/acrobato'))
    share = Path(os.environ.get('ES_SHARE', ''))
    def parse(f: Path) -> ET.Element:
        try:
            return ET.parse(f).getroot()
        except (OSError, ET.ParseError):
            return ET.Element('inputList')
    es_players = parse(PLAYERS_CFG)
    roots = [parse(userdata / 'system/configs/emulationstation/es_input.cfg'), parse(share / 'emulationstation/es_input.cfg')]

    pads = _evdev_pads()
    used: set[str] = set()
    out_root = ET.Element('inputList')
    new_args = [a for i, a in enumerate(args)
                if not (a.startswith('-p') and a[2:3].isdigit()) and not (i and args[i - 1].startswith('-p') and args[i - 1][2:3].isdigit())]
    for p in players:
        guid, name = opt.get(f'p{p}guid', ''), opt.get(f'p{p}name', '')
        vid, pid, hidapi = _guid_ids(guid)
        free = [d for d in pads if d.path not in used]
        dev = next((d for d in free if (d.info.vendor, d.info.product) == (vid, pid)), None)
        if dev is None and vid == STEAM_VID:  # Steam hardware read by Steam: games get its virtual pad
            dev = next((d for d in free if (d.info.vendor, d.info.product) == (STEAM_VID, STEAM_VIRTUAL_PID)), None)
        if dev is None:
            print(f'acrobato: player {p} ({name}): no matching input device', file=sys.stderr)
            continue
        same = (not hidapi and dev.name == name and (dev.info.vendor, dev.info.product) == (vid, pid))
        cfg = None
        if same:
            cfg = es_players.find(f'inputConfig[@deviceGUID="{guid}"]')
        if cfg is None:
            cfg = _find_config(dev, roots)
        if cfg is None:
            print(f'acrobato: player {p}: no controller mapping for {dev.name}', file=sys.stderr)
            continue
        used.add(dev.path)
        buttons, axes = _codes(dev)
        cfg = ET.fromstring(ET.tostring(cfg))
        for i in cfg.findall('input'):
            try:
                n = int(i.get('id', '-1'))
                if i.get('code') is None and i.get('type') == 'button' and 0 <= n < len(buttons):
                    i.set('code', str(buttons[n]))
                elif i.get('code') is None and i.get('type') == 'axis' and 0 <= n < len(axes):
                    i.set('code', str(axes[n]))
            except ValueError:
                pass
        out_root.append(cfg)
        from evdev import ecodes as e
        nhats = sum(1 for c, _ in dev.capabilities().get(e.EV_ABS, []) if e.ABS_HAT0X <= c <= e.ABS_HAT3Y) // 2
        new_args += [f'-p{p}index', str(pads.index(dev)), f'-p{p}guid', cfg.get('deviceGUID', guid),
                     f'-p{p}name', cfg.get('deviceName', dev.name), f'-p{p}devicepath', dev.path,
                     f'-p{p}nbbuttons', str(len(buttons)), f'-p{p}nbhats', str(nhats), f'-p{p}nbaxes', str(len(axes))]
        print(f'acrobato: player {p} -> {dev.path} ({dev.name})', file=sys.stderr)
    for d in pads:
        d.close()
    ET.ElementTree(out_root).write(PLAYERS_CFG, encoding='unicode', xml_declaration=True)
    return new_args


def main() -> int:
    args = sys.argv[1:]
    try:
        args = _fallback(args)
    except Exception as e:  # never block a launch because of this check
        print(f'acrobato: emulator check skipped: {e}', file=sys.stderr)
    try:
        args = _players(args)
    except Exception as e:
        print(f'acrobato: controller setup skipped: {e}', file=sys.stderr)
    from batocera_launch.cli.main import main as launch
    sys.argv = ['batocera-launch', *args]
    return launch()


if __name__ == '__main__':
    raise SystemExit(main())
