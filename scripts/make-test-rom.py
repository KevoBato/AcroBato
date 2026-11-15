#!/usr/bin/env python3
"""Write a tiny hand-assembled NES ROM that fills the screen with one colour.

Used to test the launch path without needing any real game.
Usage: make-test-rom.py <out.nes> [nes colour index, default 0x12 = blue]
"""
import sys

colour = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x12

code = bytes([
    0x78,                    # C000 SEI
    0xD8,                    # C001 CLD
    0xA2, 0x40,              # C002 LDX #$40
    0x8E, 0x17, 0x40,        # C004 STX $4017   (disable APU frame IRQ)
    0xA2, 0xFF,              # C007 LDX #$FF
    0x9A,                    # C009 TXS
    0xE8,                    # C00A INX         (X = 0)
    0x8E, 0x00, 0x20,        # C00B STX $2000   (NMI off)
    0x8E, 0x01, 0x20,        # C00E STX $2001   (rendering off)
    0x2C, 0x02, 0x20,        # C011 BIT $2002   (wait vblank 1)
    0x10, 0xFB,              # C014 BPL C011
    0x2C, 0x02, 0x20,        # C016 BIT $2002   (wait vblank 2)
    0x10, 0xFB,              # C019 BPL C016
    0xA9, 0x3F,              # C01B LDA #$3F
    0x8D, 0x06, 0x20,        # C01D STA $2006
    0xA9, 0x00,              # C020 LDA #$00
    0x8D, 0x06, 0x20,        # C022 STA $2006   (PPU addr = $3F00, background colour)
    0xA9, colour,            # C025 LDA #colour
    0x8D, 0x07, 0x20,        # C027 STA $2007
    0xA9, 0x00,              # C02A LDA #$00
    0x8D, 0x06, 0x20,        # C02C STA $2006
    0x8D, 0x06, 0x20,        # C02F STA $2006   (PPU addr = 0)
    0xA9, 0x0A,              # C032 LDA #$0A
    0x8D, 0x01, 0x20,        # C034 STA $2001   (show background)
    0x4C, 0x37, 0xC0,        # C037 JMP C037    (loop forever)
    0x40,                    # C03A RTI         (NMI/IRQ handler)
])

prg = bytearray(16 * 1024)
prg[:len(code)] = code
prg[0x3FFA:0x4000] = bytes([0x3A, 0xC0, 0x00, 0xC0, 0x3A, 0xC0])  # NMI, RESET, IRQ vectors
chr_rom = bytes(8 * 1024)
header = b'NES\x1a' + bytes([1, 1, 0, 0]) + bytes(8)  # 1x16K PRG, 1x8K CHR, mapper 0

with open(sys.argv[1], 'wb') as f:
    f.write(header + prg + chr_rom)
