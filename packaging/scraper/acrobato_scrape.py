"""Game artwork/metadata lookups for EmulationStation's scrapers (AcroBato).

ES runs:  acrobato-scrape <source> --system <es system> --file <rom path> [--name <name>] [--manual]
and reads a JSON list of results on stdout:
  [{"name", "desc", "releasedate": "YYYYMMDD", "developer", "publisher", "genre",
    "players", "rating": "0.0-1.0", "media": {"box2d", "box3d", "boxback", "screenshot",
    "titleshot", "fanart", "logo", "cartridge": url}}]

Sources (none needs an account or key):
  launchbox  LaunchBox Games Database: metadata + images. The public database
             (gamesdb.launchbox-app.com/Metadata.zip, ~110 MB) is downloaded on first use and
             turned into a local SQLite index, refreshed after 60 days.
  libretro   libretro-thumbnails (thumbnails.libretro.com): box art, title screens and
             in-game screenshots, matched by ROM file name (No-Intro/Redump naming).
  gametdb    GameTDB (art.gametdb.com): covers, 3D covers and disc art for GameCube/Wii
             (by disc ID read from the image) and DS (by game code).
"""
from __future__ import annotations

import argparse
import difflib
import fcntl
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

UA = {'User-Agent': 'AcroBato-scraper/1.0'}
USERDATA = Path(os.environ.get('ES_USERDATA', Path.home() / '.local/share/acrobato'))
CACHE = USERDATA / 'system' / 'cache' / 'scrapers'

