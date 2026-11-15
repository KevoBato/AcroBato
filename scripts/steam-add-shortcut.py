#!/usr/bin/env python3
"""Add a non-Steam game shortcut to Steam's shortcuts.vdf (binary VDF).

Usage: steam-add-shortcut.py <shortcuts.vdf> <name> <exe path> [icon path]
Steam must not be running (it keeps its own copy and overwrites the file).
Existing entries are kept; an entry with the same name and exe is not added twice.
"""
import struct
import sys
import zlib


def parse(data, i=0):
    out = {}
    while True:
        t = data[i]; i += 1
        if t == 0x08:
            return out, i
        end = data.index(b'\x00', i); key = data[i:end].decode('utf-8', 'surrogateescape'); i = end + 1
        if t == 0x00:
            out[key], i = parse(data, i)
        elif t == 0x01:
            end = data.index(b'\x00', i); out[key] = data[i:end].decode('utf-8', 'surrogateescape'); i = end + 1
        elif t == 0x02:
            out[key] = ('int', struct.unpack_from('<i', data, i)[0]); i += 4
        else:
            raise ValueError(f'unsupported VDF type {t:#x} at {i}')


def dump(d):
    b = bytearray()
    for k, v in d.items():
        kb = k.encode('utf-8', 'surrogateescape') + b'\x00'
        if isinstance(v, dict):
            b += b'\x00' + kb + dump(v)
        elif isinstance(v, tuple):
            b += b'\x02' + kb + struct.pack('<i', v[1])
        else:
            b += b'\x01' + kb + v.encode('utf-8', 'surrogateescape') + b'\x00'
    return bytes(b + b'\x08')


def main():
    path, name, exe = sys.argv[1:4]
    icon = sys.argv[4] if len(sys.argv) > 4 else ''
    data = open(path, 'rb').read()
    root, _ = parse(data)
    shortcuts = root.setdefault('shortcuts', {})
    qexe = f'"{exe}"'
    for e in shortcuts.values():
        if e.get('AppName', e.get('appname')) == name and e.get('Exe', e.get('exe')) == qexe:
            print('already present'); return
    appid = (zlib.crc32((qexe + name).encode()) | 0x80000000)
    appid = appid - (1 << 32)  # stored as signed int32
    start = exe.rsplit('/', 1)[0] + '/'
    entry = {'appid': ('int', appid), 'AppName': name, 'Exe': qexe, 'StartDir': f'"{start}"', 'icon': icon,
             'ShortcutPath': '', 'LaunchOptions': '', 'IsHidden': ('int', 0), 'AllowDesktopConfig': ('int', 1),
             'AllowOverlay': ('int', 1), 'OpenVR': ('int', 0), 'Devkit': ('int', 0), 'DevkitGameID': '',
             'DevkitOverrideAppID': ('int', 0), 'LastPlayTime': ('int', 0), 'FlatpakAppID': '', 'tags': {}}
    idx = str(max((int(k) for k in shortcuts if k.isdigit()), default=-1) + 1)
    shortcuts[idx] = entry
    new = dump(root)
    assert parse(new)[0] == root  # round-trips
    open(path, 'wb').write(new)
    print(f'added "{name}" as entry {idx}')


if __name__ == '__main__':
    main()
