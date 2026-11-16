# Theme

AcroBato bundles **Carbon-PixN**, Pixel Nostalgia's version of the Carbon theme for
EmulationStation: https://github.com/PixelNostalgia/Carbon-PixN, **GPL-3.0** (its `LICENSE`
ships with it). `scripts/build-appdir.sh` installs it under Carbon's name (`es-theme-carbon`)
at a pinned commit (`CARBON_REV`), then:

- removes the art Pixel Nostalgia made for its own build (`pixn*` logos and backgrounds)
- removes its `arcadepc` logos (they show another project's name, NOTParrot)
- copies this folder's `es-theme-carbon/` over it (below)
- trims the per-system art to AcroBato's systems (`scripts/prune-theme.py`)

The system logos are trademarks of their owners.

## AcroBato's additions (`es-theme-carbon/art/logos/`)

Systems Carbon-PixN has no logo for, made by `make-logos.py` from Carbon's own art and font
(Cabin Bold, SIL Open Font License): `segashell`, `apm3`, `tsunami`, `arcadepc`.

`segaalls-w.svg`: a white version of Carbon-PixN's `segaalls.svg` (its black letters and
subtitle made white) for the dark views.
