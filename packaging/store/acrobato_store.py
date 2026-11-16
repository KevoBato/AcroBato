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

RetroArch cores not bundled in the AppImage (source type "libretro") come from libretro's
official build server (buildbot.libretro.com, Linux x86_64 nightly), checked against the CRC32
its index publishes for each core, into <userdata>/emulators/usr/lib/libretro (ES_LIBRETRO_CORES).
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
    """The download for this emulator from its official releases.
    type "github" (api.github.com) or "gitea" (a Gitea/Forgejo server, src["server"]).
    release "latest" / "tags/<tag>", or "recent": the newest of the last 15 releases (pre-releases
    included) that has a matching file; some projects publish releases without a Linux build."""
    if src['type'] == 'gitea':
        base = f"{src['server']}/api/v1/repos/{src['repo']}/releases"
    else:
        base = f"https://api.github.com/repos/{src['repo']}/releases"
    release = src.get('release', 'latest')
    url = f'{base}?limit=15&per_page=15' if release == 'recent' else f'{base}/{release}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        data = json.load(r)
    for rel in (data if isinstance(data, list) else [data]):
        for a in rel.get('assets', []):
            if re.search(src['asset'], a['name']):
                return {'version': rel.get('tag_name', ''), 'asset': a['name'], 'url': a['browser_download_url'],
                        'size': a.get('size', 0), 'digest': a.get('digest') or ''}
    raise RuntimeError(f"no matching download in {src['repo']} ({release})")


BUILDBOT = 'https://buildbot.libretro.com/nightly/linux/x86_64/latest'


def buildbot_index() -> dict[str, dict]:
    """libretro's build server index: '<date> <crc32> <core>_libretro.so.zip' per line (the CRC32
    is the core's, inside the zip)."""
    with urllib.request.urlopen(urllib.request.Request(f'{BUILDBOT}/.index-extended', headers=UA), timeout=30) as r:
        lines = r.read().decode(errors='replace').splitlines()
    out = {}
    for line in lines:
        parts = line.split()
        if len(parts) == 3 and parts[2].endswith('_libretro.so.zip'):
            out[parts[2].removesuffix('_libretro.so.zip')] = {'version': parts[0], 'crc32': parts[1].lower()}
    return out