# ES system name -> (libretro thumbnails folders, LaunchBox platforms)
SYSTEMS: dict[str, tuple[list[str], list[str]]] = {
    '3do': (['The 3DO Company - 3DO'], ['3DO Interactive Multiplayer']),
    '3ds': (['Nintendo - Nintendo 3DS'], ['Nintendo 3DS']),
    'amiga500': (['Commodore - Amiga'], ['Commodore Amiga']),
    'amiga1200': (['Commodore - Amiga'], ['Commodore Amiga']),
    'amigacd32': (['Commodore - CD32'], ['Commodore Amiga CD32']),
    'amigacdtv': (['Commodore - CDTV'], ['Commodore CDTV']),
    'atari2600': (['Atari - 2600'], ['Atari 2600']),
    'atari7800': (['Atari - 7800'], ['Atari 7800']),
    'atomiswave': (['Atomiswave'], ['Sammy Atomiswave']),
    'colecovision': (['Coleco - ColecoVision'], ['ColecoVision']),
    'dos': (['DOS'], ['MS-DOS']),
    'dreamcast': (['Sega - Dreamcast'], ['Sega Dreamcast']),
    'fbneo': (['FBNeo - Arcade Games'], ['Arcade']),
    'fds': (['Nintendo - Family Computer Disk System'], ['Nintendo Famicom Disk System']),
    'gamecube': (['Nintendo - GameCube'], ['Nintendo GameCube']),
    'gamegear': (['Sega - Game Gear'], ['Sega Game Gear']),
    'gb': (['Nintendo - Game Boy'], ['Nintendo Game Boy']),
    'gba': (['Nintendo - Game Boy Advance'], ['Nintendo Game Boy Advance']),
    'gbc': (['Nintendo - Game Boy Color'], ['Nintendo Game Boy Color']),
    'lynx': (['Atari - Lynx'], ['Atari Lynx']),
    'mastersystem': (['Sega - Master System - Mark III'], ['Sega Master System']),
    'megacd': (['Sega - Mega-CD - Sega CD'], ['Sega CD']),
    'megadrive': (['Sega - Mega Drive - Genesis'], ['Sega Genesis']),
    'megadrive-msu': (['Sega - Mega Drive - Genesis'], ['Sega Genesis']),
    'msx1': (['Microsoft - MSX'], ['Microsoft MSX']),
    'msx2': (['Microsoft - MSX2'], ['Microsoft MSX2']),
    'msx2+': (['Microsoft - MSX2'], ['Microsoft MSX2+']),
    'msxturbor': (['Microsoft - MSX2'], ['Microsoft MSX2+']),
    'n64': (['Nintendo - Nintendo 64'], ['Nintendo 64']),
    'n64dd': (['Nintendo - Nintendo 64DD'], ['Nintendo 64DD']),
    'namco3xx': (['FBNeo - Arcade Games'], ['Arcade']),
    'naomi': (['Sega - Naomi'], ['Sega Naomi', 'Arcade']),
    'naomi2': (['Sega - Naomi 2'], ['Sega Naomi 2', 'Arcade']),
    'nds': (['Nintendo - Nintendo DS'], ['Nintendo DS']),
    'neogeo': (['SNK - Neo Geo', 'FBNeo - Arcade Games'], ['SNK Neo Geo AES', 'SNK Neo Geo MVS', 'Arcade']),
    'neogeocd': (['SNK - Neo Geo CD'], ['SNK Neo Geo CD']),
    'nes': (['Nintendo - Nintendo Entertainment System'], ['Nintendo Entertainment System']),
    'ngp': (['SNK - Neo Geo Pocket'], ['SNK Neo Geo Pocket']),
    'ngpc': (['SNK - Neo Geo Pocket Color'], ['SNK Neo Geo Pocket Color']),
    'pcengine': (['NEC - PC Engine - TurboGrafx 16'], ['NEC TurboGrafx-16']),
    'pcenginecd': (['NEC - PC Engine CD - TurboGrafx-CD'], ['NEC TurboGrafx-CD']),
    'pico': (['Sega - PICO'], ['Sega Pico']),
    'ps2': (['Sony - PlayStation 2'], ['Sony Playstation 2']),
    'ps3': (['Sony - PlayStation 3'], ['Sony Playstation 3']),
    'ps4': ([], ['Sony Playstation 4']),
    'psp': (['Sony - PlayStation Portable'], ['Sony PSP']),
    'psvita': (['Sony - PlayStation Vita'], ['Sony Playstation Vita']),
    'psx': (['Sony - PlayStation'], ['Sony Playstation']),
    'satellaview': (['Nintendo - Satellaview'], ['Nintendo Satellaview']),
    'saturn': (['Sega - Saturn'], ['Sega Saturn']),
    'sega32x': (['Sega - 32X'], ['Sega 32X']),
    'sg1000': (['Sega - SG-1000'], ['Sega SG-1000']),
    'sgb': (['Nintendo - Game Boy'], ['Nintendo Game Boy']),
    'snes': (['Nintendo - Super Nintendo Entertainment System'], ['Super Nintendo Entertainment System']),
    'snes-msu1': (['Nintendo - Super Nintendo Entertainment System'], ['Super Nintendo Entertainment System']),
    'spectravideo': (['Spectravideo - SVI-318 - SVI-328'], ['Spectravideo']),
    'sufami': (['Nintendo - Sufami Turbo'], ['Super Nintendo Entertainment System']),
    'systemsp': ([], ['Arcade']),
    'triforce': ([], ['Sega Triforce']),
    'vectrex': (['GCE - Vectrex'], ['GCE Vectrex']),
    'wii': (['Nintendo - Wii'], ['Nintendo Wii']),
    'wiiu': (['Nintendo - Wii U'], ['Nintendo Wii U']),
    'wswan': (['Bandai - WonderSwan'], ['WonderSwan']),
    'wswanc': (['Bandai - WonderSwan Color'], ['WonderSwan Color']),
    'xbox': (['Microsoft - Xbox'], ['Microsoft Xbox']),
}


# --- helpers ---------------------------------------------------------------------------

def fetch(url: str, timeout: int = 30) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def exists(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers=UA, method='HEAD')
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception:
        return False


def notify(text: str) -> None:
    """Pop-up in ES (its local web API), e.g. while the LaunchBox database downloads."""
    try:
        req = urllib.request.Request('http://127.0.0.1:1234/notify', data=text.encode(), method='POST')
        urllib.request.urlopen(req, timeout=2).close()
    except Exception:
        pass


TAGS = re.compile(r'\s*[\(\[][^\)\]]*[\)\]]')


