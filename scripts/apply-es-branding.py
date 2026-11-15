#!/usr/bin/env python3
"""AcroBato changes to batocera-emulationstation (applied after 0001-relocatable-paths):
- app name ACROBATO (main menu footer reads "ACROBATO V<version>"), window title "AcroBato"
- "BATOCERA SPLASH IMAGE" option renamed
- Quit menu: "EXIT ACROBATO"; the Restart/Suspend/Shutdown *system* entries are hidden,
  because outside Batocera OS they only close ES (they leave a flag file for the OS).
Exact-text edits; fails loudly if upstream changed. Usage: apply-es-branding.py <es source dir>
"""
import sys
from pathlib import Path

root = Path(sys.argv[1])


def edit(rel, old, new, count=1):
    p = root / rel
    s = p.read_text()
    if new in s and old not in s:
        return  # already applied
    if s.count(old) != count:
        sys.exit(f'{rel}: expected {count} match(es) of {old[:60]!r}, found {s.count(old)}')
    p.write_text(s.replace(old, new))
    print(f'edited {rel}')


edit('es-app/src/ApiSystem.cpp', '#if BATOCERA\n\treturn "BATOCERA";', '#if BATOCERA\n\treturn "ACROBATO";')
edit('es-app/src/guis/GuiMenu.cpp', '_("BATOCERA SPLASH IMAGE")', '_("ACROBATO SPLASH IMAGE")')
edit('es-core/src/renderers/Renderer.cpp', 'SDL_CreateWindow("EmulationStation"', 'SDL_CreateWindow("AcroBato"')

# Quit menu
gm = root / 'es-app/src/guis/GuiMenu.cpp'
s = gm.read_text()
start_marker = '\ts->addEntry(_("RESTART SYSTEM"), false, [window] {'
end_marker = '#ifdef WIN32\n\tif (Settings::getInstance()->getBool("ShowExit"))'
if 'EXIT ACROBATO' not in s:
    a, b = s.find(start_marker), s.find(end_marker)
    if a < 0 or b < 0 or b < a:
        sys.exit('GuiMenu.cpp: quit menu layout changed')
    system_entries = s[a:b]
    new = ('\ts->addEntry(_("EXIT ACROBATO"), false, [] { Utils::Platform::quitES(Utils::Platform::QuitMode::QUIT); }, "iconQuit");\n\n'
           '\t// AcroBato runs as a desktop app: these only make sense on Batocera OS\n'
           '\tif (false)\n\t{\n'
           + ''.join('\t' + line if line.strip() else line for line in system_entries.splitlines(True))
           + '\t}\n\n')
    gm.write_text(s[:a] + new + s[b:])
    print('edited es-app/src/guis/GuiMenu.cpp (quit menu)')
