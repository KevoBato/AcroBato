#!/usr/bin/env python3
"""Write a 256x256 placeholder app icon (PNG, no dependencies). Replace with real art."""
import struct
import sys
import zlib

W = H = 256
rows = []
for y in range(H):
    row = bytearray([0])  # filter: none
    for x in range(W):
        dx, dy = x - 128, y - 128
        r2 = dx * dx + dy * dy
        if r2 < 110 * 110:
            # dark disc with a lighter "play" triangle
            inside = 0 <= dx + 30 < 100 and abs(dy) < (100 - (dx + 30)) * 0.6
            row += bytes((240, 120, 40, 255)) if inside else bytes((30, 32, 44, 255))
        else:
            row += bytes((0, 0, 0, 0))
    rows.append(bytes(row))


def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)


png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 6, 0, 0, 0))
png += chunk(b'IDAT', zlib.compress(b''.join(rows), 9)) + chunk(b'IEND', b'')
with open(sys.argv[1], 'wb') as f:
    f.write(png)
