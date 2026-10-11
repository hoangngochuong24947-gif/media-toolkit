---
name: media-toolkit
description: "Use when users ask to find videos by keyword, summarize technical talks into reports, download video/audio, extract subtitles, transcribe local speech, compress or trim media, create GIFs, or batch convert images and strip metadata. Supports Chinese requests such as 找视频、视频研报、下载、提取字幕、转写、压缩、剪切、批量转图."
---

# Media Toolkit — local delivery revision

Use included scripts/media.py, resolved relative to this SKILL.md, with Python
3.10+ and argument arrays. Avoid reconstructing the former Bash snippets.

## Operating rules

1. Preserve source media. Use fresh output names in the user's deliverables
   directory, not a source repository root. The CLI isolates intermediates.
2. Run `python <skill>/scripts/media.py doctor` when readiness is unknown.
   Missing dependencies must be reported. Only the selected command's tools are
   required. Do not globally install/upgrade dependencies without authorization.
3. Use absolute paths outside the skill directory. MEDIA_FFMPEG, MEDIA_FFPROBE,
   MEDIA_MAGICK and MEDIA_YT_DLP can specify executable paths. An installation's
   tool-paths.local.json can persist a name-to-executable map (including asr-python)
   without changing global environment variables. Environment overrides win.
   Do not distribute this machine-specific profile in the portable source ZIP.
4. Completion requires exit zero AND JSON `ok: true`. Keep output receipts.
   Report actual byte size, changed dimensions/FPS, duration differences and CPU
   fallback from receipts. Validation does not certify perceptual quality.
5. Never promise fixed compression percentages, invisible degradation, 4K,
   no banding, millisecond accuracy or subsecond network completion.
6. Never read browser cookies/credential stores. Static cookies require explicit
   user supply/authorization. No unlimited retry.
7. Do not launch subagents without user authorization.
8. For topic reports/downloads, use the persistent project workflow below. State
   search scope before running; preserve the user's original request in its JSON.
   Do not silently shrink selections or cancel for lack of visible byte growth.
   A successful init/select is an accepted operation, not task completion:
   completion requires project `status: success` AND `complete: true`.

## Customer task workflow

For keyword → videos → report/download, follow [project workflow](references/customer-workflow.md).
Initialize an explicit request JSON; run bounded discovery; read candidates and
record selections with reasons; run all selected stages; read the actual verified
transcripts and author claims; publish through project report. No hidden LLM or
cloud upload is involved. Failed stages persist and require --retry-failed.
Subtitle failure automatically tries local audio ASR when enabled; model downloads
require the request's explicit allow_model_download. A failed transcription never
becomes a report from general knowledge. Project status/index records pending work.

Downloads keep source-bound `.download` directories for partial file/fragment
resume, and `.progress/current.json` plus events.jsonl for live progress. Default
download/project timeout is 1800s per subprocess (ASR command 900s, others 300s);
--timeout overrides it. Do not abort before its configured budget merely because
progress is temporarily quiet. Cancellation is not a website access failure.

## Local routing

Prefix each command with `python <skill>/scripts/media.py`.

| Intent | Arguments | Boundary |
|---|---|---|
| Probe | inspect INPUT | ffprobe JSON |
| Subtitle cleanup | subtitles INPUT.vtt -o OUTPUT.json | Cue times/numeric text preserved |
| GIF | gif INPUT -o OUTPUT.gif --max-mb 5 | Up to 5 width/FPS attempts; final byte/decode check |
| Quality compression | compress INPUT -o OUTPUT.mp4 --crf 23 | Ratio/quality depend on input |
| Target size | compress INPUT -o OUTPUT.mp4 --target-mb 25 | Decimal MB, CPU two-pass, infeasible target fails |
| Hardware | compress INPUT -o OUTPUT.mp4 --encoder auto | NVENC/VideoToolbox/QSV/VAAPI runtime attempts; CPU fallback recorded |
| H265 | compress INPUT -o OUTPUT.mp4 --codec h265 --encoder nvenc | Hardware failure falls back to libx265; byte budgets use CPU H264 |
| Audio | audio INPUT -o OUTPUT.mp3 | First stream, lossy MP3 encoding |
| M4A | audio INPUT -o OUTPUT.m4a --format m4a | AAC encoding is lossy |
| Audio copy | audio INPUT -o OUTPUT.m4a --format m4a --copy | AAC/ALAC only; packet hashes must match |
| Accurate trim | trim INPUT -o OUTPUT.mp4 --start 1.3 --end 3.1 --mode accurate | Re-encode, duration tolerance 0.15 s |
| Fast trim | trim INPUT -o OUTPUT.mp4 --start 1.3 --end 3.1 --mode fast | Stream copy, no precise boundaries |
| Image/privacy | image INPUT -o OUTPUT.webp --max-side 1920 | Primary frame, auto-orient, strip/check EXIF/profiles |
| Pixel-preserving WebP | image INPUT.png -o OUTPUT.webp --lossless | <=8-bit, no resizing, verified pixel identity |
| Batch images | images INPUT_DIR -o OUTPUT_DIR [--recursive] | Collision preflight, per-item failures, verified resume; settings must match |
| Evidence report | report CLAIMS.json -o REPORT.md | Host-authored claims, exact quote/time/number checks; no semantic certification |

