#!/usr/bin/env bash
# Turn a handle into profile URLs, then list videos with yt-dlp.
# Dry-run unless --yes or MEDIA_CONFIRM=1. Does not download media.
# Bash 3.2 or newer. No Sherlock and no extra package.
set -u

LIMIT=8
APPLY=0
OUT="${MEDIA_OUTPUT_DIR:-./output}/accounts"
HANDLES=""
PROFILES=""

# Fixed media sites. Video sites are listed with yt-dlp. The others are one page request.
SITES="YouTube Twitter GitHub Reddit Instagram TikTok Vimeo SoundCloud Twitch"
VIDEO_SITES="YouTube Instagram TikTok Vimeo SoundCloud Twitch"

usage() {
  cat <<'EOF'
usage: person.sh [--yes|--confirm] [--limit N] [-o DIR] [--sites "YouTube GitHub"] [--profile URL] HANDLE...

Default is a plan: print the accounts and sites, then exit 0. Nothing is queried.
--yes builds one profile URL per site and lists up to N recent videos on the
video sites. GitHub and Reddit are a single page request. X is only ruled out
when the page itself says the account is missing. A profile URL is listed directly.
This does not download video or audio. Subtitles and download.sh still use their
own gates. MEDIA_CONFIRM=1 is the same as --yes.
A group is several handles: person.sh --yes alice bob
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --yes|--confirm) APPLY=1; shift ;;
    --limit)
      LIMIT="${2:-}"
      shift 2
      ;;
    -o)
      OUT="${2:-}"
      shift 2
      ;;
    --profile)
      PROFILES="${PROFILES}${2:-}"$'\n'
      shift 2
      ;;
    --sites)
      SITES="${2:-}"
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    -*)
      printf 'unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
    *)
      HANDLES="${HANDLES}${1}"$'\n'
      shift
      ;;
  esac
done
while [ "$#" -gt 0 ]; do
  HANDLES="${HANDLES}${1}"$'\n'
  shift
done

if [ "${MEDIA_CONFIRM:-}" = "1" ]; then
  APPLY=1
fi

case "$LIMIT" in
  ''|*[!0-9]*)
    printf 'limit must be a positive integer\n' >&2
    exit 2
    ;;
esac
if [ "$LIMIT" -lt 1 ] || [ "$LIMIT" -gt 50 ]; then
  printf 'limit must be from 1 to 50\n' >&2
  exit 2
fi

if [ -z "$HANDLES" ] && [ -z "$PROFILES" ]; then
  usage >&2
  exit 2
fi

# Reject shell metacharacters. Account names are not group titles.
bad_token() {
  case "$1" in
    ""|-*|*' '*|*'/'*|*'\'*|*"'"*|*'\"'*|*'`'*|*'$'*|*';'*|*'&'*|*'|'*)
      return 0
      ;;
  esac
  return 1
}

clean_handles=""
while IFS= read -r handle; do
  [ -n "$handle" ] || continue
  case "$handle" in
    @*) handle="${handle#@}" ;;
  esac
  if bad_token "$handle"; then
    printf 'not an account name: %s\n' "$handle" >&2
    printf 'A group needs one handle per account, for example: person.sh alice bob\n' >&2
    exit 2
  fi
  clean_handles="${clean_handles}${handle}"$'\n'
done <<EOF
$HANDLES
EOF
HANDLES="$clean_handles"

clean_profiles=""
while IFS= read -r profile; do
  [ -n "$profile" ] || continue
  case "$profile" in
    http://*|https://*) ;;
    *)
      printf 'profile must be an http(s) URL: %s\n' "$profile" >&2
      exit 2
      ;;
  esac
  if bad_token "$profile"; then
    printf 'profile URL has a character this script will not pass through: %s\n' "$profile" >&2
    exit 2
  fi
  clean_profiles="${clean_profiles}${profile}"$'\n'
done <<EOF
$PROFILES
EOF
PROFILES="$clean_profiles"

known=" YouTube Twitter GitHub Reddit Instagram TikTok Vimeo SoundCloud Twitch "
for site in $SITES; do
  case "$known" in
    *" $site "*) ;;
    *)
      printf 'unknown site: %s\n' "$site" >&2
      exit 2
      ;;
  esac
