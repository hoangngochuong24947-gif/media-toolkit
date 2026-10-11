# Executable local media contracts

The maintained implementation is scripts/media.py, not the former Bash snippets.

## Target size

MB means 1,000,000 bytes. Initial total bitrate in bits/s:
`limit_bytes * 8 * 0.90 / duration_seconds`. Subtract configured audio bitrate
only if audio exists. Reject video bitrate below 64,000 bits/s instead of raising
it and overshooting the target.

CPU H.264 two-pass encoding isolates pass logs. If necessary, decrease bitrate
and retry, at most three attempts. Verify final size/streams/full decoding before
publication. Infeasible requests return errors with no published output. Duration,
audio rate and resolution are not automatically sacrificed.

## GIF

Generate/map a palette with Bayer dithering. Up to five width factors:
1, 0.75, 0.5, 0.3, 0.2; FPS caps: requested, 12, 10, 8, 6. Width has a minimum of
32 pixels. Report actual settings. Palette use is not a guarantee of smaller files
or no banding. Exceeding the final byte limit is a failure.

## Hardware and trimming

Explicit NVENC tries a real encode. Failure/timeout retries libx264 once.
Other hardware encoders are not selected automatically. Target-size encoding
uses CPU; a simultaneous NVENC request is rejected.

Fast trim copies streams and reports duration, subject to keyframes/preroll.
Accurate trim re-encodes, checking duration within 0.15 seconds; not millisecond
accuracy. MP3 extraction re-encodes the first audio stream and is lossy.

## Validation/publication

ffprobe checks requested streams; FFmpeg decodes staged output to a null sink.
This adds runtime and checks integrity, not appearance. Actual bytes enforce
budgets. Sources/existing outputs are never overwritten. Hard-link publication
needs a supporting filesystem; errors remain explicit.

ImageMagick converts the primary frame, auto-orients, strips EXIF/profiles,
checks geometry and decodes the result. Pixel-preserving mode rejects 16-bit
input or resizing, then compares pixels. HEIC needs a working decoder.
