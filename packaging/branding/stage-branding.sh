#!/usr/bin/env bash
# Put AcroBato branding into an AppDir: splash/logo images (ES resources and the
# Carbon theme's splash), app icon, version. Usage: stage-branding.sh <AppDir>
set -euo pipefail
B="$(cd "$(dirname "$0")" && pwd)"
A="$1"
VERSION="$(cat "$B/VERSION")"

# SVG wrapper around the PNG logo, so files ES/the theme expect as .svg keep their names
python3 - "$B/splash-square.png" "$B/logo.svg" <<'EOF'
import base64, struct, sys
png = open(sys.argv[1], 'rb').read()
w, h = struct.unpack('>II', png[16:24])
data = base64.b64encode(png).decode()
open(sys.argv[2], 'w').write(
    f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
    f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
    f'<image width="{w}" height="{h}" xlink:href="data:image/png;base64,{data}"/></svg>\n')
EOF

R="$A/usr/share/emulationstation/resources"
cp "$B/logo.svg" "$R/splash.svg"
cp "$B/logo.svg" "$R/splash_batocera.svg"
cp "$B/splash-1080.png" "$R/logo.png"   # full-screen image ES shows while a game launches
T="$A/usr/share/emulationstation/themes/es-theme-carbon/art"
[ -d "$T" ] && cp "$B/logo.svg" "$T/splash_batocera.svg"

cp "$B/icon.png" "$A/acrobato.png"
ln -sf acrobato.png "$A/.DirIcon"
mkdir -p "$A/usr/share/acrobato"; echo "$VERSION" > "$A/usr/share/acrobato/version"
echo "branding staged (AcroBato $VERSION)"
