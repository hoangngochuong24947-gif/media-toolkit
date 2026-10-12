#!/usr/bin/env bash
# Encode the audio track to MP3 (libmp3lame). Matches the skill default.
# Usage: scripts/audio-extract.sh <input> [output]
set -euo pipefail

INPUT="${1:?usage: audio-extract.sh <input> [output]}"
OUT_DIR="${MEDIA_OUTPUT_DIR:-./output}"
mkdir -p "$OUT_DIR"
OUTPUT="${2:-${OUT_DIR}/$(basename "${INPUT%.*}").mp3}"

if [ ! -f "$INPUT" ]; then
  printf 'input not found: %s\n' "$INPUT" >&2
  exit 1
fi
if [ -e "$OUTPUT" ]; then
  printf 'refusing to overwrite %s\n' "$OUTPUT" >&2
  exit 1
fi

ffmpeg -nostdin -y -v warning -i "$INPUT" -vn -c:a libmp3lame -q:a 2 "$OUTPUT"
printf 'audio: %s\n' "$OUTPUT"
ls -lh "$OUTPUT"
