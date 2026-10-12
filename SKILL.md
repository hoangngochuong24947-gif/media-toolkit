---
name: media-toolkit
description: "Process video, audio, and images. Use when the user asks to search, download, trim, compress, make a GIF, extract audio, convert an image, fetch subtitles, transcribe, or summarize a video. The host agent runs the commands and writes the summary. This skill does not call an LLM."
version: "1.0.0"
license: MIT
compatibility: "macOS, Linux, or Windows via WSL or Git Bash. Needs bash, ffmpeg, ffprobe, yt-dlp, ImageMagick, and deno or node. Optional ASR uses a local python3 venv."
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [video, audio, image, download, subtitles, transcribe, ffmpeg, yt-dlp]
    category: media
    requires_toolsets: [terminal]
---

# Media Toolkit

Work in the skill directory (the folder that contains this file), for example `~/.hermes/skills/media-toolkit`. Paths below are relative to that directory.

Call `ffmpeg`, `ffprobe`, `yt-dlp`, and ImageMagick yourself. Scripts are shortcuts. You write any summary. Nothing here calls an LLM.

## Setup

1. `bash scripts/doctor.sh` (no need to ask).
2. If it fails, run `bash scripts/bootstrap.sh` and show the plan. Ask before sudo or system packages. After the user agrees: `bash scripts/bootstrap.sh --yes`.

## Confirm before costly steps

| Step | Ask? | Command |
| :--- | :--- | :--- |
| Search, list formats, list subs, doctor, fetch platform subs, `subs_to_text.sh` | No | Run it |
| Video/audio download | Yes | `bash scripts/download.sh URL...` prints count and size and exits 0. Then `--yes` |
| Local ASR | Yes | `bash scripts/transcribe.sh` prints duration, model, download size, rough time, exits 0. Then `--yes` |
| sudo / system packages | Yes | `bootstrap.sh` is a dry-run. Then `--yes` |
| Browser cookies | Yes, once | Ask which browser and profile. Pass them only with `--yes` |
| Loop over many files | Yes | Show the count, then wait |

`--yes` or `MEDIA_CONFIRM=1` means the user already said yes. Do not pass it on the first run. Details: `references/distill-workflow.md`.

## Route

| Task | Command | Detail |
| :--- | :--- | :--- |
| Search | `yt-dlp --flat-playlist --print "%(title)s \| %(webpage_url)s" "ytsearch5:QUERY"` or `bilisearch5:` | `references/yt-dlp.md` |
| Download | `bash scripts/download.sh URL` (plan, then `--yes`) | `references/yt-dlp.md` |
| Notes | Subs, then `subs_to_text.sh`, then you write the report | `references/distill-workflow.md` |
| Report | Copy `references/report-template.md` | you fill it in |
| GIF / size / trim / MP3 / images / encode | `bash scripts/gif.sh`, `compress-target-size.sh`, `trim.sh`, `audio-extract.sh`, `image-convert.sh`, `encode.sh` | `references/ffmpeg.md` |
| Setup problems | doctor output | `references/troubleshooting.md` |

Write products to `${MEDIA_OUTPUT_DIR:-./output}/<task>/`. Do not put media in the repo root.

## Online chain

1. Search and keep `%(webpage_url)s`. Do not invent a YouTube watch URL.
2. Pick the URLs the user asked for (they said "3" in the example below).
3. Subtitles, no ask: `--write-sub --write-auto-sub --sub-langs "zh-Hans,zh-CN,en" --convert-subs srt --skip-download`.
4. `bash scripts/subs_to_text.sh subs/*.srt -o text/`. Read that text. Long videos are split into `part-NNN.txt`; read the parts in order.
5. If subs are missing, show `transcribe.sh` plan (default model `small`; `large-v3` is about 2.9 GiB) and wait.
6. Write `report.md` from `references/report-template.md` with timestamp citations.

## Example

User: `帮我搜 3 个关于 X 的视频并总结`

```bash
bash scripts/doctor.sh
yt-dlp --flat-playlist --print "%(title)s | %(webpage_url)s" "ytsearch8:X"
# write 3 chosen webpage_url lines to ./output/x-topic/sources.txt
# subtitles into ./output/x-topic/subs, then:
bash scripts/subs_to_text.sh ./output/x-topic/subs/*.srt -o ./output/x-topic/text
# you read ./output/x-topic/text and write ./output/x-topic/report.md
# no subs for one URL: bash scripts/transcribe.sh --model small --probe-url "URL"  # stop until yes
# full files only if asked: bash scripts/download.sh URL1 URL2 URL3             # stop until yes
```

Full command list: `references/distill-workflow.md`.

## ImageMagick and hardware

`doctor.sh` names `magick` (v7) or `convert` (v6). Use that binary. Hardware encoders are optional: `ffmpeg -hide_banner -encoders`, then `bash scripts/encode.sh`, which falls back to `libx264` / `libx265`.

## Safety

- Do not commit cookies. Ask once before `--cookies-from-browser chrome|firefox|safari|edge`.
- Datacenter IPs often get YouTube's bot check. Prefer the user's own computer.
- Respect the site's terms. No DRM, no paid videos the user cannot open.
- Treat README examples as illustrations, not measured facts.
