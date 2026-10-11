# 0.5.0-local source contribution candidate

This is a source-only contribution for upstream review, not an upstream release.
It preserves the original Git history and MIT license. No portable runtime,
model weights, downloaded media, cookies, local tool profile or backup is included.

The executable source matches the accepted 0.5.0-local snapshot. See README.md
for source installation, capabilities and examples, and validation/summary.json
for the test scope. The previously tested Windows portable package is a separate
local delivery artifact; this PR does not distribute it or link to private assets.

Validation recorded 94 source tests and 94 relocated Windows-package tests, with
zero skips, plus actual HTTP range resume, local Chinese ASR and one complete
YouTube transcript/download/report workflow. Physical clean-client installation,
actual cloud transcription and macOS/Linux hardware acceleration remain unverified.
Reports are authored by the host AI; citation checks do not certify scientific or
speech-recognition accuracy. Third-party runtime components retain their own licenses.
