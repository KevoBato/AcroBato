"""Emulator downloader behind EmulationStation's "Content Downloader".

ES calls `batocera-store <command>` (see ApiSystem.cpp):
    list              XML <packages> on stdout
    install "NAME"    progress lines on stdout, exit 0 on success
    remove "NAME"
    update | refresh  re-read release info from upstream
    clean-all         nothing to do

Emulators come from each project's official GitHub releases (checked against
the SHA-256 digest GitHub publishes, when there is one) or from Flathub. They
are stored under <userdata>/emulators and exposed at the path Batocera's
launcher expects, e.g. /usr/bin/duckstation-qt -> <userdata>/emulators/usr/bin/duckstation-qt
(see relocate() / ES_USR / ES_BIN).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

USERDATA = Path(os.environ.get('ES_USERDATA', Path.home() / '.local/share/acrobato'))
SHARE = Path(os.environ.get('ES_SHARE', Path(__file__).resolve().parent.parent))
CATALOG = SHARE / 'acrobato' / 'emulators.json'
ROOT = USERDATA / 'emulators'
APPS = ROOT / 'apps'           # downloaded files, one folder per emulator
USR = ROOT / 'usr'             # what Batocera's launcher sees as /usr/...
STATE = ROOT / 'installed.json'
CACHE = ROOT / '.cache' / 'releases.json'
UA = {'User-Agent': 'emulator-downloader', 'Accept': 'application/vnd.github+json'}


def say(msg: str) -> None:
    print(msg, flush=True)


def load(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def catalog() -> list[dict]:
    return load(CATALOG, {}).get('emulators', [])


def find(name: str) -> dict:
    for e in catalog():
        if name.lower() in (e['id'].lower(), e['name'].lower()):
            return e
    sys.exit(f'unknown emulator: {name}')


def github_release(src: dict) -> dict:
    url = f"https://api.github.com/repos/{src['repo']}/releases/{src['release']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        rel = json.load(r)
    for a in rel.get('assets', []):
        if re.search(src['asset'], a['name']):
            return {'version': rel.get('tag_name', ''), 'asset': a['name'], 'url': a['browser_download_url'],
                    'size': a.get('size', 0), 'digest': a.get('digest') or ''}
    raise RuntimeError(f"no matching download in {src['repo']} {rel.get('tag_name')}")


def refresh() -> None:
    cache = {}
    for e in catalog():
        if e['source']['type'] == 'github':
            try:
                cache[e['id']] = github_release(e['source'])
            except Exception as ex:  # keep going; one project being down shouldn't hide the rest
                print(f"{e['name']}: {ex}", file=sys.stderr)
    cache['_time'] = time.time()
    save(CACHE, cache)


def flatpak_installed(ref: str) -> bool:
    return subprocess.run(['flatpak', 'info', '--user', ref], capture_output=True).returncode == 0 or \
           subprocess.run(['flatpak', 'info', ref], capture_output=True).returncode == 0


def cmd_list() -> None:
    state = load(STATE, {})
    cache = load(CACHE, {})
    if not cache or time.time() - cache.get('_time', 0) > 6 * 3600:
        try:
            refresh()
            cache = load(CACHE, {})
        except Exception:
            pass
    out = ['<?xml version="1.0"?>', '<packages>']
    for e in catalog():
        info = cache.get(e['id'], {})
        installed = e['id'] in state and target(e).exists()
        # ES shows the description as the headline and the name in small print
        desc = f"{e['name']} – {e['description']}"
        if installed:
            desc += f" (installed: {state[e['id']].get('version', '?')})"
        out.append('  <package>')
        for tag, val in (('name', e['name']), ('description', desc), ('group', e.get('group', 'EMULATORS')),
                         ('repository', 'Emulators'), ('arch', 'x86_64'),
                         ('available_version', info.get('version', '')),
                         ('download_size', str(info.get('size', 0) // 1024)),  # ES expects KB
                         ('url', f"https://github.com/{e['source']['repo']}" if 'repo' in e['source'] else ''),
                         ('status', 'installed' if installed else '')):
            out.append(f'    <{tag}>{escape(str(val))}</{tag}>')
        out.append('  </package>')
    out.append('</packages>')
    print('\n'.join(out))


def target(e: dict) -> Path:
    return USR / e['install'].removeprefix('/usr/')


def download(url: str, dest: Path, label: str, size: int, digest: str) -> None:
    h = hashlib.sha256()
    done, last = 0, -1
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA['User-Agent']}), timeout=60) as r, \
         open(dest, 'wb') as f:
        total = size or int(r.headers.get('Content-Length') or 0)
        while chunk := r.read(1 << 20):
            f.write(chunk)
            h.update(chunk)
            done += len(chunk)
            pct = done * 100 // total if total else 0
            if pct != last and pct % 5 == 0:
                say(f'Downloading {label} >>> {pct}%')
                last = pct
    if digest.startswith('sha256:'):
        if h.hexdigest() != digest.split(':', 1)[1]:
            dest.unlink(missing_ok=True)
            raise RuntimeError('checksum mismatch: download was corrupted or altered, nothing installed')
        say('Checksum verified')
    else:
        say('No checksum published upstream for this file (HTTPS download only)')


def write_launcher(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('#!/bin/sh\n' + body)
    path.chmod(0o755)


def install_github(e: dict) -> str:
    info = github_release(e['source'])
    say(f"{e['name']} {info['version']}: {info['asset']}")
    app_dir = APPS / e['id']
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        dl = Path(tmp) / info['asset']
        download(info['url'], dl, e['name'], info['size'], info['digest'])
        if 'member' in e['source']:  # AppImage inside a zip
            with zipfile.ZipFile(dl) as z:
                names = [n for n in z.namelist() if re.search(e['source']['member'], n)]
                if not names:
                    raise RuntimeError('archive does not contain the expected AppImage')
                say('Extracting')
                z.extract(names[0], tmp)
                dl = Path(tmp) / names[0]
        if app_dir.exists():
            shutil.rmtree(app_dir)
        app_dir.mkdir(parents=True)
        appimage = app_dir / f"{e['id']}.AppImage"
        shutil.move(dl, appimage)
        appimage.chmod(0o755)
    # Runs the AppImage directly when FUSE is available, otherwise extract-and-run.
    # relative to the launcher, so the data folder can be moved
    rel = os.path.relpath(appimage, target(e).parent)
    write_launcher(target(e), (
        f'APP="$(dirname "$(readlink -f "$0")")/{rel}"\n'
        'unset APPDIR APPIMAGE ARGV0 OWD\n'
        'if ! command -v fusermount3 >/dev/null 2>&1 && ! command -v fusermount >/dev/null 2>&1; then\n'
        '  export APPIMAGE_EXTRACT_AND_RUN=1\n'
        'fi\n'
        'exec "$APP" "$@"\n'))
    return info['version']


def install_flatpak(e: dict) -> str:
    src = e['source']
    if not shutil.which('flatpak'):
        raise RuntimeError('Flatpak is not available on this system')
    if not flatpak_installed(src['ref']):
        say(f"Installing {e['name']} from {src['remote']} (this can take a while)")
        subprocess.run(['flatpak', 'remote-add', '--user', '--if-not-exists', 'flathub',
                        'https://dl.flathub.org/repo/flathub.flatpakrepo'], check=True)
        p = subprocess.Popen(['flatpak', 'install', '--user', '-y', '--noninteractive', src['remote'], src['ref']],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in p.stdout:
            line = line.strip()
            if line:
                say(f"{e['name']}: {line[-80:]}")
        if p.wait():
            raise RuntimeError('flatpak install failed')
    # give the sandbox access to the games/saves folder
    write_launcher(target(e), flatpak_launcher(src['ref']))


def flatpak_launcher(ref: str) -> str:
    # batocera-launch points XDG_CONFIG_HOME/XDG_DATA_HOME at AcroBato's folders so the
    # emulator uses Batocera's generated settings. flatpak itself must see the user's real
    # folders (that's where user-installed apps are found); the AcroBato ones are passed into
    # the sandbox, which can reach the AcroBato data folder.
    return (
        'CFG="${XDG_CONFIG_HOME:-$HOME/.config}"; DATA="${XDG_DATA_HOME:-$HOME/.local/share}"\n'
        'CACHE="${XDG_CACHE_HOME:-$HOME/.cache}"\n'
        'exec env XDG_CONFIG_HOME="$HOME/.config" XDG_DATA_HOME="$HOME/.local/share" XDG_CACHE_HOME="$HOME/.cache" \\\n'
        '  flatpak run --filesystem="${ES_USERDATA:-$HOME/.local/share/acrobato}" \\\n'
        '  --env=XDG_CONFIG_HOME="$CFG" --env=XDG_DATA_HOME="$DATA" --env=XDG_CACHE_HOME="$CACHE" \\\n'
        f'  {ref} "$@"\n')
    return 'flathub'


def cmd_install(name: str) -> None:
    e = find(name)
    ROOT.mkdir(parents=True, exist_ok=True)
    version = install_flatpak(e) if e['source']['type'] == 'flatpak' else install_github(e)
    state = load(STATE, {})
    state[e['id']] = {'version': version, 'installed': time.strftime('%Y-%m-%d')}
    save(STATE, state)
    say(f"{e['name']} installed")


def cmd_remove(name: str) -> None:
    e = find(name)
    target(e).unlink(missing_ok=True)
    shutil.rmtree(APPS / e['id'], ignore_errors=True)
    if e['source']['type'] == 'flatpak' and shutil.which('flatpak'):
        say(f"Removing {e['name']} (Flatpak)")
        subprocess.run(['flatpak', 'uninstall', '--user', '-y', '--noninteractive', e['source']['ref']])
    state = load(STATE, {})
    state.pop(e['id'], None)
    save(STATE, state)
    say(f"{e['name']} removed")


def main() -> int:
    args = sys.argv[1:]
    cmd = args[0] if args else 'list'
    try:
        if cmd == 'list':
            cmd_list()
        elif cmd in ('update', 'refresh'):
            refresh()
        elif cmd == 'clean-all':
            pass
        elif cmd == 'install' and len(args) > 1:
            cmd_install(args[1])
        elif cmd == 'remove' and len(args) > 1:
            cmd_remove(args[1])
        else:
            print(f'usage: batocera-store list|update|refresh|clean-all|install NAME|remove NAME', file=sys.stderr)
            return 2
    except Exception as ex:
        say(f'Error: {ex}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
