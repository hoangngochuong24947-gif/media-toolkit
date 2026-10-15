# Discovery (optional Agent-Reach)

Agent-Reach is a separate MIT-licensed project: https://github.com/Panniantong/Agent-Reach

It is a companion, not a dependency. This repo does not vendor its code. It selects upstream readers (Jina Reader, yt-dlp, twitter-cli or OpenCLI, bili-cli, Reddit, XiaoHongShu, GitHub, RSS, Exa) and health-checks them. It does not write reports and it does not process media. media-toolkit does the media work. The host agent writes the report.

Do not `pip install agent-reach` from PyPI. Upstream says that name is a different project. The documented install is the GitHub zip, via pipx or a user venv. `scripts/bootstrap.sh --with-reach` prints that plan and, only with `--yes`, runs it. It does not use sudo, does not write cookies, and does not run `agent-reach install --system`.

## When to use which tool

| Need | Tool |
| :--- | :--- |
| Topic research, a web page, RSS, GitHub, Exa search | Agent-Reach upstream command |
| What people are saying on X, Reddit, or XiaoHongShu | Agent-Reach (`twitter`, `opencli` / `rdt`, `opencli xiaohongshu`) |
| Bilibili search when yt-dlp returns HTTP 412 | `bili search` (bili-cli). Keep the BV link it returns |
| YouTube search when yt-dlp works | yt-dlp `ytsearch` is enough. Agent-Reach uses yt-dlp for YouTube too |
| Download, subtitles, transcription, trim, GIF, compress, images | media-toolkit |
| Where a handle has a profile, then that profile's videos | `scripts/person.sh` builds the profile URL and lists videos into `sources.txt` |

`bash scripts/doctor.sh` prints `capability discovery (agent-reach): absent|ready|degraded` and, when the CLI answers, one `discovery-backend:` line per channel (`status` and `active_backend` only). A missing CLI is not a failure.

Route by `active_backend` from `agent-reach doctor --json`. If the backend for a platform is empty, that platform is not ready. Ask the user before `agent-reach install --env=auto --system --channels=...`. That command can install extra tools. Still do not configure logins unless they ask.

## Handoff

Agent-Reach yields URLs. The agent writes them to `${MEDIA_OUTPUT_DIR:-./output}/<task>/sources.json`:

```json
{
  "items": [
    {
      "url": "https://x.com/someone/status/123",
      "platform": "twitter",
      "title": "post text, short",
      "author": "someone",
      "published": "2026-01-02",
      "why_selected": "directly evaluates the topic"
    }
  ]
}
```

Required field: `url`. Keep the others when you have them. Then:

```bash
python3 scripts/optional_tools.py sources ./output/<task>/sources.json
python3 scripts/optional_tools.py sources ./output/<task>/sources.json --platform twitter
```

That only prints URLs. Subtitles, `download.sh`, and `transcribe.sh` consume those URLs under the usual confirmation gates. Save the post text you actually read (twitter CLI stdout, Reddit thread, XiaoHongShu note) next to the file, for example `posts.txt`. The report cites that text and, for videos, timestamps from `subs_to_text.sh`.

## A person's videos

No username scanner is installed. A handle becomes one profile URL per media site, then `yt-dlp` lists videos from the video sites. The URL shapes for YouTube, X, GitHub, Reddit, Instagram, TikTok, Vimeo, SoundCloud, and Twitch follow the site rows in Sherlock's `data.json` (MIT, https://github.com/sherlock-project/sherlock). GitHub's host here is `github.com`, not `www.github.com`. X and Instagram are not sent to the third-party frontends in that file.

`bash scripts/doctor.sh` prints `capability accounts: ready|not-ready`. Ready means `yt-dlp` and `python3` are on `PATH`.

```bash
bash scripts/person.sh someuser
# plan, exit 0
bash scripts/person.sh --yes -o ./output/someuser --limit 8 someuser
```

`--yes` writes:

- `people.json` — one card per claimed profile (`handle`, `platform`, `profile_url`, `videos`)
- `videos.json` — the same shape as `sources.json` (`url`, `platform`, `title`, `author`, `profile_url`)
- `sources.txt` — one video URL per line

YouTube, Instagram, TikTok, Vimeo, SoundCloud, and Twitch cards are a flat video list (no file download). A list means the account is there. An error leaves the card unchecked, because a bot check looks like a missing account. GitHub and Reddit are one page request: 404, or Reddit's "nobody on Reddit goes by that name", drops the card. X is dropped only when its own page says the account is missing; otherwise the card stays unchecked and keeps the link. Do not invent video URLs for X, GitHub, or Reddit. X posts still go through Agent-Reach; a status URL that contains video still goes through yt-dlp.

