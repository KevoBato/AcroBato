#!/usr/bin/env python3
"""Trim a Carbon-style theme's per-system art to the systems AcroBato has.

Usage: prune-theme.py <theme dir> <es_systems.cfg>

The theme looks art up by system name (${system.theme}) in art/logos, art/background,
art/consoles, art/controllers and their region folders (us/, jp/, br/), with -w (white) and
-<lang> variants. Carbon-PixN has art for hundreds of systems; AcroBato has about 90.
Kept: the systems' and their groups' names (es_systems.cfg <theme>, <group>), "default", any
name the theme's XML spells out, and collections/ (ES collections use those).
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

THEME, SYSTEMS = Path(sys.argv[1]), Path(sys.argv[2])
ART_DIRS = ('logos', 'background', 'consoles', 'controllers')
REGIONS = ('us', 'jp', 'br')

root = ET.parse(SYSTEMS).getroot()
keep = {'default'}
for s in root.findall('system'):
    for tag in ('theme', 'name', 'group'):
        if v := s.findtext(tag):
            keep.add(v.strip())
# names the theme's XML uses literally (art/logos/<name>.svg ...)
for xml in THEME.rglob('*.xml'):
    for m in re.finditer(r'art/(?:%s)/(?:(?:%s)/)?([^/$<"{}]+?)\.(?:svg|png|jpg|webp)' % ('|'.join(ART_DIRS), '|'.join(REGIONS)),
                         xml.read_text(errors='replace')):
        keep.add(m.group(1))

SUFFIX = re.compile(r'(?:-w)?(?:-[a-z]{2}(?:_[A-Za-z]{2})?)?$')


def wanted(stem: str) -> bool:
    return stem in keep or SUFFIX.sub('', stem) in keep


removed = size = 0
for d in ART_DIRS:
    for folder in [THEME / 'art' / d] + [THEME / 'art' / d / r for r in REGIONS]:
        if not folder.is_dir():
            continue
        for f in folder.iterdir():
            if f.is_file() and not wanted(f.stem):
                size += f.stat().st_size
                f.unlink()
                removed += 1
print(f'theme trimmed: {removed} files, {size / 1048576:.0f} MB removed ({len(keep)} names kept)')
