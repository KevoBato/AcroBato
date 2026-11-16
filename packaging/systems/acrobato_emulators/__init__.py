"""AcroBato emulators for batocera-launch: Switch (Eden, Ryujinx, Lichii), Switch 2
(Eglantine, Lichii) and PS5 (KytyPS5).

Batocera has no Switch or PS5 support; these follow the AcroBato Batocera add-ons
(Eglantine, KytyPS5). The emulators themselves are not bundled: they are installed from
Updates & Downloads > Content Downloader into <userdata>/emulators/usr/bin (see
acrobato_store.py). Registered under the `batocera_launch.emulators` entry points.

Per system and emulator:
- settings in <userdata>/system/configs/<system>/<emulator>   (XDG_CONFIG_HOME)
- saves, keys, firmware in <userdata>/saves/<system>/<emulator> (XDG_DATA_HOME)
Keys and firmware the user puts in <userdata>/bios/<system>/ are copied into the
emulator's profile before each launch.
A ROM ending in .emuapp (created by the downloader, e.g. "Open Eden.emuapp") opens the
emulator's own window instead of a game: for firmware, keys, controllers and settings.
"""
from __future__ import annotations

import filecmp
import json
import os
import re
import shutil
import urllib.request
from pathlib import Path

from batocera_common.dataclasses import cached_dataclass, cached_property
from batocera_launch import BatoceraException, Command, Emulator, HotkeysContext

USERDATA = Path(os.environ.get('ES_USERDATA', Path.home() / '.local/share/acrobato'))
EMU_BIN = Path(os.environ.get('ES_USR', USERDATA / 'emulators/usr')) / 'bin'
CATALOG_NAMES = {'eden': 'Eden', 'ryujinx': 'Ryujinx', 'eglantine': 'Eglantine', 'lichii': 'Lichii',
                 'kyty': 'KytyPS5', 'windows-arcade-loader': 'Windows Arcade Loader', 'ge-proton': 'GE-Proton'}


def notify(text: str) -> None:
    """Pop-up in EmulationStation (its local web API)."""
    try:
        req = urllib.request.Request('http://127.0.0.1:1234/notify', data=text.encode(), method='POST')
        urllib.request.urlopen(req, timeout=2).close()
    except Exception:
        pass


def installed_binary(emulator: str) -> Path:
    exe = EMU_BIN / emulator
    if not exe.exists():
        name = CATALOG_NAMES.get(emulator, emulator)
        msg = f'{name} is not installed. Get it from Updates & Downloads > Content Downloader.'
        notify(msg)
        raise BatoceraException(msg)
    return exe


def is_emulator_window(rom: Path) -> bool:
    return rom.suffix.lower() == '.emuapp'


def sync_files(src_dir: Path, names: tuple[str, ...], dest_dir: Path) -> None:
    """Copy files (or every file for names=('*',)) from src_dir to dest_dir when missing or different."""
    if not src_dir.is_dir():
        return
    files = [p for p in src_dir.iterdir() if p.is_file()] if names == ('*',) else [src_dir / n for n in names]
    for f in files:
        if f.is_file():
            d = dest_dir / f.name
            if not d.exists() or not filecmp.cmp(f, d, shallow=False):
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, d)


# --- Eden-family settings from ES (port of the Eglantine add-on's eglantine-settings.py) ---