done

printf 'person: plan\n'
printf 'handles:\n'
printf '%s' "$HANDLES" | sed '/^$/d; s/^/  /'
printf 'profiles:\n'
printf '%s' "$PROFILES" | sed '/^$/d; s/^/  /'
printf 'sites: %s\n' "$SITES"
printf 'video-sites: %s\n' "$VIDEO_SITES"
printf 'limit: %s\n' "$LIMIT"
printf 'output: %s\n' "$OUT"
printf 'probe: one profile URL per site, then yt-dlp on video sites\n'
if [ "$APPLY" -ne 1 ]; then
  printf 'action: not started\n'
  printf 'next: rerun with --yes to query accounts and list videos. No download.\n'
  exit 0
fi

if ! command -v yt-dlp >/dev/null 2>&1; then
  printf 'yt-dlp is not on PATH\n' >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  printf 'python3 is not on PATH\n' >&2
  exit 1
fi

mkdir -p "$OUT"
export PERSON_OUT="$OUT"
export PERSON_LIMIT="$LIMIT"
export PERSON_SITES="$SITES"
export PERSON_VIDEO_SITES="$VIDEO_SITES"
export PERSON_HANDLES="$HANDLES"
export PERSON_PROFILES="$PROFILES"

python3 - <<'PY'
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

out = Path(os.environ["PERSON_OUT"])
limit = int(os.environ["PERSON_LIMIT"])
sites = os.environ["PERSON_SITES"].split()
video_sites = set(os.environ["PERSON_VIDEO_SITES"].split())
handles = [line for line in os.environ["PERSON_HANDLES"].splitlines() if line]
profiles = [line for line in os.environ["PERSON_PROFILES"].splitlines() if line]

# URL templates and the two username patterns are the site rows from
# sherlock-project/sherlock data.json (MIT). Nothing else from that project is used.
# X and Instagram are not probed through the third-party frontends Sherlock uses.

platform_of = {
    "YouTube": "youtube",
    "Twitter": "x",
    "GitHub": "github",
    "Reddit": "reddit",
    "Instagram": "instagram",
    "TikTok": "tiktok",
    "Vimeo": "vimeo",
    "SoundCloud": "soundcloud",
    "Twitch": "twitch",
}


def host_site(url: str) -> str:
    host = url.split("/")[2].lower() if "://" in url else ""
    if host.startswith("www."):
        host = host[4:]
    mapping = {
        "youtube.com": "YouTube",
        "youtu.be": "YouTube",
        "x.com": "Twitter",
        "twitter.com": "Twitter",
        "github.com": "GitHub",
        "reddit.com": "Reddit",
        "instagram.com": "Instagram",
        "tiktok.com": "TikTok",
        "vimeo.com": "Vimeo",
        "soundcloud.com": "SoundCloud",
        "twitch.tv": "Twitch",
    }
    return mapping.get(host, "")


