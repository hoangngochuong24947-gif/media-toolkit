#!/usr/bin/env bash
# Convert one image with ImageMagick 7 (magick) or 6 (convert).
# Usage: scripts/image-convert.sh <input> [output] [max-side] [quality]
set -euo pipefail

INPUT="${1:?usage: image-convert.sh <input> [output] [max-side] [quality]}"
OUT_DIR="${MEDIA_OUTPUT_DIR:-./output}"
mkdir -p "$OUT_DIR"
OUTPUT="${2:-${OUT_DIR}/$(basename "${INPUT%.*}").jpg}"
MAX_SIDE="${3:-1920}"
QUALITY="${4:-82}"

case "$MAX_SIDE" in
  ''|*[!0-9]*) printf 'max-side must be an integer\n' >&2; exit 2 ;;
esac
case "$QUALITY" in
  ''|*[!0-9]*) printf 'quality must be an integer\n' >&2; exit 2 ;;
esac
if [ ! -f "$INPUT" ]; then
  printf 'input not found: %s\n' "$INPUT" >&2
  exit 1
fi
if [ -e "$OUTPUT" ]; then
  printf 'refusing to overwrite %s\n' "$OUTPUT" >&2
  exit 1
fi

if command -v magick >/dev/null 2>&1; then
  IM="magick"
elif command -v convert >/dev/null 2>&1; then
  IM="convert"
else
  printf 'neither magick nor convert is on PATH\n' >&2
  exit 1
fi

printf 'imagemagick: %s\n' "$IM"
"$IM" "$INPUT" -auto-orient -resize "${MAX_SIDE}x${MAX_SIDE}>" -strip -quality "$QUALITY" "$OUTPUT"
printf 'image: %s\n' "$OUTPUT"
ls -lh "$OUTPUT"
