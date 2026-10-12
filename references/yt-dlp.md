# yt-dlp

Use yt-dlp for public pages the user can already open. It does not remove DRM, and it does not unlock a purchase the account has not made.

Known-good stable release used in the install lines: **2026.08.19**. Upgrade with `sudo yt-dlp --update-to stable` or `pipx upgrade yt-dlp`. Nightly builds move faster when a site changes; switch only when stable fails: `sudo yt-dlp --update-to nightly`.

Put every download under `${MEDIA_OUTPUT_DIR:-./output}`.

## Search

Always print `%(webpage_url)s`. A YouTube id glued onto `watch?v=` is wrong for Bilibili BV/av links and for any other site.

```bash
OUT="${MEDIA_OUTPUT_DIR:-./output}"
mkdir -p "$OUT"

# YouTube. ytsearchdateN sorts by date.
yt-dlp --flat-playlist --print "%(title)s | %(duration_string)s | %(uploader)s | %(webpage_url)s" "ytsearch5:QUERY"

# Bilibili.
yt-dlp --flat-playlist --print "%(title)s | %(duration_string)s | %(uploader)s | %(webpage_url)s" "bilisearch5:QUERY"
```

If `webpage_url` is empty in flat mode, drop `--flat-playlist` for that one query so yt-dlp resolves the real page URL. Do not invent a watch URL from the id.

Hand the chosen `webpage_url` to the next step unchanged.

## Formats

Best picture plus best audio, with a single-file fallback:

```bash
yt-dlp -f "bv*+ba/b" --merge-output-format mp4 \
  -P "${MEDIA_OUTPUT_DIR:-./output}" -o "%(title)s.%(ext)s" "URL"
```

`bv*+ba/b` is the current spelling of `bestvideo+bestaudio/best`.

Smaller presets when the user asked for size, not maximum quality:

```bash
# Up to 720p, else the best combined format.
yt-dlp -f "bv*[height<=720]+ba/b[height<=720]" --merge-output-format mp4 -P "${MEDIA_OUTPUT_DIR:-./output}" "URL"

# Audio only, encoded to MP3.
yt-dlp -x --audio-format mp3 --audio-quality 0 -P "${MEDIA_OUTPUT_DIR:-./output}" -o "%(title)s.%(ext)s" "URL"
```

After a video download, optional full decode (the file must actually play):

```bash
ffmpeg -nostdin -v error -i "${MEDIA_OUTPUT_DIR:-./output}/FILE.mp4" -f null -
python3 scripts/optional_tools.py validate "${MEDIA_OUTPUT_DIR:-./output}/FILE.mp4"
```

## Subtitles

Manual subtitles are the author's text. Automatic captions are speech-to-text and can be wrong. Prefer manual when both exist.

```bash
yt-dlp --list-subs "URL"
yt-dlp --write-sub --write-auto-sub \
  --sub-langs "zh-Hans,zh-CN,en.*,en" \
  --convert-subs srt \
  --skip-download \
  -P "${MEDIA_OUTPUT_DIR:-./output}" \
  -o "%(title)s.%(ext)s" \
  "URL"
```

`--sub-langs` picks languages. `--convert-subs srt` needs ffmpeg. Subtitles are not a transcript until someone reads them; see `distill-workflow.md`.

## Playlists

A URL that contains `list=` is a batch. Show the item count and estimated size (`scripts/download.sh` without `--yes`) and wait for the user before downloading. `--no-playlist` keeps a single video.

```bash
yt-dlp --yes-playlist --playlist-items 1:5 \
  -f "bv*+ba/b" --merge-output-format mp4 \
  -P "${MEDIA_OUTPUT_DIR:-./output}" \
  -o "%(playlist_index)03d-%(title)s.%(ext)s" \
  "PLAYLIST_URL"
```

## Rate limits

```bash
yt-dlp --sleep-requests 1 --max-sleep-interval 5 --limit-rate 5M "URL"
```

Do not retry a 429 in a tight loop.

## JS runtime

YouTube signature (n / nsig) checks need a JS runtime. deno is preferred. node is acceptable.

```bash
yt-dlp --js-runtimes deno "URL"
# or
yt-dlp --js-runtimes node "URL"
```

`scripts/doctor.sh` reports which one is installed.

## Cookies

Ask the user once which browser and profile to use. Do not guess, and do not pass `--cookies-from-browser` until they answer. `scripts/download.sh` will not read a browser unless that flag and `--yes` are both present.

For normal personal use on the user's own computer, reuse the browser they are already logged into:

```bash
yt-dlp --cookies-from-browser chrome "URL"
yt-dlp --cookies-from-browser firefox "URL"
yt-dlp --cookies-from-browser safari "URL"
yt-dlp --cookies-from-browser edge "URL"
```

Profile notes:

