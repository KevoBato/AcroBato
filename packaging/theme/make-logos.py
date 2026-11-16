#!/usr/bin/env python3
"""Make Carbon theme logos for AcroBato's systems that Carbon has no art for.

Usage: make-logos.py <es-theme-carbon dir> <output art/logos dir>
Needs fontTools (pip install fonttools). Run by hand when the logos change; the output SVGs are
committed (packaging/theme/es-theme-carbon/art/logos/), so the build doesn't need fontTools.

The logos are built from Carbon's own art, in its style:
- switch2: Carbon's Switch logo with a "2" in the same red, height and stroke weight
- ps5 / ps5-w: Carbon's PS4 logos with the "4" replaced by a "5" in the same thin style
- arcade systems Pixel Nostalgia's Carbon-PixN has no logo for: the maker's Carbon logo (SEGA,
  ARCADE) with the system name, or a wordmark (Tsunami)
Text is turned into paths (ES's SVG renderer, nanosvg, draws no <text>), in Cabin Bold: the
theme's own font (SIL Open Font License).

Every SVG must render with ES's nanosvg: paths, groups and transforms only (no text, no <use>,
no nested <svg>).
"""
import math
import re
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

CARBON = Path(sys.argv[1])
OUT = Path(sys.argv[2])
LOGOS = CARBON / 'art/logos'
FONT = TTFont(CARBON / 'art/fonts/Cabin-Bold.ttf')
GLYPHS = FONT.getGlyphSet()
CMAP = FONT.getBestCmap()
UPM = FONT['head'].unitsPerEm
CAP = FONT['OS/2'].sCapHeight or 0.7 * UPM


def text(s: str, x: float, baseline: float, cap: float, fill: str, track: float = 0.0) -> tuple[str, float]:
    """<path> of the text s (cap height `cap`, left edge x), and its width."""
    k = cap / CAP
    pen = SVGPathPen(GLYPHS)
    adv = 0.0
    for ch in s:
        g = CMAP[ord(ch)]
        GLYPHS[g].draw(TransformPen(pen, (k, 0, 0, -k, x + adv, baseline)))
        adv += GLYPHS[g].width * k + track * cap
    adv -= track * cap
    return f'<path d="{pen.getCommands()}" fill="{fill}"/>', adv


def text_width(s: str, cap: float, track: float = 0.0) -> float:
    return text(s, 0, 0, cap, '#000', track)[1]


def logo(name: str) -> tuple[str, float, float, float, float, str]:
    """A Carbon logo's inner SVG, its viewBox (x, y, w, h) and root attributes to keep."""
    s = (LOGOS / f'{name}.svg').read_text(encoding='utf-8')
    root = re.search(r'<svg\b[^>]*>', s).group(0)
    inner = s[s.index(root) + len(root):s.rindex('</svg>')]
    vb = re.search(r'viewBox="([^"]+)"', root)
    if vb:
        x, y, w, h = (float(v) for v in vb.group(1).replace(',', ' ').split())
    else:
        x = y = 0.0
        w = float(re.search(r'\bwidth="([\d.]+)', root).group(1))
        h = float(re.search(r'\bheight="([\d.]+)', root).group(1))
    keep = ' '.join(re.findall(r'\b(?:fill|fill-rule|style)="[^"]*"', root))
    return inner, x, y, w, h, keep


def place(name: str, x: float, y: float, height: float) -> tuple[str, float]:
    """A Carbon logo scaled to `height` at (x, y), and its width."""
    inner, vx, vy, vw, vh, keep = logo(name)
    k = height / vh
    return (f'<g transform="translate({x:.2f} {y:.2f}) scale({k:.5f}) translate({-vx:.3f} {-vy:.3f})" {keep}>'
            f'{inner}</g>'), vw * k


def svg(w: float, h: float, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
            f'viewBox="0 0 {w:.2f} {h:.2f}">{body}</svg>\n')


def write(name: str, content: str) -> None:
    (OUT / f'{name}.svg').write_text(content, encoding='utf-8', newline='\n')
    print('wrote', name)


# Layouts. Logos are drawn at height 100 units, text cap heights as below; 10 units of margin.
M = 10


def stacked(name: str, maker: str, label: str, color: str, maker_h: float = 60, cap: float = 34) -> None:
    """Maker logo on top, system name below (as Carbon's segastv and namco22 logos)."""
    _, _, _, vw, vh, _ = logo(maker)
    lw = vw * maker_h / vh
    tw = text_width(label, cap)
    w = max(lw, tw) + 2 * M
    gap = 0.3 * cap
    h = M + maker_h + gap + cap + M
    top, _ = place(maker, (w - lw) / 2, M, maker_h)
    t, _ = text(label, (w - tw) / 2, M + maker_h + gap + cap, cap, color)
    write(name, svg(w, h, top + t))