# ES option -> qt-config.ini (section, key). ES choice values are the emulator's own values.
NX_OPTIONS = {
    'nx_console_mode': ('System', 'use_docked_mode'), 'nx_memory_layout': ('Core', 'memory_layout_mode'),
    'nx_language': ('System', 'language_index'), 'nx_region': ('System', 'region_index'),
    'nx_backend': ('Renderer', 'backend'), 'nx_resolution': ('Renderer', 'resolution_setup'),
    'nx_vsync': ('Renderer', 'use_vsync'), 'nx_scaling_filter': ('Renderer', 'scaling_filter'),
    'nx_fsr_sharpness': ('Renderer', 'fsr_sharpening_slider'), 'nx_anti_aliasing': ('Renderer', 'anti_aliasing'),
    'nx_aspect_ratio': ('Renderer', 'aspect_ratio'), 'nx_frame_gen': ('Renderer', 'frame_gen'),
    'nx_frame_gen_type': ('Renderer', 'frame_gen_type'), 'nx_frame_gen_multiplier': ('Renderer', 'frame_gen_multiplier'),
    'nx_gpu_accuracy': ('Renderer', 'gpu_accuracy'), 'nx_dma_accuracy': ('Renderer', 'dma_accuracy'),
    'nx_async_shaders': ('Renderer', 'use_asynchronous_shaders'),
    'nx_disk_shader_cache': ('Renderer', 'use_disk_shader_cache'), 'nx_anisotropy': ('Renderer', 'max_anisotropy'),
    'nx_astc_decode': ('Renderer', 'accelerate_astc'), 'nx_astc_recompression': ('Renderer', 'astc_recompression'),
    'nx_vram_usage': ('Renderer', 'vram_usage_mode'), 'nx_nvdec': ('Renderer', 'nvdec_emulation'),
    'nx_frame_pacing': ('Renderer', 'frame_pacing_mode'), 'nx_dyna_state': ('Renderer', 'dyna_state'),
    'nx_cpu_accuracy': ('Cpu', 'cpu_accuracy'), 'nx_multicore': ('Core', 'use_multi_core'),
    'nx_use_speed_limit': ('Core', 'use_speed_limit'), 'nx_speed_limit': ('Core', 'speed_limit'),
}


def es_options(system: str, game: str) -> dict[str, str]:
    """The nx_* options from batocera.conf: the game's own, else the system's."""
    name = os.path.basename(game.rstrip('/'))
    sys_opts, game_opts = {}, {}
    game_line = re.compile(r'^' + re.escape(system) + r'\["(.*)"\]\.(nx_\w+)=(.*)$')
    sys_line = re.compile(r'^' + re.escape(system) + r'\.(nx_\w+)=(.*)$')
    try:
        for line in (USERDATA / 'system/batocera.conf').read_text(errors='replace').splitlines():
            line = line.strip()
            if m := game_line.match(line):
                if name and m.group(1) == name:
                    game_opts[m.group(2)] = m.group(3)
            elif m := sys_line.match(line):
                sys_opts[m.group(1)] = m.group(2)
    except OSError:
        pass
    merged = {**sys_opts, **game_opts}
    return {k: v.strip() for k, v in merged.items() if k in NX_OPTIONS and v.strip() not in ('', 'auto', 'default')}


class QtIni:
    """Line-based editing of qt-config.ini (key\\default=... and key=... pairs)."""

    def __init__(self, path: Path):
        self.path = path
        try:
            self.lines = path.read_text(errors='replace').splitlines()
        except OSError:
            self.lines = []

    def _section(self, section):
        start = None
        for i, line in enumerate(self.lines):
            if line.strip() == f'[{section}]':
                start = i
            elif start is not None and line.startswith('['):
                return start, i
        return (start, len(self.lines)) if start is not None else (None, None)

    def _find(self, section, key):
        start, end = self._section(section)
        if start is None:
            return None
        for i in range(start + 1, end):
            if self.lines[i].startswith(key + '='):
                return i
        return None

    def get(self, section, key):
        i = self._find(section, key)
        if i is None:
            return None
        j = self._find(section, key + '\\default')
        return [self.lines[i].split('=', 1)[1], self.lines[j].split('=', 1)[1] if j is not None else None]

    def set(self, section, key, value, default):
        start, _ = self._section(section)
        if start is None:
            self.lines += ['', f'[{section}]']
            start = len(self.lines) - 1
        for name, val in ((key + '\\default', default), (key, value)):
            if val is None:
                continue
            i = self._find(section, name)
            if i is None:
                self.lines.insert(start + 1, f'{name}={val}')
            else:
                self.lines[i] = f'{name}={val}'

    def remove(self, section, key):
        for name in (key, key + '\\default'):
            if (i := self._find(section, name)) is not None:
                del self.lines[i]

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text('\n'.join(self.lines) + '\n')
        tmp.replace(self.path)