def strip_tags(name: str) -> str:
    return TAGS.sub('', name).strip()


def norm(name: str) -> str:
    s = strip_tags(name).lower().replace('&', ' and ')
    s = re.sub(r'^(.*), the$', r'the \1', s.strip())
    s = re.sub(r'^the ', '', s)
    s = re.sub(r'\b(ii|iii|iv|v|vi)\b', lambda m: {'ii': '2', 'iii': '3', 'iv': '4', 'v': '5', 'vi': '6'}[m.group(1)], s)
    return re.sub(r'[^a-z0-9]', '', s)


STOP = {'the', 'of', 'a', 'an', 'and', 'in', 'on', 'to', 'de', 'la', 'le', 'les', 'no', 'vs'}
ROMAN = {'ii': '2', 'iii': '3', 'iv': '4', 'v': '5', 'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9', 'x': '10'}


def words(name: str) -> set[str]:
    ws = re.findall(r'[a-z0-9]+', strip_tags(name).lower().replace('&', ' and '))
    return {ROMAN.get(w, w) for w in ws if w not in STOP}


def fuzzy(wanted: str, candidates: list[str], limit: int) -> list[str]:
    """Candidates sharing the wanted title's words (numbers must agree, so sequels don't mix)."""
    w = words(wanted)
    if not w:
        return []
    wnum = {x for x in w if x.isdigit()}
    scored = []
    for c in candidates:
        cw = words(c)
        if not cw or {x for x in cw if x.isdigit()} != wnum:
            continue
        hit = len(w & cw)
        score = hit / len(w) * 0.7 + hit / len(cw) * 0.3
        if hit / len(w) >= 0.75:
            scored.append((score, -len(c), c))
    scored.sort(reverse=True)
    out = [c for *_, c in scored[:limit]]
    if not out:  # spelling differences: plain similarity
        by = {norm(c): c for c in candidates}
        out = [by[k] for k in difflib.get_close_matches(norm(wanted), list(by), n=limit, cutoff=0.85)]
    return out


def regions_of(name: str) -> list[str]:
    tags = ' '.join(re.findall(r'\(([^)]*)\)', name)).lower()
    out = []
    for key, lb in (('usa', 'North America'), ('us', 'United States'), ('europe', 'Europe'), ('japan', 'Japan'),
                    ('world', 'World')):
        if re.search(rf'\b{key}\b', tags):
            out.append(lb)
    return out


def rom_names(args) -> list[str]:
    stem = Path(args.file).name
    for ext in ('.zip', '.7z'):
        if stem.lower().endswith(ext):
            stem = stem[:-len(ext)]
    stem = Path(stem).stem if '.' in stem else stem
    names = [stem]
    if args.name and args.name not in names:
        names.append(args.name)
    return names


# --- libretro thumbnails --------------------------------------------------------------

LR = 'https://thumbnails.libretro.com'
LR_KINDS = {'box2d': 'Named_Boxarts', 'screenshot': 'Named_Snaps', 'titleshot': 'Named_Titles'}


def lr_safe(name: str) -> str:
    return re.sub(r'[&*/:`<>?\\|"]', '_', name)


def lr_listing(system: str, kind: str) -> list[str]:
    path = CACHE / 'libretro' / f'{system}.{kind}.json'
    if path.exists() and time.time() - path.stat().st_mtime < 7 * 86400:
        return json.loads(path.read_text())
    html = fetch(f'{LR}/{urllib.parse.quote(system)}/{kind}/', timeout=60).decode('utf-8', 'replace')
    names = sorted({urllib.parse.unquote(m)[:-4] for m in re.findall(r'href="([^"/?]+\.png)"', html)})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(names))
    return names


