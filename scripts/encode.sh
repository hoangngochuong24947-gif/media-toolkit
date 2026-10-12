#!/usr/bin/env bash
# Encode with a hardware encoder when it actually runs, else libx264/libx265.
# Listing an encoder in `ffmpeg -encoders` is not proof the GPU is usable.
# Usage: scripts/encode.sh <input> [output] [h264|h265]
set -euo pipefail

INPUT="${1:?usage: encode.sh <input> [output] [h264|h265]}"
OUT_DIR="${MEDIA_OUTPUT_DIR:-./output}"
mkdir -p "$OUT_DIR"
OUTPUT="${2:-${OUT_DIR}/$(basename "${INPUT%.*}").encoded.mp4}"
CODEC="${3:-h264}"

case "$CODEC" in
  h264) SW="libx264" ;;
  h265|hevc) SW="libx265" ;;
  *) printf 'codec must be h264 or h265\n' >&2; exit 2 ;;
esac
if [ ! -f "$INPUT" ]; then
  printf 'input not found: %s\n' "$INPUT" >&2
  exit 1
fi
if [ -e "$OUTPUT" ]; then
  printf 'refusing to overwrite %s\n' "$OUTPUT" >&2
  exit 1
fi

ENCODERS="$(ffmpeg -hide_banner -encoders 2>/dev/null || true)"
has_enc() {
  printf '%s\n' "$ENCODERS" | grep -q -F " ${1} "
}

try_encode() {
  name="$1"
  shift
  printf 'encode: trying %s\n' "$name" >&2
  if ffmpeg -nostdin -y -v error -i "$INPUT" "$@" "$OUTPUT"; then
    printf 'encode: using %s\n' "$name" >&2
    return 0
  fi
  rm -f "$OUTPUT"
  printf 'encode: %s failed; falling back\n' "$name" >&2
  return 1
}

scale='scale=trunc(iw/2)*2:trunc(ih/2)*2'
audio=(-c:a aac -b:a 128k)

if [ "$CODEC" = "h264" ]; then
  if has_enc h264_videotoolbox; then
    try_encode h264_videotoolbox -vf "$scale" -c:v h264_videotoolbox -b:v 2000k -pix_fmt yuv420p "${audio[@]}" && exit 0
  fi
  if has_enc h264_nvenc; then
    try_encode h264_nvenc -vf "$scale" -c:v h264_nvenc -preset p4 -cq 24 -pix_fmt yuv420p "${audio[@]}" && exit 0
  fi
  if has_enc h264_qsv; then
    try_encode h264_qsv -vf "$scale" -c:v h264_qsv -global_quality 24 -pix_fmt nv12 "${audio[@]}" && exit 0
  fi
  if has_enc h264_vaapi && [ -e /dev/dri/renderD128 ]; then
    try_encode h264_vaapi -vaapi_device /dev/dri/renderD128 -vf "${scale},format=nv12,hwupload" -c:v h264_vaapi -qp 24 "${audio[@]}" && exit 0
  fi
else
  if has_enc hevc_videotoolbox; then
    try_encode hevc_videotoolbox -vf "$scale" -c:v hevc_videotoolbox -b:v 1500k -tag:v hvc1 -pix_fmt yuv420p "${audio[@]}" && exit 0
  fi
  if has_enc hevc_nvenc; then
    try_encode hevc_nvenc -vf "$scale" -c:v hevc_nvenc -preset p4 -cq 26 -pix_fmt yuv420p "${audio[@]}" && exit 0
  fi
  if has_enc hevc_qsv; then
    try_encode hevc_qsv -vf "$scale" -c:v hevc_qsv -global_quality 26 -pix_fmt nv12 "${audio[@]}" && exit 0
  fi
  if has_enc hevc_vaapi && [ -e /dev/dri/renderD128 ]; then
    try_encode hevc_vaapi -vaapi_device /dev/dri/renderD128 -vf "${scale},format=nv12,hwupload" -c:v hevc_vaapi -qp 26 "${audio[@]}" && exit 0
  fi
fi

if ! has_enc "$SW"; then
  printf 'software encoder %s is not listed by ffmpeg -encoders\n' "$SW" >&2
  exit 1
fi
try_encode "$SW" -vf "$scale" -c:v "$SW" -crf 23 -preset veryfast -pix_fmt yuv420p "${audio[@]}"
