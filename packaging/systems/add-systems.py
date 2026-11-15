#!/usr/bin/env python3
"""Add AcroBato's own systems (Nintendo Switch, Switch 2, PlayStation 5) to the generated
EmulationStation and launcher data. Batocera has none of them.

Usage: add-systems.py <AppDir/usr/share>
- es_systems.cfg: the systems and their emulators (more than one = per-game EMULATOR choice)
- es_features.cfg: per-game/system settings for the Eden-family emulators (Eden, Eglantine,
  Lichii share qt-config.ini settings; see acrobato_emulators.NX_OPTIONS)
- batocera/launch/defaults/config-arch.yml: default emulator per system
- batocera/datainit/roms/<system>/_info.txt: what goes in each folder
The emulators are installed from the Content Downloader (packaging/store/emulators.json).
"""
import copy
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SHARE = Path(sys.argv[1])
HERE = Path(__file__).resolve().parent

# name, full name, maker, year, extensions, [(emulator, ...)] with the default first
SYSTEMS = [
    ('switch', 'Nintendo Switch', 'Nintendo', '2017', '.xci .nsp .nca .nro .nso .xcz .nsz .emuapp',
     ['eden', 'ryujinx', 'lichii']),
    ('switch2', 'Nintendo Switch 2', 'Nintendo', '2025', '.sw2 .nup .nx .emuapp', ['eglantine', 'lichii']),
    ('ps5', 'PlayStation 5', 'Sony', '2020', '.ps5 .elf .bin .self .json .emuapp', ['kyty']),
]
EDEN_FAMILY = ['eden', 'eglantine', 'lichii']

INFO = {
    'switch': """## Nintendo Switch

Games: .xci .nsp .nca .nro .nso (.xcz .nsz compressed)

Emulators (Updates & Downloads > Content Downloader): Eden (default), Ryujinx, Lichii.
Pick one per game in the game's ADVANCED GAME OPTIONS > EMULATOR.

Keys and firmware from a Switch you own:
- bios/switch/prod.keys and bios/switch/title.keys
- bios/switch/firmware/ (the firmware .nca files; Eden and Lichii pick them up automatically,
  for Ryujinx install them from its window)
They are copied into the emulator's profile before each game.

"Open <emulator>" entries in this list open the emulator's own window: settings, firmware,
controllers, updates and DLC.
""",
    'switch2': """## Nintendo Switch 2 (very experimental)

Games: .nup and .nx files, or dumps as folders named <game>.sw2 (containing base/exefs/main,
base/romfs, ...)

Emulators (Updates & Downloads > Content Downloader): Eglantine (default), Lichii.
Pick one per game in the game's ADVANCED GAME OPTIONS > EMULATOR. Graphics, memory and other
settings are there too.

Keys and firmware from a Switch 2 you own:
- bios/switch2/prod.keys and bios/switch2/title.keys
- bios/switch2/firmware/ (the firmware .nca files)
They are copied into the emulator's profile before each game.

Switch 2 games need a lot of memory (16 GB of RAM or more) and a strong graphics card.
AcroBato closes the emulator if memory runs out, before the computer freezes.

"Open <emulator>" entries in this list open the emulator's own window (on first start, Lichii
asks there whether to import another emulator's data or start fresh).
""",
    'ps5': """## PlayStation 5 (very experimental)

Games: game folders named <game>.ps5 (with eboot.bin inside), or eboot.bin / .elf / .self files

Emulator (Updates & Downloads > Content Downloader): KytyPS5.
Few games run yet.
""",
}


def es_command(root: ET.Element) -> str:
    ps4 = next(s for s in root.findall('system') if s.findtext('name') == 'ps4')
    return ps4.findtext('command')


def add_systems(path: Path) -> None:
    tree = ET.parse(path)
    root = tree.getroot()
    command = es_command(root)
    existing = {s.findtext('name') for s in root.findall('system')}
    for name, full, maker, year, exts, emus in SYSTEMS:
        if name in existing:
            continue
        s = ET.SubElement(root, 'system')
        for tag, val in (('fullname', full), ('name', name), ('manufacturer', maker), ('release', year),
                         ('hardware', 'console'), ('path', f'/userdata/roms/{name}'), ('extension', exts),
                         ('command', command), ('platform', name), ('theme', name)):
            ET.SubElement(s, tag).text = val
        el = ET.SubElement(s, 'emulators')
        for i, emu in enumerate(emus):
            e = ET.SubElement(el, 'emulator', name=emu)
            core = ET.SubElement(ET.SubElement(e, 'cores'), 'core')
            core.text = emu
            if i == 0:
                core.set('default', 'true')
    ET.indent(tree, space='  ')
    tree.write(path, encoding='unicode', xml_declaration=True)


def add_features(path: Path) -> None:
    tree = ET.parse(path)
    root = tree.getroot()
    src = ET.parse(HERE / 'es_features_switch2.cfg').getroot().find('emulator')
    for f in src.iter('feature'):  # eglantine_* -> nx_* (shared by the Eden family)
        f.set('value', f.get('value').replace('eglantine_', 'nx_'))
    existing = {e.get('name') for e in root.findall('emulator')}
    for emu in EDEN_FAMILY:
        if emu not in existing:
            e = copy.deepcopy(src)
            e.set('name', emu)
            root.append(e)
    for emu in ('ryujinx', 'kyty'):
        if emu not in existing:
            e = ET.SubElement(root, 'emulator', name=emu, features='')
            for shared in ('powermode', 'tdp', 'platformprofile', 'videomode'):
                ET.SubElement(e, 'sharedFeature', value=shared)
    ET.indent(tree, space='  ')
    tree.write(path, encoding='unicode', xml_declaration=True)


def add_defaults(path: Path) -> None:
    text = path.read_text() if path.exists() else ''
    for name, *_rest, emus in SYSTEMS:
        if f'\n{name}:' not in '\n' + text:
            text += f'{name}:\n  emulator: {emus[0]}\n  core: {emus[0]}\n'
    path.write_text(text)


def add_info() -> None:
    for name, text in INFO.items():
        d = SHARE / 'batocera/datainit/roms' / name
        d.mkdir(parents=True, exist_ok=True)
        (d / '_info.txt').write_text(text)


add_systems(SHARE / 'emulationstation/es_systems.cfg')
add_features(SHARE / 'emulationstation/es_features.cfg')
add_defaults(SHARE / 'batocera/launch/defaults/config-arch.yml')
add_info()
print('added systems:', ', '.join(s[0] for s in SYSTEMS))
