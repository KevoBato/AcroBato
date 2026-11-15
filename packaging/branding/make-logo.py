#!/usr/bin/env python3
"""Turn the AcroBato source logo into transparent PNGs.

- removes the cream background (flood fill from the edges; the logo's dark
  outlines stop the fill), plus the faint glow and loose sparkles
- removes the tagline under the wordmark
Outputs: logo.png (controllers + wordmark), icon.png (controllers, square 512).
Usage: make-logo.py <source image> <out dir>   (needs Pillow)
"""
import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
im = Image.open(src).convert('RGB')
W, H = im.size
px = im.load()

# background colour: median of the border
border = [px[x, y] for x in range(0, W, 7) for y in (0, H - 1)] + [px[x, y] for y in range(0, H, 7) for x in (0, W - 1)]
bg = tuple(sorted(c[i] for c in border)[len(border) // 2] for i in range(3))


def dist(c):
    return max(abs(c[0] - bg[0]), abs(c[1] - bg[1]), abs(c[2] - bg[2]))


TOL = 46  # glow, swoosh shapes and sparkles are within this of the cream; outlines are far darker
bgmask = bytearray(W * H)
q = deque((x, y) for x in range(W) for y in (0, H - 1))
q.extend((x, y) for y in range(H) for x in (0, W - 1))
while q:
    x, y = q.popleft()
    i = y * W + x
    if bgmask[i] or dist(px[x, y]) > TOL:
        continue
    bgmask[i] = 1
    if x > 0: q.append((x - 1, y))
    if x < W - 1: q.append((x + 1, y))
    if y > 0: q.append((x, y - 1))
    if y < H - 1: q.append((x, y + 1))

# enclosed background (letter counters, the cable loop): warm cream not reached by the
# edge fill. The controllers' light plastic is bluish-grey, so only warm, near-cream
# pixels count (R noticeably above B).
for i in range(W * H):
    if not bgmask[i]:
        c = px[i % W, i // W]
        if dist(c) <= 24 and c[0] - c[2] >= 4 and sum(c) >= 690:
            bgmask[i] = 1

# keep only large foreground pieces (drops sparkles, dust, glow fragments)
comp = [0] * (W * H)
sizes, boxes = {}, {}
cid = 0
for start in range(W * H):
    if bgmask[start] or comp[start]:
        continue
    cid += 1
    q = deque([start]); comp[start] = cid; n = 0
    x0 = y0 = 10**9; x1 = y1 = -1
    while q:
        i = q.popleft(); n += 1
        x, y = i % W, i // W
        x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
        for j in ((i - 1) if x > 0 else -1, (i + 1) if x < W - 1 else -1, i - W, i + W):
            if 0 <= j < W * H and not bgmask[j] and not comp[j]:
                comp[j] = cid; q.append(j)
    sizes[cid] = n; boxes[cid] = (x0, y0, x1, y1)

biggest = max(sizes.values())
MIN_FRAC = 0.004
keep = {c for c, n in sizes.items() if n >= biggest * MIN_FRAC}
print('largest pieces:', sorted(((n, boxes[c]) for c, n in sizes.items() if c in keep), reverse=True)[:8])
# drop the floor shadow and dust under the controllers: wide/flat or small pieces between
# the controllers and the wordmark that are mostly light (not outlined artwork)
def mostly_light(c):
    x0, y0, x1, y1 = boxes[c]
    tot = dark = 0
    for y in range(y0, y1 + 1, 2):
        for x in range(x0, x1 + 1, 2):
            if comp[y * W + x] == c:
                tot += 1
                if sum(px[x, y]) < 330:
                    dark += 1
    return tot and dark / tot < 0.08
keep = {c for c in keep if not mostly_light(c)}

# the tagline sits below the wordmark: find the wordmark's bottom (largest pieces in the lower half)
lower = [boxes[c] for c in keep if boxes[c][1] > H * 0.6]
word_bottom = max(b[3] for b in lower if b[3] - b[1] > H * 0.05) if lower else H
keep = {c for c in keep if boxes[c][1] <= word_bottom}

alpha = Image.new('L', (W, H), 0)
ap = alpha.load()
for i in range(W * H):
    if comp[i] in keep:
        ap[i % W, i // W] = 255
# soften the cut edge by one pixel
alpha = alpha.filter(ImageFilter.GaussianBlur(0.7))
logo = im.convert('RGBA'); logo.putalpha(alpha)
logo = logo.crop(logo.getbbox())
pad = 16
canvas = Image.new('RGBA', (logo.width + 2 * pad, logo.height + 2 * pad), (0, 0, 0, 0))
canvas.paste(logo, (pad, pad))
canvas.save(out / 'logo.png')

# icon: just the controllers (everything above the wordmark), squared
word_top = min((b[1] for b in lower if b[3] - b[1] > H * 0.05), default=H)
top = Image.new('RGBA', (W, H), (0, 0, 0, 0))
full = im.convert('RGBA'); full.putalpha(alpha)
top.paste(full.crop((0, 0, W, word_top - 8)), (0, 0))
top = top.crop(top.getbbox())
side = max(top.size) + 24
icon = Image.new('RGBA', (side, side), (0, 0, 0, 0))
icon.paste(top, ((side - top.width) // 2, (side - top.height) // 2))
icon.resize((512, 512), Image.LANCZOS).save(out / 'icon.png')
# splash images in the shapes ES and the theme expect:
#  splash-1080.png  full screen (replaces ES resources/logo.png, shown when a game launches)
#  splash-square.png  square, transparent (for the splash .svg files)
def framed(size, fill, frac, y_center=0.5):
    w, h = size
    s = min(w * frac / canvas.width, h * frac / canvas.height)
    lg = canvas.resize((round(canvas.width * s), round(canvas.height * s)), Image.LANCZOS)
    out_im = Image.new('RGBA', size, fill)
    out_im.alpha_composite(lg, ((w - lg.width) // 2, round(h * y_center - lg.height / 2)))
    return out_im

framed((1920, 1080), (0, 0, 0, 255), 0.55, 0.42).convert('RGB').save(out / 'splash-1080.png')
framed((960, 960), (0, 0, 0, 0), 0.8).save(out / 'splash-square.png')
print(f'bg={bg} pieces kept={len(keep)}/{len(sizes)} wordmark bottom={word_bottom} logo={canvas.size}')
