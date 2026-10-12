#!/usr/bin/env bash
# Trim a local file. fast = keyframe copy. accurate = re-encode.
# Usage: scripts/trim.sh <input> <start> <end> [fast|accurate] [output]
set -euo pipefail

INPUT="${1:?usage: trim.sh <input> <start> <end> [fast|accurate] [output]}"
START="${2:?usage: trim.sh <input> <start> <end> [fast|accurate] [output]}"
END="${3:?usage: trim.sh <input> <start> <end> [fast|accurate] [output]}"
MODE="${4:-fast}"
OUT_DIR="${MEDIA_OUTPUT_DIR:-./output}"
mkdir -p "$OUT_DIR"
OUTPUT="${5:-${OUT_DIR}/$(basename "${INPUT%.*}")_${MODE}.mp4}"

case "$START" in
  ''|*[!0-9:.]*) printf 'start must look like seconds or HH:MM:SS\n' >&2; exit 2 ;;
esac
case "$END" in
  ''|*[!0-9:.]*) printf 'end must look like seconds or HH:MM:SS\n' >&2; exit 2 ;;
esac
case "$MODE" in
  fast|accurate) ;;
  *) printf 'mode must be fast or accurate\n' >&2; exit 2 ;;
esac
if [ ! -f "$INPUT" ]; then
  printf 'input not found: %s\n' "$INPUT" >&2
  exit 1
fi
if [ -e "$OUTPUT" ]; then
  printf 'refusing to overwrite %s\n' "$OUTPUT" >&2
  exit 1
fi

if [ "$MODE" = "fast" ]; then
  # -ss before -i seeks to the previous keyframe. Cuts are instant and inexact.
  ffmpeg -nostdin -y -ss "$START" -to "$END" -i "$INPUT" -c copy "$OUTPUT"
else
  # Decode first, then cut, so the boundaries follow the requested timestamps.
  ffmpeg -nostdin -y -i "$INPUT" -ss "$START" -to "$END" \
    -c:v libx264 -crf 18 -preset veryfast -pix_fmt yuv420p \
    -c:a aac -b:a 128k \
    "$OUTPUT"
fi

printf 'trimmed (%s): %s\n' "$MODE" "$OUTPUT"
ls -lh "$OUTPUT"