`--timeout SECONDS`, `--tool-config PROFILE.json`, `--progress-dir DIR` precede
the subcommand. Profiles may use paths relative to the profile directory.
Existing output/receipt files are refused. Image/GIF encoding and resizing may
change appearance. Metadata stripping does not remove visible faces/text/context.

## Online preview

### Keyword collection and multi-video requests

For related videos, collect-all requests or topic reports, do not silently pick
one video. Use `collect QUERY -o JOB_DIR [--query ALIAS] --js-runtime node`.
Defaults: 500 unique videos, 50 per slice, 20 slices per invocation. It enumerates
available keyword search results with ytsearchall and merges video IDs.
Increase `--max-videos` / `--max-pages` to continue the same saved job.
The Chinese offline index.html, videos.csv and atomic state.json are outputs.
Multiple queries rotate fairly, including across resumptions. --sort date uses
YouTube date ordering; relevance is default. Date ordering is not a date cutoff.
Use an empty directory for a new job; reuse it to resume unchanged queries.
Prefer D: for deliverables when the user requests it; record the path in the
workspace handoff. Source files stay in their checkout.

`source_exhausted` means the recorded search returned no more entries, NOT
complete YouTube topic coverage. Limits/errors are partial. Rankings can shift
during resume. Report query, count, coverage boundary and stop reason.

Use `batch JOB_DIR --stage subtitles --limit 10 --languages en --js-runtime node`
next. Repeated `--video-id ID` selects items; reruns skip artifacts only after
receipt/hash verification. Failures persist; retry requires `--retry-failed`.
Rate/access/network failures stop the batch. A killed worker can leave .job.lock;
verify its PID has exited before removing this one lock. Preserve damaged files.

Bulk official-only downloads require a verified channel identity and explicit
selection: `batch JOB_DIR --stage download --channel-id UC... --limit 5`.
Each candidate's channel ID is fetched before downloading. A display name or
allowlist is not by itself proof of official status.

The catalog is not a technical report. Synthesize actual transcripts across the
selected videos, compare claims, cite URLs/timestamps and disclose items that
were not processed. Metadata-only discovery is never transcript synthesis.

- search QUERY --platform youtube|bilibili --count 5 [--js-runtime node]
- download URL -o OUTPUT.mp4 [--cookies FILE] [--js-runtime node]
- fetch-subs URL -o OUTPUT.json [--languages en] [--cookies FILE] [--js-runtime node]

Inspect candidates before claiming authority: first hit is not necessarily
official. Site/network/access and current yt-dlp runtime support determine
success. Best available streams do not imply 4K. No all-site count is validated.
Return acquisition failures clearly and preserve structured errors.

## Lecture synthesis boundary

Try fetch-subs. With no transcript, do not create a purported video-derived
report from general knowledge. Optional local ASR is now implemented separately:
`download-audio URL -o OUT.wav`, then `transcribe INPUT -o OUT.json --model small
--language en --cache-dir CACHE_DIR [--hotwords TERMS]`.
MEDIA_ASR_PYTHON points to a dedicated interpreter with requirements-asr-lock.txt.
The tested profile is Windows CPU/int8 with Python 3.13. No global installs.
Model downloads are disabled unless `--allow-model-download` is explicit.
Implementation/test authorization permits isolated test dependencies and models;
cloud APIs still require separate authorization for transfer/cost.
Keep local ASR separate from platform captions; neither accuracy nor superiority
is guaranteed. Preserve raw cues and uncertainties, never silently fix numbers.

The host agent may summarize a reliable transcript with time anchors and source
links. Use report to publish authored claims with traceable support; see
references/capability-parity.md for the claims schema. Separate speaker claims,
agent inference and external verification.
Preserve transcript JSON and processing receipts. Do not extract screenshots
unless requested. This is an agent workflow, not automatic report generation.

Optional compatible API: transcribe-api INPUT -o OUTPUT.json --endpoint URL
--allow-network [--model MODEL] [--language en]. Remote endpoints require
MEDIA_ASR_API_KEY and HTTPS; HTTP is loopback-only. Audio transfer/cost requires
user authorization. Input <=25 decimal MB; valid timed segments required.
No redirects, implicit uploads, key printing, or cloud accuracy certification.

References: [local contracts](references/ffmpeg-recipes.md),
[transcript workflow](references/distill-workflow.md).