def refresh() -> None:
    cache = {}
    index = None
    for e in catalog():
        try:
            if e['source']['type'] in ('github', 'gitea'):
                cache[e['id']] = github_release(e['source'])
            elif e['source']['type'] == 'libretro':
                index = index if index is not None else buildbot_index()
                if e['source']['core'] in index:
                    cache[e['id']] = index[e['source']['core']]
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
                         # ES makes one tab per repository (sorted by name): emulators, then cores
                         ('repository', 'RetroArch Cores' if e['source']['type'] == 'libretro' else 'Emulators'),
                         ('arch', 'x86_64'),
                         ('available_version', info.get('version', '')),
                         ('download_size', str(info.get('size', 0) // 1024)),  # ES expects KB
                         ('url', f"{e['source'].get('server', 'https://github.com')}/{e['source']['repo']}"
                          if 'repo' in e['source'] else
                          'https://buildbot.libretro.com' if e['source']['type'] == 'libretro' else ''),
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
    elif digest != 'checked-later':
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
        if e['source'].get('archive') in ('tar.gz', 'zip'):  # a whole program folder (e.g. KytyPS5)
            import tarfile
            say('Extracting')
            if e['source']['archive'] == 'zip':
                with zipfile.ZipFile(dl) as z:
                    for m in z.infolist():  # (zip has no tarfile-style 'data' filter: same checks)
                        if m.filename.startswith('/') or '..' in Path(m.filename).parts:
                            raise RuntimeError(f'unsafe path in the archive: {m.filename}')
                    z.extractall(Path(tmp) / 'x')
            else:
                with tarfile.open(dl) as t:
                    t.extractall(Path(tmp) / 'x', filter='data')
            exes = [p for p in (Path(tmp) / 'x').rglob(e['source']['exe']) if p.is_file()]
            if not exes:
                raise RuntimeError(f"archive does not contain {e['source']['exe']}")
            if app_dir.exists():
                shutil.rmtree(app_dir)
            shutil.move(exes[0].parent, app_dir)
            exe = app_dir / exes[0].name
            exe.chmod(0o755)
            rel = os.path.relpath(exe, target(e).parent)
            # run from its own folder: some programs look for their files next to themselves
            appimage_env = ('unset APPDIR APPIMAGE ARGV0 OWD\n'
                            'if ! command -v fusermount3 >/dev/null 2>&1 && ! command -v fusermount >/dev/null 2>&1; then\n'
                            '  export APPIMAGE_EXTRACT_AND_RUN=1\n'
                            'fi\n') if exe.name.endswith('.AppImage') else ''
            write_launcher(target(e), (
                f'EXE="$(dirname "$(readlink -f "$0")")/{rel}"\n' + appimage_env +
                'cd "$(dirname "$EXE")" && exec "$EXE" "$@"\n'))
            return info['version']
        if e['source'].get('archive') == 'appimage':
            # an AppImage used unpacked (its program run directly, e.g. a 32-bit one whose
            # launcher sets library paths, like linuxloader): "exe" inside it, "env" as its
            # AppRun sets ($ROOT = the unpacked AppImage)
            say('Extracting')
            dl.chmod(0o755)
            subprocess.run([str(dl), '--appimage-extract'], cwd=tmp, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if app_dir.exists():
                shutil.rmtree(app_dir)
            shutil.move(Path(tmp) / 'squashfs-root', app_dir)
            exe = app_dir / e['source']['exe']
            if not exe.is_file():
                raise RuntimeError(f"the AppImage does not contain {e['source']['exe']}")
            rel = os.path.relpath(app_dir, target(e).parent)
            env = ''.join(f'export {k}="{v}"\n' for k, v in e['source'].get('env', {}).items())
            write_launcher(target(e), (
                f'ROOT="$(dirname "$(readlink -f "$0")")/{rel}"\n' + env +
                f'exec "$ROOT/{e["source"]["exe"]}" "$@"\n'))
            return info['version']
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
        # data Batocera's launcher reads from the emulator's install (e.g. RPCS3's icons), which
        # an AppImage keeps inside: "extract_files" (paths in the AppImage) are copied out to
        # <app>/extracted/<path>, for "files" to place
        if wanted := e['source'].get('extract_files'):
            say('Extracting data files')
            x = Path(tmp) / 'appimage'
            x.mkdir()
            subprocess.run([str(appimage), '--appimage-extract'], cwd=x, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            root = next(d for d in x.iterdir() if d.is_dir())  # squashfs-root (or AppDir)
            for w in wanted:
                if not (root / w).exists():
                    raise RuntimeError(f'the AppImage does not contain {w}')
                put(root / w, app_dir / 'extracted' / w)
    # Runs the AppImage directly when FUSE is available, otherwise extract-and-run.
    # relative to the launcher, so the data folder can be moved
    rel = os.path.relpath(appimage, target(e).parent)
    write_launcher(target(e), (
        f'APP="$(dirname "$(readlink -f "$0")")/{rel}"\n'
        'unset APPDIR APPIMAGE ARGV0 OWD\n'
        '# updates come from the Content Downloader; some AppImages otherwise ask on first start\n'
        'export DISABLE_AUTO_UPDATES=1\n'
        'if ! command -v fusermount3 >/dev/null 2>&1 && ! command -v fusermount >/dev/null 2>&1; then\n'
        '  export APPIMAGE_EXTRACT_AND_RUN=1\n'
        'fi\n'
        'exec "$APP" "$@"\n'))
    return info['version']


def install_libretro(e: dict) -> str:
    """A RetroArch core from libretro's build server, CRC32-checked, at its libretro path."""
    import zlib
    core = e['source']['core']
    info = buildbot_index().get(core)
    if not info:
        raise RuntimeError(f'{core} is not on the libretro build server')
    say(f"{e['name']} ({info['version']} build)")
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        dl = Path(tmp) / f'{core}_libretro.so.zip'
        download(f'{BUILDBOT}/{core}_libretro.so.zip', dl, e['name'], 0, 'checked-later')  # CRC32 below
        say('Extracting')
        with zipfile.ZipFile(dl) as z:
            z.extract(f'{core}_libretro.so', tmp)
        so = Path(tmp) / f'{core}_libretro.so'
        crc = 0
        with open(so, 'rb') as f:
            while chunk := f.read(1 << 20):
                crc = zlib.crc32(chunk, crc)
        if f'{crc:08x}' != info['crc32']:
            raise RuntimeError('checksum mismatch: download was corrupted or altered, nothing installed')
        say('Checksum verified')
        target(e).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(so, target(e))
    return info['version']


def usr_path(p: str) -> Path:
    """A catalog install path: /usr/... in the downloaded emulators' tree, /userdata/... in the
    user's data folder (e.g. a BIOS file Batocera ships as a default: /userdata/bios/...)."""
    if p.startswith('/userdata/'):
        return USERDATA / p.removeprefix('/userdata/')
    return USR / p.removeprefix('/usr/')


def put(src: Path, dest: Path) -> None:
    """Copy a file or folder to dest, replacing what's there."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_dir() and not dest.is_symlink():
        shutil.rmtree(dest)
    elif dest.exists() or dest.is_symlink():
        dest.unlink()
    if src.is_dir():
        shutil.copytree(src, dest, symlinks=True)
    else:
        shutil.copy2(src, dest)


def install_files(e: dict) -> None:
    """Data files from the emulator's own download, where Batocera's launcher expects them
    ("files": [{"from": <path in the unpacked download>, "install": "/usr/share/..."}]), and
    empty folders it expects ("mkdir": ["/usr/share/..."])."""
    for d in e.get('mkdir', []):
        usr_path(d).mkdir(parents=True, exist_ok=True)
    # other names Batocera's launcher runs the same program by ("aliases": ["/usr/bin/..."])
    for a in e.get('aliases', []):
        link = usr_path(a)
        link.parent.mkdir(parents=True, exist_ok=True)
        link.unlink(missing_ok=True)
        link.symlink_to(os.path.relpath(target(e), link.parent))
    for f in e.get('files', []):
        src = APPS / e['id'] / f['from']
        if not src.exists():
            raise RuntimeError(f"the download has no {f['from']}")
        dest = usr_path(f['install'])
        if f['install'].startswith('/userdata/') and dest.exists():
            continue  # the user's own file (a BIOS they put there) stays
        put(src, dest)


def install_extras(e: dict) -> None:
    """Files an emulator needs besides its own download (MAME's plugins, Batocera's data for the
    emulator...), pinned by SHA-256 in the catalog. With "extract" ({path in the archive:
    path under "install"}), the download is a .tar.* archive and those parts of it are used;
    "strip" drops leading folders of the archive's paths (1 for GitHub source archives)."""
    import tarfile
    for x in e.get('extras', []):
        dest = usr_path(x['install'])
        if 'github' in x:  # a file of a GitHub release, checked against GitHub's own SHA-256
            info = github_release({'type': 'github', **x['github']})
            url, digest = info['url'], info['digest']
            if not digest.startswith('sha256:'):
                raise RuntimeError(f"no checksum published for {info['asset']}")
        else:
            url, digest = x['url'], f"sha256:{x['sha256']}"
        if 'extract' not in x:
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + '.part')
            download(url, tmp, dest.name, 0, digest)
            tmp.replace(dest)
            continue
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            arc = Path(tmp) / 'archive'
            download(url, arc, url.rsplit('/', 1)[-1], 0, digest)
            out = Path(tmp) / 'x'
            with tarfile.open(arc) as t:
                t.extractall(out, filter='data')
            root = out
            for _ in range(x.get('strip', 0)):
                (only,) = list(root.iterdir())
                root = only
            for src, rel in x['extract'].items():
                s = root / src if src not in ('', '.') else root
                if not s.exists():
                    raise RuntimeError(f'{src} is not in {x["url"]}')
                d = dest / rel if rel not in ('', '.') else dest
                if s.is_dir() and d == dest:
                    dest.mkdir(parents=True, exist_ok=True)
                    for item in s.iterdir():
                        put(item, dest / item.name)
                else:
                    put(s, d)


def installed_paths(e: dict) -> list[Path]:
    """Everything the install put outside the emulator's own folder (removed with it)."""
    # (files put in the user's data folder, e.g. BIOS files, are left there)
    paths = ([usr_path(f['install']) for f in e.get('files', []) if not f['install'].startswith('/userdata/')]
             + [usr_path(d) for d in e.get('mkdir', [])]
             + [usr_path(a) for a in e.get('aliases', [])])
    for x in e.get('extras', []):
        if 'extract' not in x:
            paths.append(usr_path(x['install']))
        else:
            paths += [usr_path(x['install']) / rel for rel in x['extract'].values() if rel not in ('', '.')]
            if any(rel in ('', '.') for rel in x['extract'].values()):
                paths.append(usr_path(x['install']))
    return paths


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
    kind = e['source']['type']
    version = (install_flatpak(e) if kind == 'flatpak' else install_libretro(e) if kind == 'libretro'
               else install_github(e))
    install_files(e)
    install_extras(e)
    state = load(STATE, {})
    state[e['id']] = {'version': version, 'installed': time.strftime('%Y-%m-%d')}
    save(STATE, state)
    for f in window_entries(e):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(e['id'] + '\n')
    say(f"{e['name']} installed")


def window_entries(e: dict) -> list[Path]:
    """'Open <emulator>.emuapp' entries in the game lists of the systems it runs: they open
    the emulator's own window (firmware, keys, settings). See acrobato_emulators."""
    return [USERDATA / 'roms' / s / f"Open {e['name']}.emuapp" for s in e.get('systems', [])]


def cmd_remove(name: str) -> None:
    e = find(name)
    for f in window_entries(e):
        f.unlink(missing_ok=True)
    target(e).unlink(missing_ok=True)
    for p in installed_paths(e):
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p, ignore_errors=True)
        else:
            p.unlink(missing_ok=True)
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
