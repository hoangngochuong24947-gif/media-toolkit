# Media Toolkit

Lightweight recipes for `ffmpeg`, `yt-dlp`, and ImageMagick. Any agent can follow [`SKILL.md`](SKILL.md). Limits, quality settings, and failures live in [`references/`](references/).

Windows: use WSL or Git Bash. The scripts are bash.

The agent runs the tools and writes any summary. The skill does not call an LLM. Costly steps (system packages, full downloads, local transcription, browser cookies, big batches) wait for a yes. `bash scripts/bootstrap.sh` only prints a plan until `--yes`.

## Install into Hermes / Claude Code / Codex / Cursor

Hermes Agent (Nous Research) loads skills from `~/.hermes/skills/`. Official CLI install, then a full copy of this repo so `scripts/` and `references/` stay together:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
mkdir -p ~/.hermes/skills/media
git clone https://github.com/hoangngochuong24947-gif/media-toolkit.git ~/.hermes/skills/media/media-toolkit
hermes skills list
```

`hermes skills install <owner/repo/path>` exists for hub and GitHub skill directories. This skill's `SKILL.md` is at the repository root and needs the sibling `scripts/` and `references/` files, so the clone above is the install to use. Do not point that command at a raw `SKILL.md` URL; Hermes would not receive the helper scripts.

Claude Code, Codex, and the shared agentskills.io directory:

```bash
git clone https://github.com/hoangngochuong24947-gif/media-toolkit.git ~/.claude/skills/media-toolkit
git clone https://github.com/hoangngochuong24947-gif/media-toolkit.git ~/.agents/skills/media-toolkit
```

Cursor: clone or copy the folder into the project (or into `~/.agents/skills/media-toolkit`) and tell the agent to follow `SKILL.md`.

Optional discovery companion, [Agent-Reach](https://github.com/Panniantong/Agent-Reach) (MIT). This repo does not vendor it. Upstream says not to install the PyPI package of the same name. After the user agrees:

```bash
bash scripts/bootstrap.sh --with-reach
bash scripts/bootstrap.sh --yes --with-reach
```

That is `pipx install` of their GitHub zip, or a user venv. It does not configure X cookies. Their installer does not write a Hermes skill. Copy the installed `agent_reach/skill` directory to `~/.hermes/skills/agent-reach` so `hermes skills list` shows it beside `media-toolkit`. Routing is in [`references/discovery.md`](references/discovery.md).

## Install tools

Check what this machine is missing:

```bash
bash scripts/doctor.sh
```

Exit 0 means `ffmpeg`, `ffprobe`, and `yt-dlp` are on `PATH`. The script also reports ImageMagick, a JS runtime, and `python3`, and it prints the install command for whatever is missing. Or show a dry-run and install only after you agree:

```bash
bash scripts/bootstrap.sh
bash scripts/bootstrap.sh --yes
```

One line that installs the system packages and puts yt-dlp on `PATH`. Known-good yt-dlp stable pin: **2026.08.19**. Upgrade later with `sudo yt-dlp --update-to stable` or `pipx upgrade yt-dlp`.

macOS:

```bash
brew install ffmpeg imagemagick yt-dlp deno python
```

Ubuntu / Debian:

```bash
sudo apt update && sudo apt install -y ffmpeg imagemagick python3 python3-pip python3-venv pipx curl ca-certificates nodejs && sudo curl -L "https://github.com/yt-dlp/yt-dlp/releases/download/2026.08.19/yt-dlp" -o /usr/local/bin/yt-dlp && sudo chmod a+rx /usr/local/bin/yt-dlp
```

Fedora:

```bash
sudo dnf install -y ffmpeg ImageMagick python3 python3-pip pipx curl nodejs && sudo curl -L "https://github.com/yt-dlp/yt-dlp/releases/download/2026.08.19/yt-dlp" -o /usr/local/bin/yt-dlp && sudo chmod a+rx /usr/local/bin/yt-dlp
```

Arch:

```bash
sudo pacman -S --needed ffmpeg imagemagick yt-dlp deno python python-pip python-pipx
```

deno is the preferred YouTube JS runtime. `node` is enough if you already have it. The apt and dnf lines install `nodejs` for that reason. On macOS and Arch the lines install deno.

Optional transcription, only inside a virtualenv, and only if subtitles are missing:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-asr.txt
```

Call `python3`, not `python`. Pins and the `large-v3` download size are in [`references/distill-workflow.md`](references/distill-workflow.md).

If `yt-dlp` is stuck in `~/.local/bin` and the shell cannot see it:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Quick start

```bash
export MEDIA_OUTPUT_DIR="./output"
mkdir -p "$MEDIA_OUTPUT_DIR"

# Search. Keep webpage_url so Bilibili BV/av links stay correct.
yt-dlp --flat-playlist --print "%(title)s | %(webpage_url)s" "ytsearch5:QUERY"

# Local MP3
bash scripts/audio-extract.sh input.mp4

# GIF, target size, trim
bash scripts/gif.sh input.mp4
bash scripts/compress-target-size.sh input.mp4 25
bash scripts/trim.sh input.mp4 00:00:01 00:00:05 accurate
```

Illustrative prompt, not a recorded result: ask the agent to search a topic, show candidate `webpage_url` lines, and take subtitles for the one you pick. Do not treat a sample answer as measured hardware specs.

## Docs

| File | What it answers |
| :--- | :--- |
| [`SKILL.md`](SKILL.md) | When to use the skill, and which command to run |
| [`references/yt-dlp.md`](references/yt-dlp.md) | Search, formats, subtitles, cookies, 412, bot check |
| [`references/ffmpeg.md`](references/ffmpeg.md) | CRF, target size, GIF, trim, images, hardware fallback |
| [`references/distill-workflow.md`](references/distill-workflow.md) | Search → subtitles → text the agent reads → report |
| [`references/report-template.md`](references/report-template.md) | Blank report the agent fills in |
| [`references/discovery.md`](references/discovery.md) | Optional Agent-Reach routing, X/Twitter, `sources.json` |
| [`references/troubleshooting.md`](references/troubleshooting.md) | Laptop vs VM, PATH, ImageMagick 6 vs 7, python3 |

Personal downloads on your own computer may use `--cookies-from-browser chrome|firefox|safari|edge`. Do not commit cookie files.

## Layout

```text
SKILL.md
README.md
requirements-asr.txt
scripts/doctor.sh
scripts/bootstrap.sh
scripts/download.sh
scripts/transcribe.sh
scripts/subs_to_text.sh
scripts/gif.sh
scripts/compress-target-size.sh
scripts/encode.sh
scripts/trim.sh
scripts/audio-extract.sh
scripts/image-convert.sh
scripts/optional_tools.py
references/
```

## License

[MIT](LICENSE).
