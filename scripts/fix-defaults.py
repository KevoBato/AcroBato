#!/usr/bin/env python3
"""Point each system's default emulator at something this app actually offers.

Batocera's defaults (launch/defaults/config.yml) assume Batocera's full set of
cores. Here only some cores are bundled and other emulators are downloadable, as
listed in the generated es_systems.cfg. For every system whose default
(emulator, core) is not listed there, write an override into config-arch.yml
(which batocera-launch merges on top of config.yml): the first bundled libretro
core if any, otherwise the first downloadable emulator.

Usage: fix-defaults.py <share dir>   (run with a Python that has PyYAML)
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

share = Path(sys.argv[1])
defaults_dir = share / 'batocera' / 'launch' / 'defaults'
base = yaml.safe_load((defaults_dir / 'config.yml').read_text()) or {}
arch_path = defaults_dir / 'config-arch.yml'
arch = yaml.safe_load(arch_path.read_text()) if arch_path.exists() else {}
arch = arch or {}

# RetroArch cores from the Content Downloader (not in the AppImage): a system that also has a
# bundled core defaults to the bundled one, so it works without a download (standalone
# emulators fall back to a bundled core at launch instead, see acrobato_launch.py)
import json
catalog = Path(__file__).resolve().parent.parent / 'packaging' / 'store' / 'emulators.json'
downloadable = {e['source']['core'] for e in json.loads(catalog.read_text())['emulators']
                if e['source']['type'] == 'libretro'}

changed = []
for system in ET.parse(share / 'emulationstation' / 'es_systems.cfg').getroot().findall('system'):
    name = system.findtext('name')
    offered = [(e.get('name'), c.text) for e in system.iter('emulator') for c in e.iter('core')]
    if not offered:
        continue
    bundled = [(e, c) for e, c in offered if e == 'libretro' and c not in downloadable]
    cur = {**(base.get('default') or {}), **(arch.get('default') or {}),
           **(base.get(name) or {}), **(arch.get(name) or {})}
    cur_pair = (cur.get('emulator'), cur.get('core'))
    if cur_pair in offered and not (cur_pair[0] == 'libretro' and cur_pair[1] in downloadable and bundled):
        continue
    emu, core = (bundled or [(e, c) for e, c in offered if e == 'libretro'] or offered)[0]
    entry = arch.setdefault(name, {}) or {}
    entry.update({'emulator': emu, 'core': core})
    arch[name] = entry
    changed.append(f"{name}: {cur.get('emulator')}/{cur.get('core')} -> {emu}/{core}")

arch_path.write_text(yaml.safe_dump(arch, sort_keys=False))
print(f'{len(changed)} system defaults changed')
for c in changed:
    print('  ' + c)