def apply_es_options(qt_config: Path, state_file: Path, system: str, game: str) -> None:
    """Write the ES choices for this game into qt-config.ini. An option left on default in ES
    gets back the emulator's own value (as set in its window), so one game's choices don't
    leak into the next."""
    wanted = es_options(system, game) if game else {}
    try:
        state = json.loads(state_file.read_text())
    except (OSError, ValueError):
        state = {}
    ini, changed = QtIni(qt_config), False
    for option, (section, key) in NX_OPTIONS.items():
        cur = ini.get(section, key)
        cur_value = cur[0] if cur else None
        saved, value = state.get(option), wanted.get(option)
        if value is not None:
            base = cur if saved is None or cur_value != saved['written'] else saved['base']
            if cur_value != value or (cur and cur[1] != 'false'):
                ini.set(section, key, value, 'false')
                changed = True
            state[option] = {'base': base, 'written': value}
        elif saved is not None:
            if cur_value == saved['written']:
                if saved['base'] is None:
                    ini.remove(section, key)
                else:
                    ini.set(section, key, saved['base'][0], saved['base'][1])
                changed = True
            del state[option]
    if changed:
        ini.save()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state))


# --- Eden-family controls from the controllers ES passes ---------------------------------------

# Switch button -> ES input name (Batocera's positional layout: ES "a" is the right face button,
# like the Switch's A). The pads' SDL numbers come straight from ES's controller config.
NX_BUTTONS = {
    'button_a': 'a', 'button_b': 'b', 'button_x': 'x', 'button_y': 'y',
    'button_lstick': 'l3', 'button_rstick': 'r3', 'button_l': 'pageup', 'button_r': 'pagedown',
    'button_zl': 'l2', 'button_zr': 'r2', 'button_plus': 'start', 'button_minus': 'select',
    'button_dup': 'up', 'button_ddown': 'down', 'button_dleft': 'left', 'button_dright': 'right',
    'button_slleft': 'pageup', 'button_srleft': 'pagedown', 'button_slright': 'pageup', 'button_srright': 'pagedown',
}
HAT_DIRECTIONS = {'1': 'up', '2': 'right', '4': 'down', '8': 'left'}


def nx_binding(guid: str, port: int, inp) -> str:
    if inp.type == 'button':
        return f'"engine:sdl,guid:{guid},port:{port},button:{inp.id}"'
    if inp.type == 'hat':
        return f'"engine:sdl,guid:{guid},hat:{inp.id},port:{port},direction:{HAT_DIRECTIONS.get(inp.value, "up")}"'
    if inp.type == 'axis':
        sign = '-' if inp.value.startswith('-') else '+'
        return f'"engine:sdl,guid:{guid},threshold:0.500000,port:{port},axis:{inp.id},invert:{sign}"'
    return '[empty]'


def nx_stick(guid: str, port: int, x, y) -> str:
    return (f'"engine:sdl,guid:{guid},axis_x:{x.id},offset_x:-0.000000,invert_y:+,deadzone:0.150000,'
            f'port:{port},axis_y:{y.id},offset_y:0.000000,invert_x:+"')


