#!/usr/bin/env bash
# Two-pass H.264 encode aimed at a size budget. Uses awk, not bc.
# Usage: scripts/compress-target-size.sh <input> <target_mb> [output]
set -euo pipefail

INPUT="${1:?usage: compress-target-size.sh <input> <target_mb> [output]}"
TARGET_MB="${2:?usage: compress-target-size.sh <input> <target_mb> [output]}"
OUT_DIR="${MEDIA_OUTPUT_DIR:-./output}"
mkdir -p "$OUT_DIR"
OUTPUT="${3:-${OUT_DIR}/$(basename "${INPUT%.*}")_${TARGET_MB}mb.mp4}"

case "$TARGET_MB" in
  ''|*[!0-9.]*) printf 'target_mb must be a positive number\n' >&2; exit 2 ;;
esac
if [ ! -f "$INPUT" ]; then
  printf 'input not found: %s\n' "$INPUT" >&2
  exit 1
fi
if [ -e "$OUTPUT" ]; then
  printf 'refusing to overwrite %s\n' "$OUTPUT" >&2
  exit 1
fi

export LC_ALL=C
DURATION="$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$INPUT")"
if ! awk -v d="$DURATION" 'BEGIN { exit (d+0 > 0 ? 0 : 1) }'; then
  printf 'unable to read a positive duration from %s\n' "$INPUT" >&2
  exit 1
fi

# 95% of the request leaves room for container overhead.
# kbps = mebibytes * 8192 / seconds. See references/ffmpeg.md.
BUDGET_MB="$(awk -v mb="$TARGET_MB" 'BEGIN { printf "%.4f", mb * 0.95 }')"
AUDIO_K=96
TOTAL_K="$(awk -v mb="$BUDGET_MB" -v dur="$DURATION" 'BEGIN { printf "%d", (mb * 8192) / dur }')"
VIDEO_K="$(awk -v total="$TOTAL_K" -v audio="$AUDIO_K" 'BEGIN { v = total - audio; if (v < 1) v = 0; printf "%d", v }')"
if awk -v v="$VIDEO_K" 'BEGIN { exit (v > 64 ? 0 : 1) }'; then
  :
else
  printf 'target is too small for this duration; video bitrate floored at 64 kbps\n' >&2
  VIDEO_K=64
fi

printf 'duration=%ss budget=%sMiB video=%sk audio=%sk\n' "$DURATION" "$BUDGET_MB" "$VIDEO_K" "$AUDIO_K"

PASSLOG="$(mktemp "${TMPDIR:-/tmp}/ffmpeg2pass_XXXXXX")"
rm -f "$PASSLOG"
trap 'rm -f "${PASSLOG}" "${PASSLOG}"-*.log "${PASSLOG}"*.log' EXIT

ffmpeg -nostdin -y -v warning -i "$INPUT" \
  -c:v libx264 -b:v "${VIDEO_K}k" -pass 1 -passlogfile "$PASSLOG" \
  -an -f null -
ffmpeg -nostdin -y -v warning -i "$INPUT" \
  -c:v libx264 -b:v "${VIDEO_K}k" -pass 2 -passlogfile "$PASSLOG" \
  -pix_fmt yuv420p -c:a aac -b:a "${AUDIO_K}k" \
  "$OUTPUT"

printf 'compressed: %s\n' "$OUTPUT"
ls -lh "$OUTPUT"
