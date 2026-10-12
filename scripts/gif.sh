#!/usr/bin/env bash
# High-quality GIF: palettegen + paletteuse. Optional convenience, not required.
# Usage: scripts/gif.sh <input> [output] [fps] [width]
set -euo pipefail

INPUT="${1:?usage: gif.sh <input> [output] [fps] [width]}"
OUT_DIR="${MEDIA_OUTPUT_DIR:-./output}"
mkdir -p "$OUT_DIR"
OUTPUT="${2:-${OUT_DIR}/$(basename "${INPUT%.*}").gif}"
FPS="${3:-15}"
WIDTH="${4:-1080}"

case "$FPS" in
  ''|*[!0-9.]*) printf 'fps must be a number\n' >&2; exit 2 ;;
esac
case "$WIDTH" in
  ''|*[!0-9]*) printf 'width must be an integer\n' >&2; exit 2 ;;
esac
if [ ! -f "$INPUT" ]; then
  printf 'input not found: %s\n' "$INPUT" >&2
  exit 1
fi
if [ -e "$OUTPUT" ]; then
  printf 'refusing to overwrite %s\n' "$OUTPUT" >&2
  exit 1
fi

PALETTE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/palette_XXXXXX")"
PALETTE="${PALETTE_DIR}/palette.png"
trap 'rm -rf "$PALETTE_DIR"' EXIT

# -update 1 writes the single palette frame. Without it, image2 may skip the file.
ffmpeg -nostdin -y -v warning -i "$INPUT" \
  -vf "fps=${FPS},scale=${WIDTH}:-1:flags=lanczos,palettegen=stats_mode=diff" \
  -frames:v 1 -update 1 \
  "$PALETTE"

ffmpeg -nostdin -y -v warning -i "$INPUT" -i "$PALETTE" \
  -filter_complex "fps=${FPS},scale=${WIDTH}:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
  -an \
  "$OUTPUT"

printf 'gif: %s\n' "$OUTPUT"
ls -lh "$OUTPUT"
