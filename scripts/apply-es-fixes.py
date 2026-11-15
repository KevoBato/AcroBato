#!/usr/bin/env python3
"""AcroBato scraper changes to batocera-emulationstation.

- Scrapers: LaunchBox (default), libretro thumbnails, GameTDB (ExternalScraper.*, backed by
  the acrobato-scrape helper; no account needed) and SteamGridDB (SteamGridDBScraper.*, the
  user's own free API key in Scraper > Accounts). ScreenScraper/TheGamesDB need Batocera's
  private developer keys and were never compiled in; IGDB and ArcadeDB are removed.
- Fixes the scrape crashes: ES defaulted to "ScreenScraper" (not in this build -> null
  pointer), and IGDB without keys threw an uncaught "INVALID CREDENTIALS" (abort).
  Unknown scraper names now fall back to an available one; the new scrapers never throw.
  Single-game scrapes ask every source (SteamGridDB adds nothing without a key); a bulk
  scrape with SteamGridDB as the scraper and no key shows a message.
Exact-text edits; fails loudly if upstream changed. Usage: apply-es-fixes.py <es source dir>
"""
import shutil
import sys
from pathlib import Path

root = Path(sys.argv[1])
here = Path(__file__).resolve().parent.parent
NO_KEY = ('_("TO SCRAPE WITH STEAMGRIDDB, ENTER YOUR API KEY IN SCRAPER > ACCOUNTS.\\n'
          'GET A FREE KEY AT STEAMGRIDDB.COM > PREFERENCES > API.")')


def edit(rel, old, new, count=1):
    p = root / rel
    s = p.read_text()
    if new in s and old not in s:
        return  # already applied
    if s.count(old) != count:
        sys.exit(f'{rel}: expected {count} match(es) of {old[:60]!r}, found {s.count(old)}')
    p.write_text(s.replace(old, new))
    print(f'edited {rel}')


for f in ('SteamGridDBScraper.h', 'SteamGridDBScraper.cpp', 'ExternalScraper.h', 'ExternalScraper.cpp'):
    shutil.copy(here / 'patches/emulationstation' / f, root / 'es-app/src/scrapers' / f)

edit('es-app/CMakeLists.txt',
     '${CMAKE_CURRENT_SOURCE_DIR}/src/scrapers/IGDBScraper.h\n',
     '${CMAKE_CURRENT_SOURCE_DIR}/src/scrapers/IGDBScraper.h\n'
     '    ${CMAKE_CURRENT_SOURCE_DIR}/src/scrapers/SteamGridDBScraper.h\n'
     '    ${CMAKE_CURRENT_SOURCE_DIR}/src/scrapers/ExternalScraper.h\n')
edit('es-app/CMakeLists.txt',
     '${CMAKE_CURRENT_SOURCE_DIR}/src/scrapers/IGDBScraper.cpp\n',
     '${CMAKE_CURRENT_SOURCE_DIR}/src/scrapers/IGDBScraper.cpp\n'
     '    ${CMAKE_CURRENT_SOURCE_DIR}/src/scrapers/SteamGridDBScraper.cpp\n'
     '    ${CMAKE_CURRENT_SOURCE_DIR}/src/scrapers/ExternalScraper.cpp\n')

S = 'es-app/src/scrapers/Scraper.cpp'
edit(S, '#include "IGDBScraper.h"\n',
     '#include "IGDBScraper.h"\n#include "SteamGridDBScraper.h"\n#include "ExternalScraper.h"\n')
edit(S, '\t{ "IGDB", new IGDBScraper() },\n\t{ "ArcadeDB", new ArcadeDBScraper() }\n',
     '\t{ "LaunchBox", new ExternalScraper("launchbox", { ScraperMediaSource::Screenshot, ScraperMediaSource::TitleShot,\n'
     '\t\tScraperMediaSource::Box2d, ScraperMediaSource::Box3d, ScraperMediaSource::BoxBack, ScraperMediaSource::FanArt,\n'
     '\t\tScraperMediaSource::Marquee, ScraperMediaSource::Wheel, ScraperMediaSource::Cartridge, ScraperMediaSource::Ratings }) },\n'
     '\t{ "libretro", new ExternalScraper("libretro", { ScraperMediaSource::Screenshot, ScraperMediaSource::TitleShot,\n'
     '\t\tScraperMediaSource::Box2d }) },\n'
     '\t{ "GameTDB", new ExternalScraper("gametdb", { ScraperMediaSource::Box2d, ScraperMediaSource::Box3d,\n'
     '\t\tScraperMediaSource::Cartridge }) },\n'
     '\t{ "SteamGridDB", new SteamGridDBScraper() }\n')
edit(S,
     '\tfor (auto scrap : Scraper::scrapers)\n\t\tif (scrap.first == scraper)\n\t\t\treturn scrap.second;\n\n\treturn nullptr;\n}',
     '\tfor (auto scrap : Scraper::scrapers)\n\t\tif (scrap.first == scraper)\n\t\t\treturn scrap.second;\n\n'
     '\t// the configured scraper is not in this build: use one that is\n'
     '\treturn Scraper::scrapers.empty() ? nullptr : Scraper::scrapers.front().second;\n}')