def wanted_controls(controllers) -> dict[str, str]:
    """[Controls] keys for the players' controllers, as the emulator's own controller setup
    would write them (Pro Controller, SDL bindings)."""
    out: dict[str, str] = {}
    players = sorted((c for c in controllers or [] if c is not None and c.type == 'joystick'),
                     key=lambda c: c.player_number)[:8]
    seen: dict[str, int] = {}
    for n in range(8):
        if n >= len(players):
            out[f'player_{n}_connected'] = 'false'
            continue
        c = players[n]
        port = seen.get(c.guid, 0)
        seen[c.guid] = port + 1
        inputs = c.inputs
        out[f'player_{n}_type'] = '0'
        out[f'player_{n}_connected'] = 'true'
        for key, es_name in NX_BUTTONS.items():
            if es_name in inputs:
                out[f'player_{n}_{key}'] = nx_binding(c.guid, port, inputs[es_name])
        # Home: the hotkey button when it's a button of its own. Steam's virtual pads use Select
        # as hotkey (Steam keeps the Steam/Guide button), but still report Guide as button 8.
        hotkey, select = inputs.get('hotkey'), inputs.get('select')
        if hotkey and not (select and (hotkey.type, hotkey.id) == (select.type, select.id)):
            out[f'player_{n}_button_home'] = nx_binding(c.guid, port, hotkey)
        elif c.guid[8:20] == 'de280000ff11':  # Steam virtual gamepad (28de:11ff)
            out[f'player_{n}_button_home'] = f'"engine:sdl,guid:{c.guid},port:{port},button:8"'
        for stick, (xs, ys) in (('lstick', ('joystick1left', 'joystick1up')), ('rstick', ('joystick2left', 'joystick2up'))):
            if xs in inputs and ys in inputs:
                out[f'player_{n}_{stick}'] = nx_stick(c.guid, port, inputs[xs], inputs[ys])
    return out


def apply_controls(qt_config: Path, state_file: Path, controllers) -> None:
    """Map the players' controllers so games work without setting controls first, while
    anything the user sets in the emulator's own controls window wins.

    A control is written only when it's unset (or on the emulator's default), or still holds
    exactly what AcroBato wrote last time. Once the user changes it in the emulator, it differs
    and is left alone from then on; "Restore defaults" there hands it back to AcroBato.
    Per-game controls set in the emulator live in its per-game files and are never touched."""
    try:
        state = json.loads(state_file.read_text())
    except (OSError, ValueError):
        state = {}
    ini, changed = QtIni(qt_config), False
    for key, value in wanted_controls(controllers).items():
        cur = ini.get('Controls', key)
        ours = state.get(key)
        free = cur is None or cur[1] == 'true' or cur[0] in ('', '[empty]')
        if free or (ours is not None and cur[0] == ours):
            if cur is None or cur[0] != value:  # already right: leave the line as it is
                ini.set('Controls', key, value, 'false')
                changed = True
            state[key] = value
        else:
            state.pop(key, None)  # the user's own setting
    if changed:
        ini.save()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state))


# --- emulators ----------------------------------------------------------------------------------

@cached_dataclass
class _Standalone(Emulator):
    """Common parts: per-system profile folders, exit = close the emulator (Alt+F4 is turned
    into a direct close by AcroBato's hotkeygen)."""

    emulator_id = ''

    @cached_property
    def hotkeygen_context(self) -> HotkeysContext:
        return {'name': self.emulator_id, 'keys': {'exit': ['KEY_LEFTALT', 'KEY_F4']}}

    @cached_property
    def config_home(self) -> Path:
        return USERDATA / 'system/configs' / self.system / self.emulator_id

    @cached_property
    def data_home(self) -> Path:
        return USERDATA / 'saves' / self.system / self.emulator_id

    def xdg_env(self) -> dict[str, str]:
        cache = USERDATA / 'system/cache' / self.system / self.emulator_id
        for d in (self.config_home, self.data_home, cache):
            d.mkdir(parents=True, exist_ok=True)
        # DISABLE_AUTO_UPDATES: Eden's AppImage (and others built with the same tooling) asks
        # "Allow ... to check for updates?" on first start; updates come from the Content Downloader
        return {'XDG_CONFIG_HOME': str(self.config_home), 'XDG_DATA_HOME': str(self.data_home),
                'XDG_CACHE_HOME': str(cache), 'QT_QPA_PLATFORM': 'xcb', 'DISABLE_AUTO_UPDATES': '1'}


