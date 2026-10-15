#!/usr/bin/env bash
# Offline checks for confirmation gates. No network and no installs.
set -eu

ROOT="$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)"
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
dry="$(bash "$ROOT/scripts/bootstrap.sh" --dry-run --with-reach)"
printf '%s\n' "$dry" | grep -q 'bootstrap: dry-run'
printf '%s\n' "$dry" | grep -q 'nothing installed'
# The reach plan depends on the machine: keep an already installed CLI, plan the
# pipx install, or report a missing Python 3.10+. Any one of the three is a
# correct dry-run; what matters is that it never installs here.
printf '%s\n' "$dry" | grep -qE '^(keep: agent-reach |would-run: pipx install |missing: Python 3\.10\+)'
printf '%s\n' "$dry" | grep -q 'reach-source: https://github.com/Panniantong/Agent-Reach/archive/main.zip'
printf '%s\n' "$dry" | grep -q 'reach-policy: no sudo'

# Discovery is optional. A missing agent-reach does not change the doctor contract,
# and a fake doctor JSON is summarized without printing channel messages.
PATH="/usr/bin:/bin" bash "$ROOT/scripts/doctor.sh" > "$TMP/doc-absent.txt" || true
grep -q 'capability discovery (agent-reach): absent' "$TMP/doc-absent.txt"
grep -q 'capability accounts: not-ready' "$TMP/doc-absent.txt"
cat > "$TMP/bin/agent-reach" <<EOF
#!/bin/sh
if [ "\$1" = "doctor" ] && [ "\$2" = "--json" ]; then
  printf '%s\n' '{"twitter":{"status":"warn","active_backend":null,"message":"secret-should-not-print"},"web":{"status":"ok","active_backend":"jina"}}'
fi
EOF
chmod +x "$TMP/bin/agent-reach"
PATH="$TMP/bin:/usr/bin:/bin" bash "$ROOT/scripts/doctor.sh" > "$TMP/doc-reach.txt" || true
grep -q 'discovery-backend: twitter status=warn active_backend=-' "$TMP/doc-reach.txt"
grep -q 'discovery-backend: web status=ok active_backend=jina' "$TMP/doc-reach.txt"
grep -q 'capability discovery (agent-reach): ready' "$TMP/doc-reach.txt"
if grep -q 'secret-should-not-print' "$TMP/doc-reach.txt"; then
  printf 'doctor must not print agent-reach channel messages\n' >&2
  exit 1
fi

# Account lookup is a plan until --yes, and --yes must not download.
plan="$(bash "$ROOT/scripts/person.sh" someuser)"
printf '%s\n' "$plan" | grep -q 'action: not started'
printf '%s\n' "$plan" | grep -q 'sites: YouTube Twitter GitHub Reddit Instagram TikTok Vimeo SoundCloud Twitch'
printf '%s\n' "$plan" | grep -q 'probe: one profile URL per site'
if printf '%s\n' "$plan" | grep -q 'action: listed'; then
  printf 'person plan must not list yet\n' >&2
  exit 1
fi

cat > "$TMP/bin/yt-dlp" <<EOF
#!/bin/sh
printf '%s\n' "\$*" >> "$TMP/person-yt-log"
cat <<JSON
{"entries":[{"title":"Talk","webpage_url":"https://www.youtube.com/watch?v=abc"},{"title":"Other","id":"def","url":"def"}]}
JSON
EOF
chmod +x "$TMP/bin/yt-dlp"
PATH="$TMP/bin:$PATH" bash "$ROOT/scripts/person.sh" --yes --sites YouTube -o "$TMP/out" --limit 2 someuser > "$TMP/person.txt"
grep -q 'action: listed' "$TMP/person.txt"
grep -q 'videos: 2' "$TMP/person.txt"
python3 - "$TMP/out/videos.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
urls = [item["url"] for item in data["items"]]
assert urls == [
    "https://www.youtube.com/watch?v=abc",
    "https://www.youtube.com/watch?v=def",
], urls
assert all(item["platform"] == "youtube" for item in data["items"])
PY
if ! grep -q 'https://www.youtube.com/@someuser' "$TMP/person-yt-log"; then
  printf 'video list must use the profile URL\n' >&2
  exit 1
fi
if grep -q 'merge-output-format\|-x ' "$TMP/person-yt-log"; then
  printf 'person listing must not download\n' >&2
  exit 1
fi

# A group title is not an account scan.
if PATH="$TMP/bin:/usr/bin:/bin" bash "$ROOT/scripts/person.sh" "some group" >/dev/null 2>"$TMP/bad.txt"; then
  printf 'a group phrase must not run\n' >&2
  exit 1
fi
grep -q 'not an account name' "$TMP/bad.txt"

printf 'gates: ok\n'
