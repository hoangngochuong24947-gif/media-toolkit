#!/usr/bin/env bash
# Estimate a download, then fetch only after --yes / MEDIA_CONFIRM=1.
# Usage: download.sh [--yes] [--audio] [--cookies-from-browser NAME] URL [URL...]
set -u

APPLY=0
AUDIO=0
COOKIES=""
URLS=""

usage() {
  cat <<'EOF'
usage: download.sh [--yes|--confirm] [--audio] [--cookies-from-browser NAME] URL [URL...]

Without --yes: print count and estimated size, then exit 0. No media is saved.
With --yes (or MEDIA_CONFIRM=1): download into ${MEDIA_OUTPUT_DIR:-./output}.
Ask the user which browser once before --cookies-from-browser. Cookies are not read until --yes.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --yes|--confirm) APPLY=1 ;;
    --audio) AUDIO=1 ;;
    --cookies-from-browser)
      shift
      COOKIES="${1:-}"
      if [ -z "$COOKIES" ]; then
        printf 'missing browser name after --cookies-from-browser\n' >&2
        exit 2
      fi
      ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    -*) printf 'unknown flag: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    *) URLS="${URLS}"$'\n'"$1" ;;
  esac
  shift
done
while [ "$#" -gt 0 ]; do
  URLS="${URLS}"$'\n'"$1"
  shift
done

if [ "${MEDIA_CONFIRM:-}" = "1" ]; then
  APPLY=1
fi

count=0
known=0
unknown=0
printf 'download-plan\n'
while IFS= read -r url; do
  [ -n "$url" ] || continue
  count=$((count + 1))
  if [ "$AUDIO" -eq 1 ]; then
    raw="$(yt-dlp --no-warnings --skip-download -f ba --print '%(filesize_approx|0)s' "$url" 2>/dev/null | tail -n 1 || true)"
  else
    raw="$(yt-dlp --no-warnings --skip-download --print '%(filesize_approx|0)s' "$url" 2>/dev/null | tail -n 1 || true)"
  fi
  case "$raw" in
    ''|*[!0-9]*) unknown=$((unknown + 1)); size_note="unknown" ;;
    *) known=$((known + raw)); size_note="${raw} bytes" ;;
  esac
  printf 'item: %s size=%s\n' "$url" "$size_note"
done <<EOF
$URLS
EOF

if [ "$count" -eq 0 ]; then
  usage >&2
  exit 2
fi

printf 'count: %s\n' "$count"
printf 'known-bytes: %s\n' "$known"
printf 'unknown-size: %s\n' "$unknown"
if [ -n "$COOKIES" ]; then
  printf 'cookies: %s\n' "$COOKIES"
  printf 'cookies-read: no\n'
else
  printf 'cookies: none\n'
fi
if [ "$AUDIO" -eq 1 ]; then
  printf 'mode: audio\n'
else
  printf 'mode: video\n'
fi

if [ "$APPLY" -ne 1 ]; then
  printf 'action: not started. Show this count and size, ask the user, then re-run with --yes.\n'
  exit 0
fi

OUT="${MEDIA_OUTPUT_DIR:-./output}"
mkdir -p "$OUT"
while IFS= read -r url; do
  [ -n "$url" ] || continue
  set -- yt-dlp --no-playlist -P "$OUT" -o '%(title)s.%(ext)s'
  if [ "$AUDIO" -eq 1 ]; then
    set -- "$@" -x --audio-format mp3 --audio-quality 0
  else
    set -- "$@" -f 'bv*+ba/b' --merge-output-format mp4
  fi
  if [ -n "$COOKIES" ]; then
    set -- "$@" --cookies-from-browser "$COOKIES"
  fi
  set -- "$@" "$url"
  "$@"
done <<EOF
$URLS
EOF
printf 'download: done -> %s\n' "$OUT"