@cached_dataclass
class _EdenFamily(_Standalone):
    """Eden and its forks (Eglantine, Lichii): `<exe> -f -g <game>`, settings in
    <XDG_CONFIG_HOME>/<profile>/qt-config.ini, keys and firmware in <XDG_DATA_HOME>/<profile>."""

    profile = 'eden'

    def game_file(self) -> Path:
        rom = Path(self.rom)
        if not rom.is_dir():
            return rom
        # Switch 2 dumps are folders (base/exefs/main, base/romfs, updates/<version>/...): the
        # emulator wants an exefs/main. Many games only boot from their newest update, so that
        # one is used when there is one (update folders are named by version number).
        updates = [u for u in (rom / 'updates').glob('*/exefs/main') if u.is_file()]
        if updates:
            def version(p: Path) -> tuple[int, str]:
                name = p.parent.parent.name
                return (int(name), name) if name.isdigit() else (-1, name)
            return max(updates, key=version)
        for candidate in ('base/exefs/main', 'exefs/main'):
            if (rom / candidate).is_file():
                return rom / candidate
        found = sorted(rom.glob('**/exefs/main'))
        if not found:
            raise BatoceraException(f'No exefs/main found in {rom}')
        return found[0]

    async def configure(self) -> Command:
        exe = installed_binary(self.emulator_id)
        env = self.xdg_env()
        data = self.data_home / self.profile
        bios = USERDATA / 'bios' / self.system
        sync_files(bios, ('prod.keys', 'title.keys'), data / 'keys')
        sync_files(bios / 'firmware', ('*',), data / 'nand/system/Contents/registered')
        game = '' if is_emulator_window(Path(self.rom)) else str(Path(self.rom))
        apply_es_options(self.config_home / self.profile / 'qt-config.ini',
                         self.config_home / 'acrobato-es-options.json', self.system, game)
        if not game:
            return Command([exe], env=env)
        apply_controls(self.config_home / self.profile / 'qt-config.ini',
                       self.config_home / 'acrobato-controls.json', self.controllers)
        # acrobato-watchdog closes the emulator before it runs the machine out of memory
        return Command(['acrobato-watchdog', exe, '-f', '-g', self.game_file()], env=env)


@cached_dataclass
class Eden(_EdenFamily):
    emulator_id = 'eden'
    profile = 'eden'


@cached_dataclass
class Eglantine(_EdenFamily):
    emulator_id = 'eglantine'
    profile = 'eden'  # Eglantine keeps Eden's folder names


@cached_dataclass
class Lichii(_EdenFamily):
    emulator_id = 'lichii'
    profile = 'lichii'


@cached_dataclass
class Ryujinx(_Standalone):
    """Ryujinx (Ryubing), from Flathub. Flatpak sets its own XDG folders inside the sandbox,
    so the data folder (keys, firmware, saves, settings) is given with --root-data-dir."""

    emulator_id = 'ryujinx'

    async def configure(self) -> Command:
        exe = installed_binary(self.emulator_id)
        env = self.xdg_env()
        root = self.config_home
        bios = USERDATA / 'bios' / self.system
        sync_files(bios, ('prod.keys', 'title.keys'), root / 'system')
        args: list[str | Path] = [exe, '--root-data-dir', root]
        if is_emulator_window(Path(self.rom)):
            return Command(args, env=env)
        return Command(['acrobato-watchdog', *args, '--fullscreen', Path(self.rom)], env=env)


