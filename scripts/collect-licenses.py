#!/usr/bin/env python3
"""Collect license texts and write NOTICES.md for everything bundled in the AppDir.

Run at the end of build-appdir.sh, inside the build container (needs dpkg for the
system libraries): collect-licenses.py <AppDir> <WORK> <batocera.linux checkout> <project dir>
Output: <AppDir>/usr/share/acrobato/licenses/ (license texts) and .../NOTICES.md (summary).
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

A, WORK, BL, HERE = (Path(p) for p in sys.argv[1:5])
OUT = A / 'usr/share/acrobato/licenses'
SRC = WORK / 'deps/src'
CORES = SRC / 'cores'
LIC_NAMES = re.compile(r'^(licen[cs]e|copying)', re.I)

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
rows = []  # (component, version, license, source, files)
missing = []


def copy(dest_name: str, *sources: Path) -> list[str]:
    """Copy license files into OUT/<dest_name>/ and return their relative paths."""
    got = []
    for s in sources:
        if s.is_file():
            d = OUT / dest_name
            d.mkdir(parents=True, exist_ok=True)
            shutil.copy(s, d / s.name)
            got.append(f'{dest_name}/{s.name}')
    if not got:
        missing.append(dest_name)
    return got


def top_licenses(d: Path) -> list[Path]:
    return sorted(p for p in d.iterdir() if p.is_file() and LIC_NAMES.match(p.name)) if d.is_dir() else []


def git_rev(d: Path) -> str:
    try:
        return subprocess.run(['git', '-C', str(d), 'rev-parse', '--short=10', 'HEAD'], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return ''


# --- AcroBato itself ---------------------------------------------------------------
rows.append(('AcroBato (build scripts, patches, launcher glue, scrapers, downloader)',
             (A / 'usr/share/acrobato/version').read_text().strip() if (A / 'usr/share/acrobato/version').exists() else '',
             'GPL-3.0-or-later', 'AcroBato source repository', copy('acrobato', HERE / 'LICENSE')))

# --- EmulationStation, Batocera, RetroArch, evmapy ---------------------------------
es = WORK / 'src/es'
rows.append(('batocera-emulationstation', git_rev(es), 'MIT (fonts: Apache-2.0 / Ubuntu Font Licence)',
             'https://github.com/batocera-linux/batocera-emulationstation',
             copy('emulationstation', es / 'LICENSE.md', es / 'opensans_license.txt', es / 'ubuntu_licence.txt')))
rows.append(('Batocera (batocera-launch, hotkeygen, system data, controller database, es_systems)',
             git_rev(BL), 'LGPL-3.0-or-later', 'https://github.com/batocera-linux/batocera.linux',
             copy('batocera', BL / 'COPYING', BL / 'COPYING.LESSER', BL / 'LICENSE-NOTICE')))
ev = WORK / 'src/evmapy'
rows.append(('evmapy (with Batocera patches)', git_rev(ev), 'GPL-2.0', 'https://github.com/kempniu/evmapy',
             copy('evmapy', *top_licenses(ev))))
ra = SRC / 'retroarch'
rows.append(('RetroArch', git_rev(ra), 'GPL-3.0', 'https://github.com/libretro/RetroArch', copy('retroarch', *top_licenses(ra))))

# --- SDL, FFmpeg ----------------------------------------------------------------------
for name, d, url in (('SDL2', next((p for p in SRC.glob('SDL2-*') if p.is_dir()), None), 'https://libsdl.org'),
                     ('SDL3', next((p for p in SRC.glob('SDL3-*') if p.is_dir()), None), 'https://libsdl.org'),
                     ('SDL2_mixer', SRC / 'SDL_mixer', 'https://github.com/libsdl-org/SDL_mixer')):
    if d:
        rows.append((name, d.name.split('-', 1)[-1] if '-' in d.name else git_rev(d),
                     'Zlib (SDL2 and SDL3 with Batocera input patches)', url, copy(name.lower(), *top_licenses(d))))
ff = SRC / 'ffmpeg'
rows.append(('FFmpeg (minimal build, LGPL configuration)', git_rev(ff), 'LGPL-2.1-or-later', 'https://ffmpeg.org',
             copy('ffmpeg', ff / 'COPYING.LGPLv2.1', ff / 'LICENSE.md')))

# --- RetroArch cores -------------------------------------------------------------------
SPECIAL = {  # cores whose license is not in a top-level LICENSE/COPYING file
    'handy': ['lynx/license.txt'], 'stella2014': ['stella/license.txt'], 'fbneo': ['src/license.txt', 'LICENSE.md'],
    'parallel-n64': ['mupen64plus-rsp-cxd4/COPYING', 'gles2n64/src/COPYING',
                     'mupen64plus-video-paraLLEl/parallel-rdp/LICENSE'],
}
NOTE = {
    'snes9x': 'Snes9x license (non-commercial)', 'genesisplusgx': 'Genesis Plus GX license (non-commercial)',
    'picodrive': 'MAME-style license (non-commercial)', 'fbneo': 'FBNeo license (non-commercial, no donations)',
    'opera': 'FreeDO modified LGPL (non-commercial, credits required)', 'mgba': 'MPL-2.0', 'handy': 'Zlib',
    'melonds': 'GPL-3.0', 'swanstation': 'GPL-3.0', 'vecx': 'GPL-3.0', 'neocd': 'LGPL-3.0',
    'bluemsx': 'BSD-style / GPL (per file)', 'dolphin': 'GPL-2.0-or-later (some parts other licenses)',
    'parallel-n64': 'GPL-2.0 (parts MIT)', 'ppsspp': 'GPL-2.0-or-later',
}
table = re.search(r"TABLE='(.*?)'", (HERE / 'scripts/build-cores.sh').read_text(), re.S).group(1)
for line in table.strip().splitlines():
    pkg = line.split('|')[0].strip()
    d = CORES / pkg
    if not d.is_dir():
        continue
    files =[d / p for p in SPECIAL.get(pkg, [])] or top_licenses(d)
    if pkg == 'opera':  # license is in the source file headers
        hdr = (d / 'libopera/opera_arm.c').read_text(errors='replace')
        m = re.search(r'/\*(.*?FreeDO licensed under.*?)\*/', hdr, re.S)
        (OUT / 'cores-opera').mkdir(parents=True, exist_ok=True)
        (OUT / 'cores-opera/LICENSE-FreeDO.txt').write_text((m.group(1) if m else hdr[:3000]).strip() + '\n')
        got = ['cores-opera/LICENSE-FreeDO.txt']
    else:
        got = copy(f'cores-{pkg}', *files)
    lic = NOTE.get(pkg) or ('GPL-2.0' if got and 'Version 2' in (OUT / got[0]).read_text(errors='replace')[:400] else 'see license file')
    rows.append((f'{pkg} (RetroArch core)', git_rev(d), lic, f'libretro core source ({pkg}), see Batocera recipe', got))
info = CORES / 'libretro-core-info'
rows.append(('libretro core info files', git_rev(info), 'MIT', 'https://github.com/libretro/libretro-core-info',
             copy('libretro-core-info', *top_licenses(info))))

# --- data bundled with the app ------------------------------------------------------------
rows.append(('Carbon theme for EmulationStation', '', 'no license stated (by Rookervik, based on "simple" by Nils '
             'Bonenberger; maintained by fabricecaruso); credits in its readme.txt',
             'https://github.com/fabricecaruso/es-theme-carbon',
             copy('theme-carbon', A / 'usr/share/emulationstation/themes/es-theme-carbon/readme.txt')))
rows.append(('RetroArch assets (menu icons, sounds)', '', 'CC-BY-4.0', 'https://github.com/libretro/retroarch-assets', []))
rows.append(('RetroArch shaders (slang/glsl presets used by Batocera)', '', 'various, per shader (see each file header)',
             'https://github.com/libretro/slang-shaders', []))
rows.append(('Dolphin "Sys" data / PPSSPP assets', '', 'GPL-2.0-or-later (part of Dolphin / PPSSPP)',
             'https://github.com/dolphin-emu/dolphin, https://github.com/hrydgard/ppsspp', []))

# --- Python and its packages ----------------------------------------------------------------
py = A / 'usr/python/lib/python3.14'
rows.append(('Python 3.14 (python-build-standalone)', '', 'PSF-2.0 (bundled libraries: see its LICENSE.txt)',
             'https://github.com/astral-sh/python-build-standalone', copy('python', py / 'LICENSE.txt')))
for di in sorted((py / 'site-packages').glob('*.dist-info')):
    meta = (di / 'METADATA').read_text(errors='replace') if (di / 'METADATA').exists() else ''
    name = re.search(r'^Name: (.*)$', meta, re.M); ver = re.search(r'^Version: (.*)$', meta, re.M)
    lic = re.search(r'^License-Expression: (.*)$', meta, re.M) or re.search(r'^License: (.*)$', meta, re.M)
    cls = re.findall(r'^Classifier: License :: (?:OSI Approved :: )?(.*)$', meta, re.M)
    lic_s = (lic.group(1).strip() if lic and len(lic.group(1)) < 80 else '') or ', '.join(cls) or 'see license file'
    files = [p for p in di.rglob('*') if p.is_file() and LIC_NAMES.match(p.name)]
    n = name.group(1).strip() if name else di.name
    if n == 'acrobato-emulators':  # AcroBato's own (packaging/systems)
        rows.append((f'{n} (Python package, part of AcroBato)', ver.group(1).strip() if ver else '',
                     'GPL-3.0-or-later', 'AcroBato source repository', ['acrobato/LICENSE']))
        continue
    if n.startswith(('batocera', 'python-batocera')) or n == 'hotkeygen':  # part of batocera.linux
        rows.append((f'{n} (Python package, part of Batocera)', ver.group(1).strip() if ver else '',
                     'LGPL-3.0-or-later', 'https://github.com/batocera-linux/batocera.linux',
                     ['batocera/COPYING.LESSER', 'batocera/LICENSE-NOTICE']))
        continue
    rows.append((f'{n} (Python package)', ver.group(1).strip() if ver else '', lic_s, 'https://pypi.org/project/' + n,
                 copy(f'python-{n}', *files)))

# --- system libraries bundled from Ubuntu 22.04 (Debian copyright files) ---------------------
libs = sorted(p.name for p in (A / 'usr/lib').glob('*.so*') if p.name not in
              ('libSDL2-2.0.so.0', 'libSDL2_mixer-2.0.so.0', 'libSDL3.so.0') and not p.name.startswith(('libav', 'libsw')))
pkgs: dict[str, list[str]] = {}
for lib in libs:
    r = subprocess.run(['dpkg', '-S', f'*/{lib}'], capture_output=True, text=True)
    pkg = r.stdout.split(':', 1)[0].strip() if r.returncode == 0 and r.stdout else ''
    pkgs.setdefault(pkg or '(unknown)', []).append(lib)
vlc = subprocess.run(['dpkg', '-S', '/usr/lib/x86_64-linux-gnu/vlc/plugins'], capture_output=True, text=True).stdout
for p in {x.split(':')[0].strip() for x in vlc.replace(', ', '\n').splitlines() if ':' in x} or set():
    pkgs.setdefault(p, []).append('VLC plugins')
for pkg, its in sorted(pkgs.items()):
    if pkg == '(unknown)':
        rows.append((', '.join(its), '', 'unknown: not from an Ubuntu package', '', []))
        continue
    src = Path(f'/usr/share/doc/{pkg}/copyright')
    ver = subprocess.run(['dpkg-query', '-W', '-f=${Version}', pkg], capture_output=True, text=True).stdout
    rows.append((f'{pkg} ({", ".join(its)})', ver, 'see Debian copyright file', f'Ubuntu 22.04 package {pkg}',
                 copy(f'ubuntu-{pkg}', src)))

# --- NOTICES.md -------------------------------------------------------------------------------
md = ['# AcroBato third-party notices', '',
      'AcroBato bundles the open-source software listed below. Each component remains under its own',
      'license; the full texts are in this folder (`usr/share/acrobato/licenses/` in the AppImage).', '',
      '## Source code', '',
      'Source code for the GPL/LGPL/MPL components is available from the upstream projects listed below, at the',
      'versions shown. AcroBato\'s own build scripts and its changes to these projects are published in the AcroBato',
      'source repository.', '',
      '## Restrictions to be aware of', '',
      '- **Non-commercial cores:** Snes9x, Genesis Plus GX, PicoDrive, FinalBurn Neo and Opera may not be sold or used',
      '  in a commercial product or activity. AcroBato must stay free to include them.',
      '- **FinalBurn Neo** additionally forbids asking for donations for a project that uses its code.',
      '- **Opera (3DO)** requires full credit to the FreeDO authors (Alexander Troosh, Maxim Grishin and others).',
      '- No BIOS files or commercial games are included. Users supply their own.', '',
      '## Components', '', '| Component | Version | License | Source | License files |', '|---|---|---|---|---|']
for comp, ver, lic, src, files in rows:
    md.append(f'| {comp} | {ver} | {lic} | {src} | {", ".join(files) if files else "-"} |'.replace('\n', ' '))
(OUT / 'NOTICES.md').write_text('\n'.join(md) + '\n')
print(f'licenses: {len(rows)} components, {sum(len(r[4]) for r in rows)} license files'
      + (f'; missing license file for: {", ".join(missing)}' if missing else ''))