def beside(name: str, maker: str, label: str, color: str, maker_h: float = 100, cap: float = 62) -> None:
    """Maker logo on the left, the label on the right, bottoms aligned."""
    _, _, _, vw, vh, _ = logo(maker)
    lw = vw * maker_h / vh
    gap = 0.35 * cap
    tw = text_width(label, cap)
    w = M + lw + gap + tw + M
    h = M + maker_h + M
    left, _ = place(maker, M, M, maker_h)
    t, _ = text(label, M + lw + gap, M + maker_h, cap, color)
    write(name, svg(w, h, left + t))


def wordmark(name: str, top: str, bottom: str, color: str, accent: str, cap: float = 64) -> None:
    """Makers Carbon has no logo for: a bold name, with a smaller tracked second line."""
    small = 0.36 * cap
    tw = text_width(top, cap)
    bw = text_width(bottom, small, track=0.35) if bottom else 0
    w = max(tw, bw) + 2 * M
    gap = 0.38 * cap
    h = M + cap + (gap + small if bottom else 0) + M
    body, _ = text(top, (w - tw) / 2, M + cap, cap, color)
    if bottom:
        b, _ = text(bottom, (w - bw) / 2, M + cap + gap + small, small, accent, track=0.35)
        body += b
    write(name, svg(w, h, body))


def switch2() -> None:
    """Carbon's Switch logo + a "2" (stroke 11, the SWITCH letters' box y 59..111)."""
    s = (LOGOS / 'switch.svg').read_text(encoding='utf-8')
    gi = s.rfind('<g style="font-style')  # the TM mark, moved after the 2
    tm, body = s[gi:s.rfind('</svg>')], s[:gi]
    sw = 11
    h = sw / 2
    l, r, t, b = 520 + h, 566 - h, 59 + h, 111 - h
    rad = (r - l) / 2
    cx, cy = l + rad, t + rad
    a = math.radians(35)
    ex, ey = cx + rad * math.cos(a), cy + rad * math.sin(a)
    two = (f'<path d="M{l:.2f} {cy:.2f}A{rad:.2f} {rad:.2f} 0 1 1 {ex:.2f} {ey:.2f}L{l:.2f} {b:.2f}H566" '
           f'style="fill:none;stroke:red;stroke-width:{sw};stroke-linecap:butt;stroke-linejoin:round"/>')
    body = body.replace('width="560"', 'width="620"', 1)
    write('switch2', body + two + f'<g transform="translate(60 0)">{tm}</g></svg>\n')


def ps5() -> None:
    """Carbon's PS4 logos with the 4 (and its counter) replaced by a 5: the PS letters' height
    (y 24.06..88.51) and stroke (6.57), sharp left corners and round right ones like the S."""
    for src, dst in (('ps4', 'ps5'), ('ps4-w', 'ps5-w')):
        s = (LOGOS / f'{src}.svg').read_text(encoding='utf-8')
        four = [p for p in re.findall(r'<path\b[^>]*/>', s) if re.search(r' d="M(382\.08|393\.714) ', p)]
        assert len(four) == 2, f'{src}: the 4 not found'
        color = '#fff' if 'fill="#fff"' in four[0] + four[1] else '#000'
        for p in four:
            s = s.replace(p, '')
        sw = 6.57
        h = sw / 2
        top, bot = 24.06 + h, 88.51 - h
        mid = 52.5
        left, right = 392 + h, 467 - h
        rad = (bot - mid) / 2
        five = (f'<path d="M467 {top:.2f}H{left:.2f}V{mid:.2f}H{right - rad:.2f}'
                f'A{rad:.2f} {rad:.2f} 0 0 1 {right:.2f} {mid + rad:.2f}'
                f'A{rad:.2f} {rad:.2f} 0 0 1 {right - rad:.2f} {bot:.2f}H392" '
                f'style="fill:none;stroke:{color};stroke-width:{sw};stroke-linecap:butt;stroke-linejoin:miter"/>')
        write(dst, s.replace('</svg>', five + '</svg>'))


OUT.mkdir(parents=True, exist_ok=True)
switch2()
ps5()

# Only systems with no official logo in Pixel Nostalgia's Carbon-PixN (the others are its
# logos, see README.md)
SEGA = '#0060a8'
stacked('segashell', 'sega', 'Shell', SEGA)
stacked('apm3', 'sega', 'APM3', SEGA)
beside('arcadepc', 'arcade', 'PC', '#F4B20C', maker_h=60, cap=48)
wordmark('tsunami', 'TSUNAMI', 'VISUAL TECHNOLOGIES', '#0093c9', '#9a9a9a')