@cached_dataclass
class Kyty(_Standalone):
    """KytyPS5: `kyty_emulator --game <eboot.bin> --fullscreen` (AMD CPUs also need --amd-cpu)."""

    emulator_id = 'kyty'

    async def configure(self) -> Command:
        exe = installed_binary(self.emulator_id)
        rom = Path(self.rom)
        if is_emulator_window(rom):
            # Kyty's own window (settings) is the kyty_launcher next to kyty_emulator
            app = USERDATA / 'emulators/apps/kyty'
            return Command(['sh', '-c', 'cd "$0" && exec ./kyty_launcher', app],
                           env={'QT_QPA_PLATFORM': 'xcb'})
        game = rom
        if rom.is_dir():
            for candidate in ('eboot.bin', 'sce_module/eboot.bin'):
                if (rom / candidate).is_file():
                    game = rom / candidate
                    break
        args = [exe, '--game', game, '--fullscreen']
        try:
            if 'AuthenticAMD' in Path('/proc/cpuinfo').read_text(errors='replace'):
                args.append('--amd-cpu')
        except OSError:
            pass
        return Command(args, env={'QT_QPA_PLATFORM': 'xcb', 'SDL_VIDEODRIVER': 'x11'})


# --- Windows Arcade Loader (Taito Type X, NESiCAxLive, Sega RingEdge, Namco ES3, ...) ------------

def _yaml(value: str | bool) -> str:
    return ('true' if value else 'false') if isinstance(value, bool) else json.dumps(str(value))


