#!/usr/bin/env python3
"""Copy only the RetroArch shader presets Batocera's shader sets use (plus every
file they depend on) from libretro's slang-shaders and glsl-shaders packs.

Both packs install into the same folder on Batocera (/usr/share/batocera/shaders),
so the output mirrors that. Also mirrors the extra steps in Batocera's
slang-shaders.mk (presets that moved upstream, Batocera's own handheld .slangp).
Mega Bezel presets are skipped (very large); they can be a download later.

Usage: stage-shaders.py <slang-shaders> <glsl-shaders> <batocera-shaders/configs> <out dir> [<batocera slang presets dir>]
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path, PurePosixPath

SKIP = ('bezel/Mega_Bezel',)
# Batocera's configs use the old locations of these slang presets (slang-shaders.mk)
SLANG_MOVED = {
    'interpolation/sharp-bilinear-simple.slangp': 'pixel-art-scaling/sharp-bilinear-simple.slangp',
    'scalehq/2xScaleHQ.slangp': 'edge-smoothing/scalehq/2xScaleHQ.slangp',
}
FILE_VALUE = re.compile(r'^\s*[\w.-]+\s*=\s*"?([^"\s]+\.(?:slang|glsl|slangp|glslp|png|jpg|jpeg|bmp|tga|inc|h|params))"?\s*$', re.I)
REFERENCE = re.compile(r'^\s*#reference\s+"([^"]+)"')
INCLUDE = re.compile(r'^\s*#include\s+"([^"]+)"')
BINARY = ('.png', '.jpg', '.jpeg', '.bmp', '.tga')


def norm(p: PurePosixPath) -> PurePosixPath | None:
    parts: list[str] = []
    for part in p.parts:
        if part == '..':
            if not parts:
                return None
            parts.pop()
        elif part != '.':
            parts.append(part)
    return PurePosixPath(*parts)


def copy_as(src_root: Path, src_rel: PurePosixPath, dest_rel: PurePosixPath, out: Path, seen: set) -> bool:
    """Copy src_root/src_rel to out/dest_rel, then every file it references.
    References resolve relative to the source file and land relative to the destination."""
    if (src_rel, dest_rel) in seen:
        return True
    seen.add((src_rel, dest_rel))
    src = src_root / src_rel
    if not src.is_file():
        return False
    dest = out / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    if src.suffix.lower() in BINARY:
        return True
    for line in src.read_text(errors='replace').splitlines():
        m = FILE_VALUE.match(line) or REFERENCE.match(line) or INCLUDE.match(line)
        if not m:
            continue
        s = norm(src_rel.parent / m.group(1))
        d = norm(dest_rel.parent / m.group(1))
        if s is not None and d is not None:
            copy_as(src_root, s, d, out, seen)
    return True


def presets_used(configs: Path) -> set[str]:
    names = set()
    for yml in configs.rglob('rendering-defaults*.yml'):
        for line in yml.read_text().splitlines():
            m = re.match(r'\s*shader:\s*(\S+)', line)
            if m and not m.group(1).startswith(SKIP):
                names.add(m.group(1))
    return names


def main() -> int:
    slang, glsl, configs, out = (Path(p) for p in sys.argv[1:5])
    bato_presets = Path(sys.argv[5]) if len(sys.argv) > 5 else None
    seen: set = set()
    found, absent = [], []
    for name in sorted(presets_used(configs)):
        for root, ext in ((slang, '.slangp'), (glsl, '.glslp')):
            dest = PurePosixPath(name + ext)
            src = PurePosixPath(SLANG_MOVED.get(str(dest), str(dest)))
            (found if copy_as(root, src, dest, out, seen) else absent).append(str(dest))
    # Batocera's own slang versions of glsl-only handheld presets (refs are relative to handheld/)
    if bato_presets and (bato_presets / 'handheld').is_dir():
        for p in sorted((bato_presets / 'handheld').glob('*.slangp')):
            shutil.copy2(p, out / 'handheld' / p.name)
            for line in p.read_text().splitlines():
                m = FILE_VALUE.match(line)
                if m:
                    s = norm(PurePosixPath('handheld') / m.group(1))
                    if s is not None:
                        copy_as(slang, s, s, out, seen)
            found.append(f'handheld/{p.name}')
    # Batocera adds a curvature variant of crt-pi (glsl-shaders.mk)
    pi = out / 'crt/shaders/crt-pi.glsl'
    if pi.is_file():
        (out / 'crt/shaders/crt-pi-curvature.glsl').write_text(
            pi.read_text().replace('//#define CURVATURE', '#define CURVATURE'))
    still_missing = [a for a in absent if not (out / a).is_file()]
    files = sum(1 for p in out.rglob('*') if p.is_file())
    print(f'{len(found)} presets copied, {files} files; not available: {still_missing or "none"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
