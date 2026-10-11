# Transcript acquisition and agent synthesis

The CLI implements acquisition/parsing, not automatic research reports.
It can publish host-authored Markdown claims with exact evidence checks:
`report CLAIMS.json -o REPORT.md`. See capability-parity.md for the schema.

```powershell
python scripts/media.py fetch-subs 'VIDEO_URL' -o output/subtitles.json --languages en --js-runtime node
python scripts/media.py subtitles local.vtt -o output/local-transcript.json
```

The parser recognizes cue timestamps instead of deleting digit-leading lines.
Dialogue numbers survive. Tags/entities are cleaned. Repeated complete lines
are removed between adjacent overlapping cues and recognizable touching rolling
frames; real consecutive single-line repetition is preserved. Source cues/timestamps are
preserved alongside cleaned text. This conservative algorithm cannot fix every
rolling caption, speaker change or transcription error; review remains necessary.

If acquisition fails due to rate limit, login, TLS or formats, return its error,
not a plausible summary. No subtitle file is not proof of absence of speech.
Do not read browser credentials. Static cookies require explicit authorization.
Do not retry forever.

Whisper is a separate opt-in step: additional backend, model download and possible
GPU compatibility checks. APIs may require keys, external data transfer and cost.
The local optional worker is shipped; models/libraries are not automatically
installed. Use the pinned requirements-asr-lock.txt with Python 3.13 and a
dedicated interpreter. Pin PyAV 16.1.0 for faster-whisper 1.2.1 compatibility.
The first model download is explicit; cached inference can run locally.
Use download-audio for audio-only acquisition. If it fails, preserve the failure;
an already authorized/downloaded local video can be used directly as ASR input.

For topic requests, use collect then batch; a single-video summary does not fulfill
a multi-video request. The collection checkpoint distinguishes resource limits,
network failures and available-search exhaustion. None proves full-platform coverage.
Report all discovered candidates, those actually read, and those excluded/failed.

With a real transcript, the host agent can provide:

1. Source URL/file, transcript path and indication of automatic captions.
2. Speaker's actual problem, proposal and conclusions.
3. Timestamped claims and quantitative results with units/context.
4. Separate speaker statements, inference and externally verified facts.
5. Recognition uncertainties/missing sections; no screenshots unless requested.

Transcript extraction does not establish scientific validity. Preserve source
JSON and receipts with any resulting notes.
