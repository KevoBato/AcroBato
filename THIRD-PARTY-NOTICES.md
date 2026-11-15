# AcroBato third-party notices

AcroBato bundles the open-source software listed below. Each component remains under its own
license; the full texts are in this folder (`usr/share/acrobato/licenses/` in the AppImage).

## Source code

Source code for the GPL/LGPL/MPL components is available from the upstream projects listed below, at the
versions shown. AcroBato's own build scripts and its changes to these projects are published in the AcroBato
source repository.

## Restrictions to be aware of

- **Non-commercial cores:** Snes9x, Genesis Plus GX, PicoDrive, FinalBurn Neo and Opera may not be sold or used
  in a commercial product or activity. AcroBato must stay free to include them.
- **FinalBurn Neo** additionally forbids asking for donations for a project that uses its code.
- **Opera (3DO)** requires full credit to the FreeDO authors (Alexander Troosh, Maxim Grishin and others).
- No BIOS files or commercial games are included. Users supply their own.

## Components

| Component | Version | License | Source | License files |
|---|---|---|---|---|
| AcroBato (build scripts, patches, launcher glue, scrapers, downloader) | 0.1.0 | GPL-3.0-or-later | AcroBato source repository | acrobato/LICENSE |
| batocera-emulationstation | b722aa988a | MIT (fonts: Apache-2.0 / Ubuntu Font Licence) | https://github.com/batocera-linux/batocera-emulationstation | emulationstation/LICENSE.md, emulationstation/opensans_license.txt, emulationstation/ubuntu_licence.txt |
| Batocera (batocera-launch, hotkeygen, system data, controller database, es_systems) | 23d3fcfea8 | LGPL-3.0-or-later | https://github.com/batocera-linux/batocera.linux | batocera/COPYING, batocera/COPYING.LESSER, batocera/LICENSE-NOTICE |
| evmapy (with Batocera patches) | bd65338c23 | GPL-2.0 | https://github.com/kempniu/evmapy | evmapy/LICENSE |
| RetroArch | 4b74434a30 | GPL-3.0 | https://github.com/libretro/RetroArch | retroarch/COPYING |
| SDL2 | 2.32.10 | Zlib (SDL2 and SDL3 with Batocera input patches) | https://libsdl.org | sdl2/LICENSE.txt |
| SDL3 | 3.4.14 | Zlib (SDL2 and SDL3 with Batocera input patches) | https://libsdl.org | sdl3/LICENSE.txt |
| SDL2_mixer | a37e09f85d | Zlib (SDL2 and SDL3 with Batocera input patches) | https://github.com/libsdl-org/SDL_mixer | sdl2_mixer/LICENSE.txt |
| FFmpeg (minimal build, LGPL configuration) | d61977cbe4 | LGPL-2.1-or-later | https://ffmpeg.org | ffmpeg/COPYING.LGPLv2.1, ffmpeg/LICENSE.md |
| fceumm (RetroArch core) | 236ccdfc91 | GPL-2.0 | libretro core source (fceumm), see Batocera recipe | cores-fceumm/Copying |
| nestopia (RetroArch core) | 224713b257 | GPL-2.0 | libretro core source (nestopia), see Batocera recipe | cores-nestopia/COPYING |
| snes9x (RetroArch core) | 890b5d4455 | Snes9x license (non-commercial) | libretro core source (snes9x), see Batocera recipe | cores-snes9x/LICENSE |
| genesisplusgx (RetroArch core) | 27426f00aa | Genesis Plus GX license (non-commercial) | libretro core source (genesisplusgx), see Batocera recipe | cores-genesisplusgx/LICENSE.txt |
| picodrive (RetroArch core) | ab021146b7 | MAME-style license (non-commercial) | libretro core source (picodrive), see Batocera recipe | cores-picodrive/COPYING |
| gambatte (RetroArch core) | d9d6cd0638 | GPL-2.0 | libretro core source (gambatte), see Batocera recipe | cores-gambatte/COPYING |
| mgba (RetroArch core) | 25ca25612e | MPL-2.0 | libretro core source (mgba), see Batocera recipe | cores-mgba/LICENSE |
| pcsx (RetroArch core) | 8625c395a2 | GPL-2.0 | libretro core source (pcsx), see Batocera recipe | cores-pcsx/COPYING |
| stella2014 (RetroArch core) | 7d1361e407 | GPL-2.0 | libretro core source (stella2014), see Batocera recipe | cores-stella2014/license.txt |
| handy (RetroArch core) | bc55d462f0 | Zlib | libretro core source (handy), see Batocera recipe | cores-handy/license.txt |
| beetle-ngp (RetroArch core) | a50d5ac288 | GPL-2.0 | libretro core source (beetle-ngp), see Batocera recipe | cores-beetle-ngp/COPYING |
| beetle-wswan (RetroArch core) | 4b01295838 | GPL-2.0 | libretro core source (beetle-wswan), see Batocera recipe | cores-beetle-wswan/COPYING |
| beetle-pce-fast (RetroArch core) | eed8075ece | GPL-2.0 | libretro core source (beetle-pce-fast), see Batocera recipe | cores-beetle-pce-fast/COPYING |
| prosystem (RetroArch core) | 8a88014287 | GPL-2.0 | libretro core source (prosystem), see Batocera recipe | cores-prosystem/License.txt |
| vecx (RetroArch core) | 8f671cc9d7 | GPL-3.0 | libretro core source (vecx), see Batocera recipe | cores-vecx/LICENSE.md |
| melonds (RetroArch core) | 66b5d2634c | GPL-3.0 | libretro core source (melonds), see Batocera recipe | cores-melonds/LICENSE |
| desmume (RetroArch core) | 8f6b32cb9a | GPL-2.0 | libretro core source (desmume), see Batocera recipe | cores-desmume/license.txt |
| dolphin (RetroArch core) | ed70219e8b | GPL-2.0-or-later (some parts other licenses) | libretro core source (dolphin), see Batocera recipe | cores-dolphin/COPYING |
| mupen64plus-next (RetroArch core) | 6752836de8 | GPL-2.0 | libretro core source (mupen64plus-next), see Batocera recipe | cores-mupen64plus-next/LICENSE |
| parallel-n64 (RetroArch core) | 2f3bf60dcd | GPL-2.0 (parts MIT) | libretro core source (parallel-n64), see Batocera recipe | cores-parallel-n64/COPYING, cores-parallel-n64/COPYING, cores-parallel-n64/LICENSE |
| ppsspp (RetroArch core) | fa50bb1976 | GPL-2.0-or-later | libretro core source (ppsspp), see Batocera recipe | cores-ppsspp/LICENSE.TXT |
| flycast (RetroArch core) | 5aa091fde6 | GPL-2.0 | libretro core source (flycast), see Batocera recipe | cores-flycast/LICENSE |
| swanstation (RetroArch core) | 7f69c199ed | GPL-3.0 | libretro core source (swanstation), see Batocera recipe | cores-swanstation/LICENSE |
| fbneo (RetroArch core) | a251c76229 | FBNeo license (non-commercial, no donations) | libretro core source (fbneo), see Batocera recipe | cores-fbneo/license.txt, cores-fbneo/LICENSE.md |
| beetle-saturn (RetroArch core) | 1382b85dca | GPL-2.0 | libretro core source (beetle-saturn), see Batocera recipe | cores-beetle-saturn/COPYING |
| dosbox-pure (RetroArch core) | 6108e45e5f | GPL-2.0 | libretro core source (dosbox-pure), see Batocera recipe | cores-dosbox-pure/LICENSE |
| opera (RetroArch core) | a501a278d0 | FreeDO modified LGPL (non-commercial, credits required) | libretro core source (opera), see Batocera recipe | cores-opera/LICENSE-FreeDO.txt |
| neocd (RetroArch core) | 3118c69017 | LGPL-3.0 | libretro core source (neocd), see Batocera recipe | cores-neocd/LICENSE.md |
| bluemsx (RetroArch core) | e3086eb5d3 | BSD-style / GPL (per file) | libretro core source (bluemsx), see Batocera recipe | cores-bluemsx/license.txt |
| puae (RetroArch core) | 6536174a80 | GPL-2.0 | libretro core source (puae), see Batocera recipe | cores-puae/COPYING |
| libretro core info files | eac3a2784d | MIT | https://github.com/libretro/libretro-core-info | libretro-core-info/COPYING |
| Carbon theme for EmulationStation |  | no license stated (by Rookervik, based on "simple" by Nils Bonenberger; maintained by fabricecaruso); credits in its readme.txt | https://github.com/fabricecaruso/es-theme-carbon | theme-carbon/readme.txt |
| RetroArch assets (menu icons, sounds) |  | CC-BY-4.0 | https://github.com/libretro/retroarch-assets | - |
| RetroArch shaders (slang/glsl presets used by Batocera) |  | various, per shader (see each file header) | https://github.com/libretro/slang-shaders | - |
| Dolphin "Sys" data / PPSSPP assets |  | GPL-2.0-or-later (part of Dolphin / PPSSPP) | https://github.com/dolphin-emu/dolphin, https://github.com/hrydgard/ppsspp | - |
| Homebrew games for the first start (2048 by tsone, Old Towers by RetroSouls, Space Twins by 9wires, Reflectron and Santatlantean by Aetherbyte) |  | freeware, distributed by Batocera; permission for AcroBato not yet confirmed with the authors | Batocera datainit | - |
| Python 3.14 (python-build-standalone) |  | PSF-2.0 (bundled libraries: see its LICENSE.txt) | https://github.com/astral-sh/python-build-standalone | python/LICENSE.txt |
| aiodns (Python package) | 4.0.4 | MIT | https://pypi.org/project/aiodns | python-aiodns/LICENSE |
| aiohappyeyeballs (Python package) | 2.7.1 | PSF-2.0 | https://pypi.org/project/aiohappyeyeballs | python-aiohappyeyeballs/LICENSE |
| aiohttp (Python package) | 3.14.5 | Apache-2.0 AND MIT | https://pypi.org/project/aiohttp | python-aiohttp/LICENSE.txt, python-aiohttp/LICENSE |
| aiosignal (Python package) | 1.4.0 | Apache 2.0 | https://pypi.org/project/aiosignal | python-aiosignal/LICENSE |
| attrs (Python package) | 26.1.0 | MIT | https://pypi.org/project/attrs | python-attrs/LICENSE |
| batocera-common (Python package, part of Batocera) | 44.0 | LGPL-3.0-or-later | https://github.com/batocera-linux/batocera.linux | batocera/COPYING.LESSER, batocera/LICENSE-NOTICE |
| batocera-launch (Python package, part of Batocera) | 44.0 | LGPL-3.0-or-later | https://github.com/batocera-linux/batocera.linux | batocera/COPYING.LESSER, batocera/LICENSE-NOTICE |
| batocera-launch-dolphin (Python package, part of Batocera) | 44.0 | LGPL-3.0-or-later | https://github.com/batocera-linux/batocera.linux | batocera/COPYING.LESSER, batocera/LICENSE-NOTICE |
| batocera-launch-flycast (Python package, part of Batocera) | 44.0 | LGPL-3.0-or-later | https://github.com/batocera-linux/batocera.linux | batocera/COPYING.LESSER, batocera/LICENSE-NOTICE |
| batocera-launch-libretro (Python package, part of Batocera) | 44.0 | LGPL-3.0-or-later | https://github.com/batocera-linux/batocera.linux | batocera/COPYING.LESSER, batocera/LICENSE-NOTICE |
| batocera-launch-libretro-mame (Python package, part of Batocera) | 44.0 | LGPL-3.0-or-later | https://github.com/batocera-linux/batocera.linux | batocera/COPYING.LESSER, batocera/LICENSE-NOTICE |
| batocera-launch-mame (Python package, part of Batocera) | 44.0 | LGPL-3.0-or-later | https://github.com/batocera-linux/batocera.linux | batocera/COPYING.LESSER, batocera/LICENSE-NOTICE |
| batocera-launch-mame-common (Python package, part of Batocera) | 44.0 | LGPL-3.0-or-later | https://github.com/batocera-linux/batocera.linux | batocera/COPYING.LESSER, batocera/LICENSE-NOTICE |
| batocera-launch-pcsx2 (Python package, part of Batocera) | 44.0 | LGPL-3.0-or-later | https://github.com/batocera-linux/batocera.linux | batocera/COPYING.LESSER, batocera/LICENSE-NOTICE |
| batocera-launch-rpcs3 (Python package, part of Batocera) | 44.0 | LGPL-3.0-or-later | https://github.com/batocera-linux/batocera.linux | batocera/COPYING.LESSER, batocera/LICENSE-NOTICE |
| brotli (Python package) | 1.2.1 | MIT | https://pypi.org/project/brotli | python-brotli/LICENSE |
| cffi (Python package) | 2.1.1 | MIT-0 | https://pypi.org/project/cffi | python-cffi/LICENSE |
| configobj (Python package) | 5.0.9 | BSD-3-Clause | https://pypi.org/project/configobj | python-configobj/LICENSE |
| dbus-fast (Python package) | 5.2.0 | MIT | https://pypi.org/project/dbus-fast | python-dbus-fast/LICENSE |
| evdev (Python package) | 2.0.0 | BSD-3-Clause | https://pypi.org/project/evdev | python-evdev/LICENSE |
| frozenlist (Python package) | 1.8.0 | Apache-2.0 | https://pypi.org/project/frozenlist | python-frozenlist/LICENSE |
| hotkeygen (Python package, part of Batocera) | 1.1 | LGPL-3.0-or-later | https://github.com/batocera-linux/batocera.linux | batocera/COPYING.LESSER, batocera/LICENSE-NOTICE |
| idna (Python package) | 3.20 | BSD-3-Clause | https://pypi.org/project/idna | python-idna/LICENSE.md |
| lazy-loader (Python package) | 0.6 | BSD-3-Clause | https://pypi.org/project/lazy-loader | python-lazy-loader/LICENSE.md |
| multidict (Python package) | 7.2.1 | Apache-2.0 | https://pypi.org/project/multidict | python-multidict/LICENSE |
| packaging (Python package) | 26.3 | Apache-2.0 OR BSD-2-Clause | https://pypi.org/project/packaging | python-packaging/LICENSE.APACHE, python-packaging/LICENSE.BSD, python-packaging/LICENSE |
| pillow (Python package) | 13.0.0 | MIT-CMU | https://pypi.org/project/pillow | python-pillow/LICENSE |
| propcache (Python package) | 0.5.4 | Apache-2.0 | https://pypi.org/project/propcache | python-propcache/LICENSE |
| pycares (Python package) | 5.2.1 | MIT | https://pypi.org/project/pycares | python-pycares/LICENSE |
| pycparser (Python package) | 3.12 | BSD-3-Clause | https://pypi.org/project/pycparser | python-pycparser/LICENSE |
| pyudev (Python package) | 0.24.5 | LGPL-2.1-or-later | https://pypi.org/project/pyudev | python-pyudev/COPYING |
| PyYAML (Python package) | 6.0.3 | MIT | https://pypi.org/project/PyYAML | python-PyYAML/LICENSE |
| qrcode (Python package) | 8.2 | BSD | https://pypi.org/project/qrcode | python-qrcode/LICENSE |
| ruamel.yaml (Python package) | 0.19.1 | MIT | https://pypi.org/project/ruamel.yaml | python-ruamel.yaml/LICENSE |
| toml (Python package) | 0.10.2 | MIT | https://pypi.org/project/toml | python-toml/LICENSE |
| typing_extensions (Python package) | 4.16.0 | PSF-2.0 | https://pypi.org/project/typing_extensions | python-typing_extensions/LICENSE |
| uvloop (Python package) | 0.23.0 | MIT License | https://pypi.org/project/uvloop | python-uvloop/LICENSE-APACHE, python-uvloop/LICENSE-MIT |
| yarl (Python package) | 1.25.1 | Apache-2.0 | https://pypi.org/project/yarl | python-yarl/LICENSE |
| liba52-0.7.4 (liba52-0.7.4.so) | 0.7.4-20 | see Debian copyright file | Ubuntu 22.04 package liba52-0.7.4 | ubuntu-liba52-0.7.4/copyright |
| libapparmor1 (libapparmor.so.1) | 3.0.4-2ubuntu2.5 | see Debian copyright file | Ubuntu 22.04 package libapparmor1 | ubuntu-libapparmor1/copyright |
| libaribb24-0 (libaribb24.so.0) | 1.0.3-2 | see Debian copyright file | Ubuntu 22.04 package libaribb24-0 | ubuntu-libaribb24-0/copyright |
| libasyncns0 (libasyncns.so.0) | 0.8-6build2 | see Debian copyright file | Ubuntu 22.04 package libasyncns0 | ubuntu-libasyncns0/copyright |
| libbluetooth3 (libbluetooth.so.3) | 5.64-0ubuntu1.6 | see Debian copyright file | Ubuntu 22.04 package libbluetooth3 | ubuntu-libbluetooth3/copyright |
| libbrotli1 (libbrotlicommon.so.1, libbrotlidec.so.1) | 1.0.9-2ubuntu0.1 | see Debian copyright file | Ubuntu 22.04 package libbrotli1 | ubuntu-libbrotli1/copyright |
| libbsd0 (libbsd.so.0) | 0.11.5-1 | see Debian copyright file | Ubuntu 22.04 package libbsd0 | ubuntu-libbsd0/copyright |
| libcairo2 (libcairo.so.2) | 1.16.0-5ubuntu2.1 | see Debian copyright file | Ubuntu 22.04 package libcairo2 | ubuntu-libcairo2/copyright |
| libcap2 (libcap.so.2) | 1:2.44-1ubuntu0.22.04.3 | see Debian copyright file | Ubuntu 22.04 package libcap2 | ubuntu-libcap2/copyright |
| libcom-err2 (libcom_err.so.2) | 1.46.5-2ubuntu1.2 | see Debian copyright file | Ubuntu 22.04 package libcom-err2 | ubuntu-libcom-err2/copyright |
| libcurl4 (libcurl.so.4) | 7.81.0-1ubuntu1.30 | see Debian copyright file | Ubuntu 22.04 package libcurl4 | ubuntu-libcurl4/copyright |
| libdb5.3 (libdb-5.3.so) | 5.3.28+dfsg1-0.8ubuntu3 | see Debian copyright file | Ubuntu 22.04 package libdb5.3 | ubuntu-libdb5.3/copyright |
| libdeflate0 (libdeflate.so.0) | 1.10-2 | see Debian copyright file | Ubuntu 22.04 package libdeflate0 | ubuntu-libdeflate0/copyright |
| libdvbpsi10 (libdvbpsi.so.10) | 1.3.3-1 | see Debian copyright file | Ubuntu 22.04 package libdvbpsi10 | ubuntu-libdvbpsi10/copyright |
| libebml5 (libebml.so.5) | 1.4.2-2 | see Debian copyright file | Ubuntu 22.04 package libebml5 | ubuntu-libebml5/copyright |
| libffi8 (libffi.so.8) | 3.4.2-4 | see Debian copyright file | Ubuntu 22.04 package libffi8 | ubuntu-libffi8/copyright |
| libflac8 (libFLAC.so.8) | 1.3.3-2ubuntu0.2 | see Debian copyright file | Ubuntu 22.04 package libflac8 | ubuntu-libflac8/copyright |
| libfreeimage3 (libfreeimage.so.3) | 3.18.0+ds2-6ubuntu5.1 | see Debian copyright file | Ubuntu 22.04 package libfreeimage3 | ubuntu-libfreeimage3/copyright |
| libfreetype6 (libfreetype.so.6) | 2.11.1+dfsg-1ubuntu0.4 | see Debian copyright file | Ubuntu 22.04 package libfreetype6 | ubuntu-libfreetype6/copyright |
| libfribidi0 (libfribidi.so.0) | 1.0.8-2ubuntu3.1 | see Debian copyright file | Ubuntu 22.04 package libfribidi0 | ubuntu-libfribidi0/copyright |
| libgcrypt20 (libgcrypt.so.20) | 1.9.4-3ubuntu3.3 | see Debian copyright file | Ubuntu 22.04 package libgcrypt20 | ubuntu-libgcrypt20/copyright |
| libglew2.2 (libGLEW.so.2.2) | 2.2.0-4 | see Debian copyright file | Ubuntu 22.04 package libglew2.2 | ubuntu-libglew2.2/copyright |
| libgmp10 (libgmp.so.10) | 2:6.2.1+dfsg-3ubuntu1 | see Debian copyright file | Ubuntu 22.04 package libgmp10 | ubuntu-libgmp10/copyright |
| libgnutls30 (libgnutls.so.30) | 3.7.3-4ubuntu1.9 | see Debian copyright file | Ubuntu 22.04 package libgnutls30 | ubuntu-libgnutls30/copyright |
| libgomp1 (libgomp.so.1) | 12.3.0-1ubuntu1~22.04.3 | see Debian copyright file | Ubuntu 22.04 package libgomp1 | ubuntu-libgomp1/copyright |
| libgpg-error0 (libgpg-error.so.0) | 1.43-3 | see Debian copyright file | Ubuntu 22.04 package libgpg-error0 | ubuntu-libgpg-error0/copyright |
| libgssapi-krb5-2 (libgssapi_krb5.so.2) | 1.19.2-2ubuntu0.10 | see Debian copyright file | Ubuntu 22.04 package libgssapi-krb5-2 | ubuntu-libgssapi-krb5-2/copyright |
| libhogweed6 (libhogweed.so.6) | 3.7.3-1build2 | see Debian copyright file | Ubuntu 22.04 package libhogweed6 | ubuntu-libhogweed6/copyright |
| libidn12 (libidn.so.12) | 1.38-4ubuntu1.1 | see Debian copyright file | Ubuntu 22.04 package libidn12 | ubuntu-libidn12/copyright |
| libidn2-0 (libidn2.so.0) | 2.3.2-2build1 | see Debian copyright file | Ubuntu 22.04 package libidn2-0 | ubuntu-libidn2-0/copyright |
| libilmbase25 (libHalf-2_5.so.25, libIex-2_5.so.25, libIlmThread-2_5.so.25, libImath-2_5.so.25) | 2.5.7-2 | see Debian copyright file | Ubuntu 22.04 package libilmbase25 | ubuntu-libilmbase25/copyright |
| libjack0 (libjack.so.0) | 1:0.125.0-3build2 | see Debian copyright file | Ubuntu 22.04 package libjack0 | ubuntu-libjack0/copyright |
| libjbig0 (libjbig.so.0) | 2.1-3.1ubuntu0.22.04.1 | see Debian copyright file | Ubuntu 22.04 package libjbig0 | ubuntu-libjbig0/copyright |
| libjpeg-turbo8 (libjpeg.so.8) | 2.1.2-0ubuntu1 | see Debian copyright file | Ubuntu 22.04 package libjpeg-turbo8 | ubuntu-libjpeg-turbo8/copyright |
| libjxr0 (libjpegxr.so.0, libjxrglue.so.0) | 1.2~git20170615.f752187-5 | see Debian copyright file | Ubuntu 22.04 package libjxr0 | ubuntu-libjxr0/copyright |
| libk5crypto3 (libk5crypto.so.3) | 1.19.2-2ubuntu0.10 | see Debian copyright file | Ubuntu 22.04 package libk5crypto3 | ubuntu-libk5crypto3/copyright |
| libkeyutils1 (libkeyutils.so.1) | 1.6.1-2ubuntu3 | see Debian copyright file | Ubuntu 22.04 package libkeyutils1 | ubuntu-libkeyutils1/copyright |
| libkrb5-3 (libkrb5.so.3) | 1.19.2-2ubuntu0.10 | see Debian copyright file | Ubuntu 22.04 package libkrb5-3 | ubuntu-libkrb5-3/copyright |
| libkrb5support0 (libkrb5support.so.0) | 1.19.2-2ubuntu0.10 | see Debian copyright file | Ubuntu 22.04 package libkrb5support0 | ubuntu-libkrb5support0/copyright |
| liblcms2-2 (liblcms2.so.2) | 2.12~rc1-2ubuntu0.1 | see Debian copyright file | Ubuntu 22.04 package liblcms2-2 | ubuntu-liblcms2-2/copyright |
| libldap-2.5-0 (liblber-2.5.so.0, libldap-2.5.so.0) | 2.5.20+dfsg-0ubuntu0.22.04.1 | see Debian copyright file | Ubuntu 22.04 package libldap-2.5-0 | ubuntu-libldap-2.5-0/copyright |
| liblz4-1 (liblz4.so.1) | 1.9.3-2build2 | see Debian copyright file | Ubuntu 22.04 package liblz4-1 | ubuntu-liblz4-1/copyright |
| liblzma5 (liblzma.so.5) | 5.2.5-2ubuntu1.2 | see Debian copyright file | Ubuntu 22.04 package liblzma5 | ubuntu-liblzma5/copyright |
| libmad0 (libmad.so.0) | 0.15.1b-10ubuntu1 | see Debian copyright file | Ubuntu 22.04 package libmad0 | ubuntu-libmad0/copyright |
| libmatroska7 (libmatroska.so.7) | 1.6.3-2 | see Debian copyright file | Ubuntu 22.04 package libmatroska7 | ubuntu-libmatroska7/copyright |
| libmd0 (libmd.so.0) | 1.0.4-1build1 | see Debian copyright file | Ubuntu 22.04 package libmd0 | ubuntu-libmd0/copyright |
| libmpcdec6 (libmpcdec.so.6) | 2:0.1~r495-2 | see Debian copyright file | Ubuntu 22.04 package libmpcdec6 | ubuntu-libmpcdec6/copyright |
| libmpg123-0 (libmpg123.so.0) | 1.29.3-1ubuntu0.1 | see Debian copyright file | Ubuntu 22.04 package libmpg123-0 | ubuntu-libmpg123-0/copyright |
| libmysofa1 (libmysofa.so.1) | 1.2.1~dfsg0-1 | see Debian copyright file | Ubuntu 22.04 package libmysofa1 | ubuntu-libmysofa1/copyright |
| libnettle8 (libnettle.so.8) | 3.7.3-1build2 | see Debian copyright file | Ubuntu 22.04 package libnettle8 | ubuntu-libnettle8/copyright |
| libnghttp2-14 (libnghttp2.so.14) | 1.43.0-1ubuntu0.4 | see Debian copyright file | Ubuntu 22.04 package libnghttp2-14 | ubuntu-libnghttp2-14/copyright |
| libogg0 (libogg.so.0) | 1.3.5-0ubuntu3 | see Debian copyright file | Ubuntu 22.04 package libogg0 | ubuntu-libogg0/copyright |
| libopenexr25 (libIlmImf-2_5.so.25) | 2.5.7-1 | see Debian copyright file | Ubuntu 22.04 package libopenexr25 | ubuntu-libopenexr25/copyright |
| libopenjp2-7 (libopenjp2.so.7) | 2.4.0-6ubuntu0.5 | see Debian copyright file | Ubuntu 22.04 package libopenjp2-7 | ubuntu-libopenjp2-7/copyright |
| libopus0 (libopus.so.0) | 1.3.1-0.1build2 | see Debian copyright file | Ubuntu 22.04 package libopus0 | ubuntu-libopus0/copyright |
| libp11-kit0 (libp11-kit.so.0) | 0.24.0-6ubuntu0.1 | see Debian copyright file | Ubuntu 22.04 package libp11-kit0 | ubuntu-libp11-kit0/copyright |
| libpixman-1-0 (libpixman-1.so.0) | 0.40.0-1ubuntu0.22.04.1 | see Debian copyright file | Ubuntu 22.04 package libpixman-1-0 | ubuntu-libpixman-1-0/copyright |
| libpng16-16 (libpng16.so.16) | 1.6.37-3ubuntu0.7 | see Debian copyright file | Ubuntu 22.04 package libpng16-16 | ubuntu-libpng16-16/copyright |
| libpsl5 (libpsl.so.5) | 0.21.0-1.2build2 | see Debian copyright file | Ubuntu 22.04 package libpsl5 | ubuntu-libpsl5/copyright |
| libraw20 (libraw.so.20) | 0.20.2-2ubuntu2.22.04.3 | see Debian copyright file | Ubuntu 22.04 package libraw20 | ubuntu-libraw20/copyright |
| librtmp1 (librtmp.so.1) | 2.4+20151223.gitfa8646d.1-2build4 | see Debian copyright file | Ubuntu 22.04 package librtmp1 | ubuntu-librtmp1/copyright |
| libsamplerate0 (libsamplerate.so.0) | 0.2.2-1build1 | see Debian copyright file | Ubuntu 22.04 package libsamplerate0 | ubuntu-libsamplerate0/copyright |
| libsasl2-2 (libsasl2.so.2) | 2.1.27+dfsg2-3ubuntu1.2 | see Debian copyright file | Ubuntu 22.04 package libsasl2-2 | ubuntu-libsasl2-2/copyright |
| libsndfile1 (libsndfile.so.1) | 1.0.31-2ubuntu0.2 | see Debian copyright file | Ubuntu 22.04 package libsndfile1 | ubuntu-libsndfile1/copyright |
| libsndio7.0 (libsndio.so.7) | 1.8.1-1.1 | see Debian copyright file | Ubuntu 22.04 package libsndio7.0 | ubuntu-libsndio7.0/copyright |
| libsoxr0 (libsoxr.so.0) | 0.1.3-4build2 | see Debian copyright file | Ubuntu 22.04 package libsoxr0 | ubuntu-libsoxr0/copyright |
| libspatialaudio0 (libspatialaudio.so.0) | 0.3.0+git20180730+dfsg1-2build1 | see Debian copyright file | Ubuntu 22.04 package libspatialaudio0 | ubuntu-libspatialaudio0/copyright |
| libspeexdsp1 (libspeexdsp.so.1) | 1.2~rc1.2-1.1ubuntu3 | see Debian copyright file | Ubuntu 22.04 package libspeexdsp1 | ubuntu-libspeexdsp1/copyright |
| libssh-4 (libssh.so.4) | 0.9.6-2ubuntu0.22.04.8 | see Debian copyright file | Ubuntu 22.04 package libssh-4 | ubuntu-libssh-4/copyright |
| libssl3 (libcrypto.so.3, libssl.so.3) | 3.0.2-0ubuntu1.30 | see Debian copyright file | Ubuntu 22.04 package libssl3 | ubuntu-libssl3/copyright |
| libtasn1-6 (libtasn1.so.6) | 4.18.0-4ubuntu0.2 | see Debian copyright file | Ubuntu 22.04 package libtasn1-6 | ubuntu-libtasn1-6/copyright |
| libtheora0 (libtheoradec.so.1, libtheoraenc.so.1) | 1.1.1+dfsg.1-15ubuntu4 | see Debian copyright file | Ubuntu 22.04 package libtheora0 | ubuntu-libtheora0/copyright |
| libtiff5 (libtiff.so.5) | 4.3.0-6ubuntu0.13 | see Debian copyright file | Ubuntu 22.04 package libtiff5 | ubuntu-libtiff5/copyright |
| libunistring2 (libunistring.so.2) | 1.0-1 | see Debian copyright file | Ubuntu 22.04 package libunistring2 | ubuntu-libunistring2/copyright |
| libusb-1.0-0 (libusb-1.0.so.0) | 2:1.0.25-1ubuntu2 | see Debian copyright file | Ubuntu 22.04 package libusb-1.0-0 | ubuntu-libusb-1.0-0/copyright |
| libuuid1 (libuuid.so.1) | 2.37.2-4ubuntu3.6 | see Debian copyright file | Ubuntu 22.04 package libuuid1 | ubuntu-libuuid1/copyright |
| libvlc-bin (VLC plugins) | 3.0.16-1build7 | see Debian copyright file | Ubuntu 22.04 package libvlc-bin | ubuntu-libvlc-bin/copyright |
| libvlc5 (libvlc.so.5) | 3.0.16-1build7 | see Debian copyright file | Ubuntu 22.04 package libvlc5 | ubuntu-libvlc5/copyright |
| libvlccore9 (libvlccore.so.9) | 3.0.16-1build7 | see Debian copyright file | Ubuntu 22.04 package libvlccore9 | ubuntu-libvlccore9/copyright |
| libvorbis0a (libvorbis.so.0) | 1.3.7-1build2 | see Debian copyright file | Ubuntu 22.04 package libvorbis0a | ubuntu-libvorbis0a/copyright |
| libvorbisenc2 (libvorbisenc.so.2) | 1.3.7-1build2 | see Debian copyright file | Ubuntu 22.04 package libvorbisenc2 | ubuntu-libvorbisenc2/copyright |
| libwebp7 (libwebp.so.7) | 1.2.2-2ubuntu0.22.04.2 | see Debian copyright file | Ubuntu 22.04 package libwebp7 | ubuntu-libwebp7/copyright |
| libwebpmux3 (libwebpmux.so.3) | 1.2.2-2ubuntu0.22.04.2 | see Debian copyright file | Ubuntu 22.04 package libwebpmux3 | ubuntu-libwebpmux3/copyright |
| libxinerama1 (libXinerama.so.1) | 2:1.1.4-3 | see Debian copyright file | Ubuntu 22.04 package libxinerama1 | ubuntu-libxinerama1/copyright |
| libxkbcommon0 (libxkbcommon.so.0) | 1.4.0-1 | see Debian copyright file | Ubuntu 22.04 package libxkbcommon0 | ubuntu-libxkbcommon0/copyright |
| libxrandr2 (libXrandr.so.2) | 2:1.5.2-1build1 | see Debian copyright file | Ubuntu 22.04 package libxrandr2 | ubuntu-libxrandr2/copyright |
| libxss1 (libXss.so.1) | 1:1.2.3-1build2 | see Debian copyright file | Ubuntu 22.04 package libxss1 | ubuntu-libxss1/copyright |
| libxxf86vm1 (libXxf86vm.so.1) | 1:1.1.4-1build3 | see Debian copyright file | Ubuntu 22.04 package libxxf86vm1 | ubuntu-libxxf86vm1/copyright |
| libzstd1 (libzstd.so.1) | 1.4.8+dfsg-3build1 | see Debian copyright file | Ubuntu 22.04 package libzstd1 | ubuntu-libzstd1/copyright |
| vlc-plugin-base (libvlc_pulse.so.0, VLC plugins) | 3.0.16-1build7 | see Debian copyright file | Ubuntu 22.04 package vlc-plugin-base | ubuntu-vlc-plugin-base/copyright |
| zlib1g (libz.so.1) | 1:1.2.11.dfsg-2ubuntu9.2 | see Debian copyright file | Ubuntu 22.04 package zlib1g | ubuntu-zlib1g/copyright |