@cached_dataclass
class WindowsArcadeLoader(_Standalone):
    """Windows arcade games in Wine through aderumier's Windows Arcade Loader (GPL-3.0,
    https://github.com/aderumier/windowsarcadeloader), as in Pixel Nostalgia's Batocera builds:
    its arcade-launcher runs the game with the cabinet's I/O, dongle and network services
    emulated, and maps the pads itself. Port of its Batocera generator
    (tools/batocera/windowsArcadeLoaderGenerator.py) to batocera-launch.

    The game is <dump>/<gameid>.windowsloader (the game id picks the loader's profile).
    Needs GE-Proton (the Wine runner), also from the Content Downloader. The loader keeps its
    Wine prefix and user profiles (controls per game, wheels, player order, cards) in its
    own folder; its GUI ("Open Windows Arcade Loader") edits them."""

    emulator_id = 'windows-arcade-loader'

    @cached_property
    def hotkeygen_context(self) -> HotkeysContext:
        # exit: the launcher stops the game (and Wine) on SIGTERM; coin: P1 coin (key 5)
        return {'name': self.emulator_id,
                'keys': {'exit': 'pkill -TERM -u "$(id -u)" -x arcade-launcher', 'coin': 'KEY_5'}}

    def _launcher_yaml(self, app: Path, runner: Path) -> None:
        """Machine settings (layer 2 of every game profile): the GE-Proton from the Content
        Downloader. Left alone once the user writes their own (no AcroBato marker line)."""
        # The loader wants a Wine tree (bin/wine, lib/wine/...): GE-Proton's is its files/, so
        # runners_dir is the GE-Proton folder and the runner "files".
        # winetricks (Windows components for the Wine prefix): the loader looks in the runner's
        # bin/, then <runners_dir>/winetricks; GE-Proton ships one in protonfixes/
        tricks = runner / 'winetricks'
        if not tricks.exists() and (runner / 'protonfixes/winetricks').exists():
            tricks.unlink(missing_ok=True)
            tricks.symlink_to('protonfixes/winetricks')
        f = app / 'launcher.yaml'
        marker = '# Written by AcroBato'
        text = f.read_text(errors='replace') if f.exists() else ''
        # the release ships Batocera's (paths under /userdata/system/wine/custom): replaced
        if text and not text.startswith(marker) and '/userdata/system/wine/custom' not in text:
            return  # the user's own
        f.write_text(f'{marker} (remove this line to keep your own changes)\n'
                     f'runners_dir: {json.dumps(str(runner))}\n'
                     'runner: files\n'
                     'payloads_dir: payloads\n'
                     f'squashfs_saves: {json.dumps(str(USERDATA / "saves"))}\n')

    def _options_layer(self) -> Path:
        """The ES options as an extra profile layer (only the ones set, so a game's own
        profile setting stays unless the user picks another)."""
        get = self.config.get
        top, inputs, env = {}, {'exit_combo': '[]'}, {}
        if get('wal_reshade') in ('0', '1'):
            top['reshade'] = _yaml(get('wal_reshade') == '1')
        if get('wal_renderer') in ('dxvk', 'wined3d'):
            top['dxvk'] = _yaml(get('wal_renderer') == 'dxvk')
        if get('wal_mouse_guns') in ('0', '1'):
            inputs['guns_mouse'] = _yaml(get('wal_mouse_guns') == '1')
        if get('wal_keyboard') in ('0', '1'):
            inputs['keyboard_enabled'] = _yaml(get('wal_keyboard') == '1')
        if get('wal_sinden_border') in ('auto', '0', '1'):
            env['WAL_SINDEN_BORDER'] = _yaml(get('wal_sinden_border'))
        if get('wal_sinden_border_size'):
            env['WAL_SINDEN_BORDER_SIZE'] = _yaml(get('wal_sinden_border_size'))
        if get('wal_sinden_border_color'):
            env['WAL_SINDEN_BORDER_COLOR'] = _yaml(get('wal_sinden_border_color'))
        env['WAL_SINDEN_DETECTED'] = _yaml('1' if any(getattr(g, 'needs_borders', False) for g in self.guns or []) else '0')
        if get('keep_aspect_ratio') in ('on', 'off'):
            env['WAL_KEEP_ASPECT_RATIO'] = _yaml('1' if get('keep_aspect_ratio') == 'on' else '0')
        if get('wal_crosshair') in ('0', '1'):
            env['WAL_CROSSHAIR'] = _yaml(get('wal_crosshair'))
        if get('wal_freeplay') in ('0', '1'):
            env['WAL_FREEPLAY'] = _yaml(get('wal_freeplay'))
        lines = [f'{k}: {v}' for k, v in top.items()]
        for name, section in (('input', inputs), ('env', env)):
            if section:
                lines.append(f'{name}:')
                lines += [f'  {k}: {v}' for k, v in section.items()]
        layer = self.config_home / 'es-options.yaml'
        layer.parent.mkdir(parents=True, exist_ok=True)
        layer.write_text('\n'.join(lines) + '\n')
        return layer

    async def configure(self) -> Command:
        installed_binary(self.emulator_id)
        app = USERDATA / 'emulators/apps' / self.emulator_id
        runner = USERDATA / 'emulators/apps/ge-proton'
        if not (runner / 'files/bin/wine').exists():
            msg = 'Windows Arcade Loader needs GE-Proton. Get it from Updates & Downloads > Content Downloader.'
            notify(msg)
            raise BatoceraException(msg)
        self._launcher_yaml(app, runner)
        # First game: the loader builds its shared Wine prefix (about 40 winetricks verbs:
        # DirectX, Visual C++ runtimes..., recorded in .wal-tricks), many minutes with no window
        tricks = app / 'wine-prefix/full/.wal-tricks'
        done = len(tricks.read_text(errors='replace').split()) if tricks.exists() else 0
        if not is_emulator_window(self.rom) and done < 35:
            notify('Windows Arcade Loader: setting up Wine for the first game. This downloads Windows '
                   'components and can take 10 minutes or more; the game starts when it is done.')
        env = {
            # the pads' ES mappings, ES's player order (by device), no HIDAPI (as in Batocera)
            'SDL_GAMECONTROLLERCONFIG': self.get_sdl_game_controller_config(),
            'SDL_JOYSTICK_HIDAPI': '0',
            'WAL_PLAYER_PADS': ';'.join(c.device_path for c in self.controllers or [] if c and c.device_path),
        }
        if is_emulator_window(Path(self.rom)):
            return Command(['sh', '-c', 'cd "$0" && exec ./arcade-launcher gui --root "$0"', app], env=env)
        layer = self._options_layer()
        return Command(['sh', '-c', 'cd "$0" && exec ./arcade-launcher run "$1" --root "$0" --profile "$2"',
                        app, Path(self.rom), layer], env=env)
