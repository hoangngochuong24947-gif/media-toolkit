#!/usr/bin/env bash
# Local ASR plan. Does no download and no transcription unless --yes.
# Usage: transcribe.sh [--yes] [--model small] [--probe-url URL] [audio-or-video...]
set -u

APPLY=0
MODEL="small"
URLS=""
FILES=""

usage() {
  cat <<'EOF'
usage: transcribe.sh [--yes|--confirm] [--model NAME] [--probe-url URL] [FILE...]

Without --yes: print videos, duration, model, download size, and a rough time
estimate, then exit 0. Nothing is downloaded or transcribed.
With --yes (or MEDIA_CONFIRM=1): fetch audio for --probe-url if needed, then
run faster-whisper from the skill .venv. Default model is small.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --yes|--confirm) APPLY=1 ;;
    --model)
      shift
      MODEL="${1:-}"
      ;;
    --probe-url)
      shift
      URLS="${URLS}"$'\n'"${1:-}"
      ;;
    -h|--help) usage; exit 0 ;;
    -*) printf 'unknown flag: %s\n' "$1" >&2; exit 2 ;;
    *) FILES="${FILES}"$'\n'"$1" ;;
  esac
  shift
done

if [ "${MEDIA_CONFIRM:-}" = "1" ]; then
  APPLY=1
fi
if [ -z "$MODEL" ]; then
  printf 'missing model name\n' >&2
  exit 2
fi

case "$MODEL" in
  tiny) MODEL_SIZE="about 75 MiB" ;;
  base) MODEL_SIZE="about 145 MiB" ;;
  small) MODEL_SIZE="about 488 MiB" ;;
  medium) MODEL_SIZE="about 1.5 GiB" ;;
  large-v3) MODEL_SIZE="about 2.9 GiB" ;;
  *) MODEL_SIZE="unknown; read the model card before downloading" ;;
esac

SKILL_DIR="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
HUB="${HF_HOME:-$HOME/.cache/huggingface}/hub"
CACHE_DIR="${HUB}/models--Systran--faster-whisper-${MODEL}"
if [ -d "$CACHE_DIR" ]; then
  CACHED="yes"
else
  CACHED="no"
fi

total_dur="0"
audio_bytes=0
audio_unknown=0
items=0

printf 'asr-plan\n'
printf 'model: %s\n' "$MODEL"
if [ "$CACHED" = "yes" ]; then
  printf 'model-download: cached at %s\n' "$CACHE_DIR"
else
  printf 'model-download: not cached; first download %s\n' "$MODEL_SIZE"
fi

while IFS= read -r file; do
  [ -n "$file" ] || continue
  items=$((items + 1))
  dur="$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null || true)"
  case "$dur" in
    ''|*[!0-9.]*) dur="0" ;;
  esac
  total_dur="$(awk -v a="$total_dur" -v b="$dur" 'BEGIN { printf "%.3f", a+b }')"
  printf 'file: %s duration-seconds=%s\n' "$file" "$dur"
done <<EOF
$FILES
EOF

while IFS= read -r url; do
  [ -n "$url" ] || continue
  items=$((items + 1))
  meta="$(yt-dlp --no-warnings --skip-download -f ba --print '%(duration|0)s %(filesize_approx|0)s %(title)s' "$url" 2>/dev/null | tail -n 1 || true)"
  dur="$(printf '%s\n' "$meta" | awk '{ print $1 }')"
  bytes="$(printf '%s\n' "$meta" | awk '{ print $2 }')"
  title="$(printf '%s\n' "$meta" | awk '{ $1=""; $2=""; sub(/^ +/, ""); print }')"
  case "$dur" in
    ''|*[!0-9.]*) dur="0" ;;
  esac
  total_dur="$(awk -v a="$total_dur" -v b="$dur" 'BEGIN { printf "%.3f", a+b }')"
  case "$bytes" in
    ''|*[!0-9]*) audio_unknown=$((audio_unknown + 1)); bytes_note="unknown" ;;
    *) audio_bytes=$((audio_bytes + bytes)); bytes_note="${bytes} bytes" ;;
  esac
  printf 'url: %s title=%s duration-seconds=%s audio-size=%s\n' "$url" "${title:-unknown}" "$dur" "$bytes_note"
done <<EOF
$URLS
EOF

if [ "$items" -eq 0 ]; then
  usage >&2
  exit 2
fi

printf 'count: %s\n' "$items"
printf 'total-duration-seconds: %s\n' "$total_dur"
printf 'audio-known-bytes: %s\n' "$audio_bytes"
printf 'audio-unknown-size: %s\n' "$audio_unknown"
printf 'rough-cpu-time: order of the audio duration for small/int8 (often 0.3–2× realtime). Not a measurement. GPU is optional and faster.\n'
printf 'gpu: not required\n'

if [ "$APPLY" -ne 1 ]; then
  printf 'action: not started. Tell the user the lines above and wait. Re-run with --yes after they agree.\n'
  exit 0
fi

PY="${SKILL_DIR}/.venv/bin/python3"
if [ ! -x "$PY" ]; then
  printf 'faster-whisper venv is missing. Ask the user, then bash scripts/bootstrap.sh --yes --with-asr\n' >&2
  exit 1
fi

OUT="${MEDIA_OUTPUT_DIR:-./output}/asr"
mkdir -p "$OUT"
WORK="$FILES"

while IFS= read -r url; do
  [ -n "$url" ] || continue
  yt-dlp --no-playlist -x --audio-format m4a -P "$OUT" -o 'asr-%(id)s.%(ext)s' "$url"
done <<EOF
$URLS
EOF

if [ -n "$URLS" ]; then
  for audio in "$OUT"/asr-*.m4a; do
    [ -f "$audio" ] || continue
    WORK="${WORK}"$'\n'"$audio"
  done
fi

set --
while IFS= read -r file; do
  [ -n "$file" ] || continue
  set -- "$@" "$file"
done <<EOF
$WORK
EOF
if [ "$#" -eq 0 ]; then
  printf 'no audio files to transcribe\n' >&2
  exit 1
fi

"$PY" - "$MODEL" "$OUT" "$@" <<'PY'
import json
import sys
from pathlib import Path

model_name = sys.argv[1]
out_dir = Path(sys.argv[2])
files = [Path(p) for p in sys.argv[3:] if p]
try:
    from faster_whisper import WhisperModel
except ImportError:
    sys.stderr.write("faster-whisper is not installed in .venv\n")
    sys.exit(1)

model = WhisperModel(model_name, device="cpu", compute_type="int8")
for audio in files:
    segments, info = model.transcribe(str(audio), beam_size=5, vad_filter=True)
    payload = {
        "source": str(audio),
        "model": model_name,
        "language": info.language,
        "segments": [
            {"start": s.start, "end": s.end, "text": s.text.strip()}
            for s in segments
        ],
    }
    dest = out_dir / (audio.stem + ".json")
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(dest)
PY