def best_names(wanted: list[str], available: list[str], limit: int) -> list[str]:
    """Exact name first, then same title (region tags ignored, ROM's region preferred), then close titles."""
    avail = set(available)
    out: list[str] = []
    for w in wanted:
        if lr_safe(w) in avail and lr_safe(w) not in out:
            out.append(lr_safe(w))
    by_norm: dict[str, list[str]] = {}
    for a in available:
        by_norm.setdefault(norm(a), []).append(a)
    pref = regions_of(wanted[0])
    for w in wanted:
        same = by_norm.get(norm(w), [])
        same.sort(key=lambda a: (not any(r.split()[0].lower() in a.lower() for r in pref), len(a)))
        out += [a for a in same if a not in out]
    if len(out) < limit:
        titles = {strip_tags(a): a for a in reversed(available)}  # one entry per title
        for t in fuzzy(wanted[-1], list(titles), limit):
            same = sorted(by_norm.get(norm(t), [titles[t]]),
                          key=lambda a: (not any(r.split()[0].lower() in a.lower() for r in pref), len(a)))
            out += [a for a in same[:1] if a not in out]
    return out[:limit]


def scrape_libretro(args) -> list[dict]:
    folders = SYSTEMS.get(args.system, ([], []))[0]
    results = []
    for folder in folders:
        try:
            boxes = lr_listing(folder, 'Named_Boxarts')
        except Exception as e:
            print(f'libretro {folder}: {e}', file=sys.stderr)
            continue
        for match in best_names(rom_names(args), boxes, 5 if args.manual else 1):
            media = {}
            for key, kind in LR_KINDS.items():
                try:
                    listing = boxes if kind == 'Named_Boxarts' else lr_listing(folder, kind)
                except Exception:
                    continue
                if match in listing:
                    media[key] = f'{LR}/{urllib.parse.quote(folder)}/{kind}/{urllib.parse.quote(match)}.png'
            if media:
                results.append({'name': strip_tags(match), 'media': media})
        if results:
            break
    return results


# --- LaunchBox ------------------------------------------------------------------------

LB_ZIP = 'https://gamesdb.launchbox-app.com/Metadata.zip'
LB_IMG = 'https://images.launchbox-app.com/'
LB_TYPES = {  # LaunchBox image type -> our media key (first listed wins)
    'Box - Front': 'box2d', 'Box - Front - Reconstructed': 'box2d', 'Fanart - Box - Front': 'box2d',
    'Box - 3D': 'box3d', 'Box - Back': 'boxback', 'Screenshot - Gameplay': 'screenshot',
    'Screenshot - Game Title': 'titleshot', 'Fanart - Background': 'fanart', 'Clear Logo': 'logo',
    'Cart - Front': 'cartridge', 'Disc': 'cartridge',
}


