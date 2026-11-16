#!/usr/bin/env bash
# Minimal FFmpeg 4.4 (same sonames as Ubuntu 22.04's: libavcodec.so.58 etc.)
# so VLC's plugins load it instead of Ubuntu's build, which links ~100 MB of
# extra codec libraries (x265, aom, codec2, librsvg+ICU, ...).
# Only decoders/demuxers used by theme video previews are enabled, plus ffprobe (Batocera's
# Hypseus Singe launcher reads laserdisc videos' size with it; Batocera OS ships it).
# Run inside the "esbuild" distrobox. Installs into $WORK/deps/ffmpeg.
set -euo pipefail
WORK="${WORK:-$HOME/rbl}"
SRC="$WORK/deps/src/ffmpeg"
OUT="$WORK/deps/ffmpeg"
[ -f "$OUT/lib/libavcodec.so.58" ] && [ -x "$OUT/bin/ffprobe" ] && { echo "ffmpeg-min already built"; exit 0; }
command -v nasm >/dev/null || sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nasm
[ -d "$SRC" ] || git clone -q --depth 1 -b n4.4.2 https://git.ffmpeg.org/ffmpeg.git "$SRC"
cd "$SRC"
./configure --prefix="$OUT" --enable-shared --disable-static --disable-ffmpeg --disable-ffplay --enable-ffprobe --disable-doc \
  --disable-everything --disable-autodetect --disable-network --disable-avdevice --disable-avfilter \
  --disable-postproc --enable-swscale --enable-swresample --enable-protocol=file \
  --enable-decoder=h264,hevc,mpeg4,mpeg2video,mpeg1video,vp8,vp9,av1,theora,mjpeg,aac,mp3,mp2,vorbis,opus,flac,ac3,pcm_s16le,pcm_s24le,pcm_f32le \
  --enable-demuxer=mov,matroska,webm_dash_manifest,avi,mpegps,mpegts,mpegvideo,ogg,mp3,aac,flac,wav \
  --enable-parser=h264,hevc,mpeg4video,mpegvideo,vp8,vp9,av1,aac,mpegaudio,vorbis,opus,flac,ac3 \
  --enable-bsf=h264_mp4toannexb,hevc_mp4toannexb,aac_adtstoasc >/dev/null
make -j"$(nproc)" >/dev/null
make install >/dev/null
ls "$OUT/lib"/*.so.*
