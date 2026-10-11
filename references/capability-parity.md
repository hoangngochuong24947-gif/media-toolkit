# Capability additions in 0.4.0-local

This remains an agent skill and executable CLI, not a standalone application.

## Audio

`audio INPUT -o OUT.m4a --format m4a --copy` copies the first AAC/ALAC audio
stream and compares every packet SHA256 before publication. Incompatible codecs
fail with lossless_unavailable. Default MP3 and non-copy M4A are lossy encoding.
Copy means no additional encoding loss; source audio may already be lossy.

## Hardware

`compress INPUT -o OUT.mp4 --encoder cpu|auto|nvenc|qsv|vaapi|videotoolbox
--codec h264|h265`. Auto tries VideoToolbox on macOS; NVENC then QSV on Windows;
NVENC, VAAPI, QSV on Linux; CPU last. Explicit hardware tries CPU after failure.
VAAPI uses `--hw-device /dev/dri/renderD128` by default. VideoToolbox disables
its own software fallback, so actual.encoder tells the truth. CRF/quality values
have backend-specific meanings; VideoToolbox uses 2 Mbps. Hardware selection
does not imply perceptual equivalence or a fixed speedup. Target-size mode
requires CPU H264. Decode validation follows each attempt; receipts retain
failure details and fallback status.

## Image batch

`images INPUT_DIR -o OUTPUT_DIR [--recursive] [--lossless] [--retry-failed]`.
The new output directory must be empty and outside the source directory tree.
Duplicate output stems are rejected before conversion. Same source/settings can
resume: source SHA256, output SHA256 and per-file receipt must match. Changed
or damaged files are preserved and failed; choose a new directory to regenerate.
Failures persist; retry-failed explicitly retries them. Successful files remain
available when another item fails; command status partial and exit nonzero.
HEIC requires an ImageMagick decoder; only primary frames are processed.

## Evidence report

The host agent reads transcripts and writes a claims JSON; the CLI validates
evidence and assembles Markdown. It does not infer prose independently.

```json
{
  "title": "Video report",
  "coverage": "Actually read sources and excluded candidates",
  "claims": [{
    "statement": "Speaker reports 128GB memory.",
    "transcript": "transcript.json",
    "subtitle": 0,
    "cue": 3,
    "quote": "128GB memory",
    "kind": "speaker"
  }],
  "limitations": "Caption uncertainties and missing verification"
}
```

Transcript paths are relative to the claims file or absolute. For fetch-subs,
subtitle selects the language document; otherwise cues are top-level. Quote
must occur verbatim in the chosen cue. Statement numeric tokens must occur in
the quote. The report includes timestamps, transcript hashes and source links;
kind is speaker or inference. These checks establish traceability, not semantic
entailment, source authority, scientific validity or ASR correctness.
The host must check units, context, cross-source contradictions and conclusions.

## Compatible API ASR

`transcribe-api INPUT -o OUT.json --endpoint https://HOST/audio/transcriptions
--allow-network [--model whisper-1] [--language en]`.
Set MEDIA_ASR_API_KEY locally; never pass keys as command arguments. Explicit
authorization is needed for audio transfer and possible charges. A loopback
HTTP endpoint may run without a key. Input <=25 decimal MB. Standard multipart
file/model/language/verbose_json fields; response must contain valid timed
segments. No redirects. HTTP failures do not expose response bodies or keys.
Tests use an isolated local mock; a real cloud service still needs acceptance.