- Default profile is just the browser name.
- Another Chrome profile: `--cookies-from-browser "chrome:Profile 1"` (the folder name under the Chrome user-data directory, not the visible profile label).
- Firefox often needs the folder name: `--cookies-from-browser "firefox:default-release"`.
- Safari is macOS-only and uses the user's login keychain.
- Edge: `--cookies-from-browser "edge:Default"` or `"edge:Profile 1"`.

On macOS, the first Chrome or Edge read can prompt for the keychain item "Chrome Safe Storage". That prompt is expected. The user allows it once. It is not a reason to avoid the flag on a machine they are sitting at.

Headless, remote, or VM sessions have no interactive browser profile. Export a Netscape `cookies.txt` from a browser that can play the video (the "Get cookies.txt LOCALLY" extension, or the browser's own export) and store it outside the repo, mode `600`:

```bash
mkdir -p ~/.config/yt-dlp
chmod 700 ~/.config/yt-dlp
# save the export as ~/.config/yt-dlp/cookies.txt
chmod 600 ~/.config/yt-dlp/cookies.txt
yt-dlp --cookies ~/.config/yt-dlp/cookies.txt "URL"
```

Never commit `cookies.txt` or a copy of it. `.gitignore` already excludes those names.

Cloud, VM, and datacenter IP addresses often get YouTube's "Sign in to confirm you're not a bot" / "confirm you're not a bot" page even for public videos. The fix is to run yt-dlp on the user's own computer, or to pass cookies from a browser that has already passed that check. Updating yt-dlp does not turn a blocked datacenter address into a home address.

## Region locks

If a video is only offered in some countries, yt-dlp cannot move the machine into that country. `--geo-bypass` only helps when the client address is already allowed and the site mis-detects it. A browser cookie exported from a session that can play the video is the honest signal. Do not promise a block bypass.

## X / Twitter

yt-dlp handles a status URL that contains a video. Text, threads, and search belong to Agent-Reach (`references/discovery.md`), not to yt-dlp.

```bash
yt-dlp --simulate -F "https://x.com/USER/status/ID"
yt-dlp --simulate -F "https://twitter.com/USER/status/ID"
```

`--simulate` and `-F` only list formats. A public video sometimes works with no login. NSFW, private, and age-limited posts need a logged-in session. Ask once which browser and profile, then pass `--cookies-from-browser` only on a download the user has already approved (`scripts/download.sh --yes`). The same ask covers X credentials for the `twitter` CLI: `TWITTER_AUTH_TOKEN` and `TWITTER_CT0` must be environment variables in that shell. Do not echo them, do not write them into the repo, and do not commit them.

Spaces and live broadcasts are unreliable in yt-dlp. If `-F` returns no video format, or says login or unsupported, stop and say so. Do not retry in a loop; X rate-limits aggressive clients.

## Bilibili HTTP 412

412 from Bilibili is an anti-bot response: missing cookies, a rejected header, or a datacenter address. Try these in order:

```bash
yt-dlp --cookies-from-browser chrome \
  --referer "https://www.bilibili.com" \
  --user-agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36" \
  -f "bv*+ba/b" --merge-output-format mp4 \
  -P "${MEDIA_OUTPUT_DIR:-./output}" \
  "https://www.bilibili.com/video/BVxxxxxxxxxx"
```

Also: upgrade yt-dlp to the known-good pin or newer, and slow down (`--sleep-requests 1 --limit-rate 2M`). Search still uses `%(webpage_url)s` so the BV or av link you pass back is the real page.

When search itself returns 412, discover with Agent-Reach instead of yt-dlp: `bili search "QUERY" --type video` (see `references/discovery.md`). Put that BV or av URL in `sources.json`, then come back here to download or take subtitles.

## What yt-dlp will not do

- DRM (Widevine and similar), even if a browser can play it.
- Paid or members-only media the account has not bought.
- Live streams at the true live edge (latency, DVR windows, and premieres are unreliable).
- A guaranteed 4K file. You get the best format the site actually serves.
- Logged-in downloads from a machine that cannot read that browser's cookies.

## Errors

| Symptom | What it usually means | What to do |
| :--- | :--- | :--- |
| "confirm you're not a bot" / "Sign in to confirm" | Datacenter or flagged IP, or missing YouTube cookies | Run on the user's computer, or `--cookies-from-browser` / `--cookies` from a browser that can play it |
| HTTP 412 | Bilibili (or similar) anti-bot | Cookies, `--referer https://www.bilibili.com`, a browser user-agent, update yt-dlp, slow down |
| HTTP 429 / "Too Many Requests" | Rate limit | `--sleep-requests` and `--limit-rate`; wait; do not tight-loop |
| HTTP 403 | Forbidden, stale signature, or blocked IP | Update yt-dlp, add deno, pass cookies if the video is login-gated |
| nsig / signature / "unable to extract" / "nsig extraction failed" | JS challenge newer than this yt-dlp | `yt-dlp --update-to stable` or `nightly`, and install deno (`--js-runtimes deno`) |
| "Requested format is not available" | The `-f` filter matched nothing | Drop the height cap or use `bv*+ba/b` |