edit('es-core/src/Settings.cpp', 'mStringMap["Scraper"] = "ScreenScraper";',
     'mStringMap["Scraper"] = "LaunchBox";\n\tmStringMap["SteamGridDBApiKey"] = "";')

G = 'es-app/src/guis/GuiScraperStart.cpp'
edit(G, '#include "scrapers/ThreadedScraper.h"\n',
     '#include "scrapers/ThreadedScraper.h"\n#include "scrapers/SteamGridDBScraper.h"\n')
edit(G,
     '\taddGroup(_("SCREENSCRAPER"));\n'
     '\taddInputTextConfigRow(_("USERNAME"), "ScreenScraperUser", false, true);\n'
     '\taddInputTextConfigRow(_("PASSWORD"), "ScreenScraperPass", true, true);\n\n'
     '\taddGroup(_("IGDB"));\n'
     '\taddInputTextConfigRow(_("CLIENT ID"), "IGDBClientID", false, true);\n'
     '\taddInputTextConfigRow(_("CLIENT SECRET"), "IGDBSecret", true, true);\n',
     '\taddGroup(_("STEAMGRIDDB"));\n'
     '\taddInputTextConfigRow(_("API KEY"), "SteamGridDBApiKey", true, true);\n')
edit(G,
     'void GuiScraperStart::pressedStart()\n{\n',
     'void GuiScraperStart::pressedStart()\n{\n'
     '\tif (Scraper::getScraperName(Scraper::getScraper()) == "SteamGridDB" && !SteamGridDBScraper::hasApiKey())\n\t{\n'
     f'\t\tmWindow->pushGui(new GuiMsgBox(mWindow, {NO_KEY}));\n'
     '\t\treturn;\n\t}\n\n')

# --- Empty library: start anyway -----------------------------------------------------------
# ES quits with "WE CAN'T FIND ANY SYSTEMS!" when no system has a game. AcroBato ships no games,
# so on an empty library ES shows every (empty) system for this session (setting not saved)
# and tells the user where to put games. Once a system has games, only those are shown again.
U = 'es-app/src/views/UIModeController.cpp'
edit(U,
     'bool UIModeController::LoadEmptySystems()\n{\n'
     '\treturn getInstance()->isUIModeFull() && Settings::LoadEmptySystems();\n}\n',
     'bool gEmptyLibrary = false;  // AcroBato: no games anywhere yet (set in main.cpp)\n\n'
     'bool UIModeController::LoadEmptySystems()\n{\n'
     '\treturn gEmptyLibrary || (getInstance()->isUIModeFull() && Settings::LoadEmptySystems());\n}\n')
M = 'es-app/src/main.cpp'
edit(M,
     '\tif(SystemData::sSystemVector.size() == 0)\n\t{\n'
     '\t\tLOG(LogError) << "No systems found!',
     '\textern bool gEmptyLibrary;\n'
     '\tif (SystemData::sSystemVector.size() == 0 && !gEmptyLibrary)\n\t{\n'
     '\t\tLOG(LogWarning) << "No games found: showing all systems so the library can be set up";\n'
     '\t\tgEmptyLibrary = true;\n'
     '\t\tSystemData::loadConfig(window);\n\t}\n\n'
     '\tif(SystemData::sSystemVector.size() == 0)\n\t{\n'
     '\t\tLOG(LogError) << "No systems found!')
edit(M,
     '\t\twindow.pushGui(new GuiMsgBox(&window, errorMsg, _("QUIT"), [] { Utils::Platform::quitES(); }));\n\t}\n',
     '\t\twindow.pushGui(new GuiMsgBox(&window, errorMsg, _("QUIT"), [] { Utils::Platform::quitES(); }));\n\t}\n'
     '\telse\n\t{\n'
     '\t\textern bool gEmptyLibrary;\n'
     '\t\tif (gEmptyLibrary)\n\t\t{\n'
     '\t\t\tconst char* u = getenv("ES_USERDATA");\n'
     '\t\t\tstd::string roms = std::string(u ? u : "/userdata") + "/roms";\n'
     '\t\t\twindow.pushGui(new GuiMsgBox(&window, _("WELCOME TO ACROBATO!") + std::string("\\n\\n") +\n'
     '\t\t\t\t_("NO GAMES FOUND YET. PUT YOUR GAMES IN THE FOLDER OF EACH SYSTEM IN:") + "\\n" + roms + "\\n\\n" +\n'
     '\t\t\t\t_("EACH SYSTEM FOLDER HAS AN _info.txt FILE LISTING THE FILE TYPES AND BIOS FILES IT NEEDS. "\n'
     '\t\t\t\t  "RESTART ACROBATO AFTER ADDING GAMES."), _("OK"), nullptr));\n'
     '\t\t}\n\t}\n')