def list_videos(url: str) -> tuple[list[dict], str]:
    try:
        proc = subprocess.run(
            [
                "yt-dlp",
                "--flat-playlist",
                "--playlist-end",
                str(limit),
                "--no-warnings",
                "-J",
                url,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return [], "yt-dlp timed out"
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "yt-dlp failed").strip().splitlines()
        return [], err[0] if err else "yt-dlp failed"
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return [], "yt-dlp did not return JSON"
    entries = data.get("entries") if isinstance(data, dict) else None
    if entries is None and isinstance(data, dict) and data.get("webpage_url"):
        entries = [data]
    videos = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        video_url = str(entry.get("webpage_url") or entry.get("url") or "").strip()
        if video_url.startswith("/"):
            video_url = ""
        if not video_url.startswith("http"):
            vid = str(entry.get("id") or "").strip()
            if vid and "youtube" in url:
                video_url = f"https://www.youtube.com/watch?v={vid}"
            else:
                continue
        title = str(entry.get("title") or entry.get("id") or "").strip()
        videos.append({"title": title, "url": video_url})
        if len(videos) >= limit:
            break
    return videos, ""


TEMPLATES = {
    "YouTube": "https://www.youtube.com/@{}",
    "Twitter": "https://x.com/{}",
    "GitHub": "https://github.com/{}",
    "Reddit": "https://www.reddit.com/user/{}",
    "Instagram": "https://www.instagram.com/{}",
    "TikTok": "https://www.tiktok.com/@{}",
    "Vimeo": "https://vimeo.com/{}",
    "SoundCloud": "https://soundcloud.com/{}",
    "Twitch": "https://www.twitch.tv/{}",
}
HANDLE_OK = {
    "Twitter": re.compile(r"^[a-zA-Z0-9_]{1,15}$"),
    "GitHub": re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$"),
}


def fetch(url: str) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "media-toolkit",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            return response.status, response.read(200_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        body = exc.read(200_000).decode("utf-8", "replace") if exc.fp else ""
        return exc.code, body
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, str(exc)


def page_status(site: str, url: str) -> tuple[str, str]:
    if site == "Twitter":
        status, body = fetch(url)
        missing = "<div class=\"error-panel\"><span>User " in body or status == 404
        if missing:
            return "missing", "the page says this account is not there"
        return "unchecked", "a plain request does not prove an X account; open the profile"
    if site == "GitHub":
        status, _body = fetch(url)
        if status == 404:
            return "missing", ""
        if status == 200:
            return "claimed", ""
        return "unchecked", f"github http {status}"
    if site == "Reddit":
        status, body = fetch(url)
        if "Sorry, nobody on Reddit goes by that name." in body or status == 404:
            return "missing", ""
        if status == 200:
            return "claimed", ""
        return "unchecked", f"reddit http {status}"
    return "unchecked", "profile only"


cards = []
seen = set()
for handle_name in handles:
    for site in sites:
        pattern = HANDLE_OK.get(site)
        if pattern and not pattern.match(handle_name):
            continue
        profile_url = TEMPLATES[site].format(handle_name)
        if (site, profile_url) in seen:
            continue
        seen.add((site, profile_url))
        card = {
            "handle": handle_name,
            "platform": platform_of.get(site, site.lower()),
            "site": site,
            "profile_url": profile_url,
            "status": "claimed",
            "videos": [],
        }
        if site in video_sites:
            videos, note = list_videos(profile_url)
            card["videos"] = videos
            if videos:
                card["status"] = "claimed"
            elif note:
                card["status"] = "unchecked"
                card["list_note"] = note
            else:
                card["status"] = "missing"
        else:
            status, note = page_status(site, profile_url)
            card["status"] = status
            if note:
                card["list_note"] = note
        if card["status"] == "missing":
            continue
        cards.append(card)

for profile_url in profiles:
    site = host_site(profile_url)
    if (site, profile_url) in seen:
        continue
    seen.add((site, profile_url))
    card = {
        "handle": "",
        "platform": platform_of.get(site, "web"),
        "site": site or "web",
        "profile_url": profile_url,
        "status": "given",
        "videos": [],
    }
    if site in video_sites:
        videos, note = list_videos(profile_url)
        card["videos"] = videos
        if note:
            card["list_note"] = note
    else:
        card["list_note"] = "profile only; pass a video URL or a video-site profile"
    cards.append(card)

items = []
lines = []
for card in cards:
    for video in card["videos"]:
        items.append(
            {
                "url": video["url"],
                "platform": card["platform"],
                "title": video["title"],
                "author": card["handle"],
                "profile_url": card["profile_url"],
                "why_selected": "listed from the account profile",
            }
        )
        lines.append(video["url"])

people = {
    "handles": handles,
    "profiles": profiles,
    "limit": limit,
    "sites": sites,
    "cards": cards,
}
(out / "people.json").write_text(json.dumps(people, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(out / "videos.json").write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(out / "sources.txt").write_text(("\n".join(lines) + ("\n" if lines else "")), encoding="utf-8")
print(f"cards: {len(cards)}")
print(f"videos: {len(items)}")
print(f"people: {out / 'people.json'}")
print(f"videos-file: {out / 'videos.json'}")
print(f"sources: {out / 'sources.txt'}")
PY

status=$?
if [ "$status" -ne 0 ]; then
  printf 'action: failed\n'
  exit "$status"
fi
printf 'action: listed\n'
printf 'next: subtitles from sources.txt need no extra confirm. download.sh still stops for --yes.\n'
exit 0