def lb_db() -> sqlite3.Connection:
    db = CACHE / 'launchbox' / 'launchbox.sqlite'
    db.parent.mkdir(parents=True, exist_ok=True)
    with open(db.parent / '.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # one download/build at a time (bulk scraping runs several)
        if not db.exists() or time.time() - db.stat().st_mtime > 60 * 86400:
            lb_build(db)
    return sqlite3.connect(f'file:{db}?mode=ro', uri=True)


def lb_build(db: Path) -> None:
    notify('Downloading the LaunchBox games database (110 MB, first use only)...')
    tmpzip = db.with_suffix('.zip.part')
    with urllib.request.urlopen(urllib.request.Request(LB_ZIP, headers=UA), timeout=60) as r, open(tmpzip, 'wb') as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    notify('Indexing the LaunchBox games database...')
    tmpdb = db.with_suffix('.sqlite.part')
    tmpdb.unlink(missing_ok=True)
    con = sqlite3.connect(tmpdb)
    con.executescript('''
        CREATE TABLE games(id INTEGER PRIMARY KEY, platform TEXT, name TEXT, norm TEXT, overview TEXT,
                           date TEXT, developer TEXT, publisher TEXT, genres TEXT, players TEXT, rating REAL);
        CREATE TABLE alts(id INTEGER, norm TEXT);
        CREATE TABLE images(id INTEGER, type TEXT, region TEXT, file TEXT);''')
    with zipfile.ZipFile(tmpzip) as z, z.open('Metadata.xml') as xml:
        rows = {'games': [], 'alts': [], 'images': []}

        def flush(force=False):
            for t, sql in (('games', 'INSERT OR REPLACE INTO games VALUES (?,?,?,?,?,?,?,?,?,?,?)'),
                           ('alts', 'INSERT INTO alts VALUES (?,?)'), ('images', 'INSERT INTO images VALUES (?,?,?,?)')):
                if rows[t] and (force or len(rows[t]) >= 5000):
                    con.executemany(sql, rows[t])
                    rows[t].clear()

        for _, el in ET.iterparse(xml):
            tag = el.tag
            if tag == 'Game':
                t = el.findtext
                try:
                    rating = float(t('CommunityRating') or 0) / 5
                except ValueError:
                    rating = 0
                rows['games'].append((int(t('DatabaseID') or 0), t('Platform'), t('Name'), norm(t('Name') or ''),
                                      t('Overview'), (t('ReleaseDate') or '')[:10], t('Developer'), t('Publisher'),
                                      t('Genres'), t('MaxPlayers'), rating))
            elif tag == 'GameAlternateName':
                rows['alts'].append((int(el.findtext('DatabaseID') or 0), norm(el.findtext('AlternateName') or '')))
            elif tag == 'GameImage':
                if el.findtext('Type') in LB_TYPES:
                    rows['images'].append((int(el.findtext('DatabaseID') or 0), el.findtext('Type'),
                                           el.findtext('Region') or '', el.findtext('FileName')))
            else:
                continue
            el.clear()
            flush()
        flush(True)
    con.executescript('''CREATE INDEX g_pn ON games(platform, norm); CREATE INDEX a_n ON alts(norm);
                         CREATE INDEX i_id ON images(id);''')
    con.commit()
    con.close()
    tmpdb.replace(db)
    tmpzip.unlink(missing_ok=True)
    notify('LaunchBox games database ready')


def scrape_launchbox(args) -> list[dict]:
    platforms = SYSTEMS.get(args.system, ([], []))[1]
    if not platforms:
        return []
    con = lb_db()
    q = ','.join('?' * len(platforms))
    names = rom_names(args)
    ids: list[int] = []
    for n in names:
        key = norm(n)
        for (i,) in con.execute(f'SELECT id FROM games WHERE platform IN ({q}) AND norm=?', (*platforms, key)):
            ids.append(i)
        for (i,) in con.execute(f'SELECT g.id FROM alts a JOIN games g ON g.id=a.id WHERE a.norm=? AND g.platform IN ({q})',
                                (key, *platforms)):
            ids.append(i)
    limit = 5 if args.manual else 1
    if len(ids) < limit:
        allnames = dict(con.execute(f'SELECT name, id FROM games WHERE platform IN ({q})', platforms).fetchall())
        for n in fuzzy(names[-1], list(allnames), limit):
            ids.append(allnames[n])
    seen, results = set(), []
    pref = regions_of(names[0]) + ['North America', 'United States', 'World', 'Europe', '', 'Japan']
    for i in ids:
        if i in seen or len(results) >= limit:
            continue
        seen.add(i)
        g = con.execute('SELECT name, overview, date, developer, publisher, genres, players, rating FROM games WHERE id=?',
                        (i,)).fetchone()
        media: dict[str, tuple[int, str]] = {}
        for typ, region, file in con.execute('SELECT type, region, file FROM images WHERE id=?', (i,)):
            key = LB_TYPES[typ]
            rank = (list(LB_TYPES).index(typ), pref.index(region) if region in pref else len(pref))
            if key not in media or rank < media[key][0]:
                media[key] = (rank, LB_IMG + urllib.parse.quote(file))
        results.append({
            'name': g[0], 'desc': g[1] or '', 'releasedate': (g[2] or '').replace('-', ''),
            'developer': g[3] or '', 'publisher': g[4] or '', 'genre': ', '.join(x.strip() for x in (g[5] or '').split(';') if x.strip()),
            'players': g[6] or '', 'rating': f'{g[7]:.2f}' if g[7] else '',
            'media': {k: v[1] for k, v in media.items()},
        })
    return results


# --- GameTDB --------------------------------------------------------------------------

GT = 'https://art.gametdb.com'


def disc_id(path: Path) -> str | None:
    """GameCube/Wii disc ID (6 chars) from ISO/GCM/NKit, RVZ/WIA, CISO, WBFS; DS game code (4 chars)."""
    try:
        with open(path, 'rb') as f:
            head = f.read(0x8006)
    except OSError:
        return None
    ext = path.suffix.lower()
    if ext == '.nds':
        code = head[0x0C:0x10]
    elif head[:4] in (b'RVZ\x01', b'WIA\x01'):
        code = head[0x58:0x5E]
    elif head[:4] == b'CISO':
        code = head[0x8000:0x8006]
    elif head[:4] == b'WBFS':
        with open(path, 'rb') as f:
            f.seek(0x200)
            code = f.read(6)
    else:
        code = head[:6]
    try:
        s = code.decode('ascii')
    except UnicodeDecodeError:
        return None
    return s if re.fullmatch(r'[A-Z0-9]{4}([A-Z0-9]{2})?', s) else None


def gt_regions(code: str) -> list[str]:
    first = {'E': 'US', 'J': 'JA', 'K': 'KO', 'P': 'EN', 'D': 'DE', 'F': 'FR', 'S': 'ES', 'I': 'IT',
             'U': 'AU'}.get(code[3], 'EN')
    return list(dict.fromkeys([first, 'US', 'EN', 'JA']))


def gt_title(platform: str, code: str) -> str | None:
    path = CACHE / 'gametdb' / f'{platform}.txt'
    if not path.exists() or time.time() - path.stat().st_mtime > 30 * 86400:
        url = {'wii': 'https://www.gametdb.com/wiitdb.txt?LANG=EN', 'ds': 'https://www.gametdb.com/dstdb.txt?LANG=EN'}[platform]
        try:
            data = fetch(url, timeout=60)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        except Exception:
            return None
    for line in path.read_text('utf-8', 'replace').splitlines():
        if line.startswith(code + ' = '):
            return line.split(' = ', 1)[1].strip()
    return None


def scrape_gametdb(args) -> list[dict]:
    platform = {'gamecube': 'wii', 'wii': 'wii', 'nds': 'ds'}.get(args.system)
    if not platform:
        return []
    code = disc_id(Path(args.file))
    if not code:
        return []
    # GameTDB's server can be slow (seconds per request), so only the cover is checked: the
    # first region that has it is used for the 3D cover and disc/cart art too (ES skips any
    # image that turns out to be missing).
    if platform == 'wii':
        cover, extra = ('cover', 'png'), {'box3d': ('cover3D', 'png'), 'cartridge': ('disc', 'png')}
    else:
        cover, extra = ('coverHQ', 'jpg'), {'cartridge': ('cart', 'png')}  # DS: no 3D covers
    region = next((r for r in gt_regions(code)[:3] if exists(f'{GT}/{platform}/{cover[0]}/{r}/{code}.{cover[1]}')), None)
    if region is None:
        return []
    media = {'box2d': f'{GT}/{platform}/{cover[0]}/{region}/{code}.{cover[1]}'}
    for key, (folder, ext) in extra.items():
        media[key] = f'{GT}/{platform}/{folder}/{region}/{code}.{ext}'
    return [{'name': gt_title(platform, code) or strip_tags(rom_names(args)[0]), 'media': media}]


SOURCES = {'launchbox': scrape_launchbox, 'libretro': scrape_libretro, 'gametdb': scrape_gametdb}


def main() -> int:
    p = argparse.ArgumentParser(prog='acrobato-scrape')
    p.add_argument('source', choices=sorted(SOURCES))
    p.add_argument('--system', required=True)
    p.add_argument('--file', required=True)
    p.add_argument('--name', default='')
    p.add_argument('--manual', action='store_true')
    args = p.parse_args()
    try:
        results = SOURCES[args.source](args)
    except Exception as e:
        print(f'{args.source}: {e}', file=sys.stderr)
        print(json.dumps({'error': str(e)}))
        return 0
    print(json.dumps(results))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
