# Troubleshooting

Run `bash scripts/doctor.sh` first. It names the missing tool and prints an install command. Required for exit 0: `ffmpeg`, `ffprobe`, and `yt-dlp` on `PATH`.

Search, subtitle download, and doctor do not need a confirmation. System packages, full media downloads, local ASR, browser cookies, X login credentials, Agent-Reach install, an account lookup (`person.sh`), and batch loops do. See the table in `SKILL.md`. `bootstrap.sh`, `download.sh`, `transcribe.sh`, and `person.sh` print a plan and exit 0 until `--yes`. A missing `agent-reach` command does not fail doctor.

## Where you are running

| Place | What works | What fails |
| :--- | :--- | :--- |
| Your own macOS or Linux machine | ffmpeg, ImageMagick, yt-dlp, `--cookies-from-browser` | Nothing special if doctor is green |
| Windows | Use WSL (apt one-liner) or Git Bash with the Windows builds on `PATH`. doctor prints a `winget` line on Git Bash. | Do not expect bash scripts to run in `cmd.exe` |
| Cloud VM or datacenter | Local ffmpeg recipes (trim, GIF, compress, images) | YouTube "confirm you're not a bot", Bilibili HTTP 412. Cookies from a browser that can play the video, or run yt-dlp on your own computer |

A VM that can run `ffmpeg -f lavfi -i testsrc` can still be blocked by YouTube. That block is an IP check, not a broken install.

## PATH

| Symptom | Fix |
| :--- | :--- |
| `yt-dlp` exists at `~/.local/bin/yt-dlp` and doctor warns | `export PATH="$HOME/.local/bin:$PATH"` and add the same line to `~/.bashrc` or `~/.zshrc` |
| pipx says it installed yt-dlp, shell cannot find it | `python3 -m pipx ensurepath`, then open a new shell |
| deno installer finished, `deno` not found | `export PATH="$HOME/.deno/bin:$PATH"` |
| doctor is green in one terminal and red in another | The second terminal has a different `PATH`. Open a new shell after editing the rc file |

Install yt-dlp onto `PATH` on purpose: `/usr/local/bin/yt-dlp`, `brew install yt-dlp`, or pipx plus `ensurepath`. A copy that only lives in a virtualenv the agent did not activate is invisible.

Known-good stable pin: **2026.08.19**. Upgrade: `sudo yt-dlp --update-to stable` or `pipx upgrade yt-dlp`.

## ImageMagick 6 vs 7

| doctor line | Binary | Example |
| :--- | :--- | :--- |
| `magick (v7)` | `magick` | `magick in.png -strip out.jpg` |
| `convert (v6)` | `convert` | `convert in.png -strip out.jpg` |

Ubuntu's `imagemagick` package is v6 (`convert`, `mogrify`). Homebrew's formula is v7 (`magick`). Do not tell the user to run `magick` when only `convert` exists. `scripts/image-convert.sh` chooses.

`convert` on some corporate images is blocked by ImageMagick policy for PDF/PS. PNG and JPEG still work. This skill does not need PDF input.

## python3, not python

Transcription and `scripts/optional_tools.py` use `python3`. On macOS, `python` may be missing or may be Python 2 on old machines. On Debian/Ubuntu, `python` is often not installed even when `python3` is.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-asr.txt
```

`requirements-asr.txt` must stay in git. A `.gitignore` rule of `*.txt` would hide it; this repo does not use that rule.

If `python3 -m venv` fails, install the venv package (`sudo apt install -y python3-venv`) and retry. Do not fall back to bare `python`.

## YouTube and Bilibili

| Message | Read this |
| :--- | :--- |
| confirm you're not a bot | `references/yt-dlp.md` cookies section. Expected on many VMs. |
| HTTP 412 | Bilibili anti-bot. Cookies, referer, user-agent, update yt-dlp, slow down. |
| HTTP 429 | Slow down. |
| nsig / signature | Update yt-dlp and install deno. |
| Empty `webpage_url` in a flat search | Re-run that query without `--flat-playlist`. Do not build a YouTube URL from the id. |

## ffmpeg encode fell back

`ffmpeg -hide_banner -encoders` lists encoders compiled into the binary. NVENC still fails when `libcuda.so.1` is absent. VAAPI fails without `/dev/dri/renderD128`. `scripts/encode.sh` treats that as a failed attempt and uses `libx264` or `libx265`.

## GIF palette was empty

The palette pass must include `-update 1` (and `-frames:v 1`). `scripts/gif.sh` does. A hand-written command that omits `-update 1` can leave a missing or stale palette on current ffmpeg.
