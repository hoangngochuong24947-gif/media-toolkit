#!/usr/bin/env bash
# Offline checks for confirmation gates. No network and no installs.
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/gates.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

# ASR plan only: no transcript, exit 0.
ffmpeg -nostdin -y -v error -f lavfi -i sine=frequency=440:duration=1 -f lavfi -i testsrc=size=64x64:rate=5:duration=1 -shortest "$TMP/clip.mp4"
plan="$(bash "$ROOT/scripts/transcribe.sh" --model small "$TMP/clip.mp4")"
printf '%s\n' "$plan" | grep -q 'model: small'
printf '%s\n' "$plan" | grep -q 'action: not started'
printf '%s\n' "$plan" | grep -q 'model-download:'
test ! -e "$TMP/clip.json"

# large-v3 plan names the download size and still does no work.
plan_big="$(bash "$ROOT/scripts/transcribe.sh" --model large-v3 "$TMP/clip.mp4")"
printf '%s\n' "$plan_big" | grep -q '2.9 GiB'
test ! -d "${HF_HOME:-$HOME/.cache/huggingface}/hub/models--Systran--faster-whisper-large-v3"

# Download plan uses a fake yt-dlp and must not request a merge.
mkdir -p "$TMP/bin"
cat > "$TMP/bin/yt-dlp" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >> "$TMP/yt-log"
printf '%s\n' 2048
EOF
chmod +x "$TMP/bin/yt-dlp"
PATH="$TMP/bin:$PATH" bash "$ROOT/scripts/download.sh" "https://example.com/a" "https://example.com/b" > "$TMP/dl.txt"
grep -q 'count: 2' "$TMP/dl.txt"
grep -q 'known-bytes: 4096' "$TMP/dl.txt"
grep -q 'action: not started' "$TMP/dl.txt"
grep -q -- '--skip-download' "$TMP/yt-log"
if grep -q 'merge-output-format' "$TMP/yt-log"; then
  printf 'download plan must not start a merge\n' >&2
  exit 1
fi

# bootstrap dry-run must not be the install path.
dry="$(bash "$ROOT/scripts/bootstrap.sh" --dry-run)"
printf '%s\n' "$dry" | grep -q 'bootstrap: dry-run'
printf '%s\n' "$dry" | grep -q 'nothing installed'

printf 'gates: ok\n'