Several people are several handles: `person.sh --yes alice bob`. A sentence like "people in this group" needs those handles first. Take them from the user, or from authors already chosen out of a topic search. Same spelling on two sites stays two cards until the user picks.

A URL the user already has skips the handle templates: `person.sh --yes --profile "https://www.youtube.com/@someuser"`.

After the list, subtitles use `sources.txt` with no extra confirm. `download.sh` still prints a plan and waits. The host reads the text and writes `report.md`.

## X / Twitter

Reading one public post, searching, and timelines are Agent-Reach, not yt-dlp. Upstream quick reference (see their install guide):

```bash
twitter search "QUERY" -n 10
```

`twitter` reads `TWITTER_AUTH_TOKEN` and `TWITTER_CT0` from the environment. Ask the user once before any X login. They export cookies themselves (Cookie-Editor header string, then `agent-reach configure twitter-cookies`, or they set the two variables). Do not echo the values, do not write them into the repo, and do not commit them. `agent-reach doctor` only checks that a config exists. The `twitter` process still needs the variables in that shell.

A status URL that contains a video is media-toolkit:

```bash
yt-dlp --simulate -F "https://x.com/USER/status/ID"
yt-dlp --simulate -F "https://twitter.com/USER/status/ID"
```

`--simulate` / `-F` is a read. Public videos sometimes list formats with no login. NSFW, private, and age-limited posts need a logged-in session. Ask once which browser and profile, then:

```bash
bash scripts/download.sh --cookies-from-browser "chrome:Default" "https://x.com/USER/status/ID"
# show count and size, wait, then add --yes
```

X Spaces and live streams are a poor fit for yt-dlp. If `-F` says unsupported or login required, say so and stop. Do not loop `twitter search` or yt-dlp against rate limits.

## Bilibili when yt-dlp returns 412

Datacenter IPs often get HTTP 412 from Bilibili. Agent-Reach's current selector is bili-cli, then OpenCLI. After `bili` is on PATH:

```bash
bili search "QUERY" --type video
```

Put the BV or av URL in `sources.json`. Fetching the video file or its subtitles is still media-toolkit, and it may still need the cookie steps in `references/yt-dlp.md`.

## Worked example

User: `看看 X 上大家怎么评价 <topic>，把里面的视频也总结一下`

```bash
bash scripts/doctor.sh
# discovery absent: show this plan and wait
bash scripts/bootstrap.sh --with-reach
# after they agree (no cookies are configured by this command):
bash scripts/bootstrap.sh --yes --with-reach
agent-reach doctor --json

# Ask once before any X login. Then, in that shell only, never echoed:
# export TWITTER_AUTH_TOKEN="..."
# export TWITTER_CT0="..."
twitter search "<topic>" -n 10

# Agent writes ./output/<topic>/sources.json (url, platform, title, author, published, why_selected)
# and saves the post text it read to ./output/<topic>/posts.txt

python3 scripts/optional_tools.py sources ./output/<topic>/sources.json --platform twitter

# For each status URL that actually has video (read-only):
yt-dlp --simulate -F "https://x.com/USER/status/ID"
# login wall: ask which browser once, then
bash scripts/download.sh --cookies-from-browser "BROWSER" "https://x.com/USER/status/ID"
# wait for yes, then the same command with --yes

# Subtitles, no ask, when the page has them:
yt-dlp --write-sub --write-auto-sub --sub-langs "en.*,zh-Hans,zh-CN" \
  --convert-subs srt --skip-download \
  -P ./output/<topic>/subs -o "%(id)s.%(ext)s" "https://x.com/USER/status/ID"
bash scripts/subs_to_text.sh ./output/<topic>/subs/*.srt -o ./output/<topic>/text

# No subs: bash scripts/transcribe.sh --model small --probe-url "URL"  and wait
# Agent reads posts.txt and ./output/<topic>/text, then writes report.md
# from references/report-template.md. Cite the post and the timestamps.
```

Hermes: install this skill at `~/.hermes/skills/media/media-toolkit`. Agent-Reach's own installer writes its skill to Claude Code, OpenClaw, OpenCode, and `~/.agents/skills`, not to Hermes. After the CLI is installed, copy the `agent_reach/skill` directory from that install to `~/.hermes/skills/agent-reach` (the directory name is the skill name). `hermes skills list` should show both. Do not point Hermes at a raw `SKILL.md` URL.
