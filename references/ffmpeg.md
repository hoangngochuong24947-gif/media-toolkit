# ffmpeg and ImageMagick

Recipes for files already on disk. Downloads are in `yt-dlp.md`. Every output path below goes to `${MEDIA_OUTPUT_DIR:-./output}` unless you pass another path.

Scripts are shortcuts. The same flags work when you call ffmpeg yourself.

## What this will and will not do

ffmpeg can re-encode, cut, concat, burn subtitles, and measure loudness. It cannot invent detail: scaling a 480p frame to 1080p does not add real resolution. It cannot undo heavy compression, and it cannot strip DRM. `loudnorm` cannot repair audio that was already clipped to distortion.

## CRF and preset

CRF is quality, not a file size. Lower CRF is higher quality and a larger file. `slow` spends more CPU for a smaller file at the same CRF. Hardware encoders often have no real CRF; they use a bitrate or a vendor quality knob, and they are optional.

| Goal | Codec | Starting point |
| :--- | :--- | :--- |
| Screen recording, code, UI text | libx264 | `-crf 20 -preset slow -pix_fmt yuv420p` |
| General video | libx264 | `-crf 23 -preset medium -pix_fmt yuv420p` |
| Smaller archival | libx265 | `-crf 28 -preset medium -pix_fmt yuv420p -tag:v hvc1` |
| Fast, good enough | libx264 | `-crf 23 -preset veryfast -pix_fmt yuv420p` |

```bash
OUT="${MEDIA_OUTPUT_DIR:-./output}"
mkdir -p "$OUT"
ffmpeg -nostdin -i input.mov -c:v libx264 -crf 23 -preset slow -pix_fmt yuv420p \
  -c:a aac -b:a 128k "$OUT/compressed.mp4"
```

## Target size (two pass)

```text
video_kbps = (target_mib * 0.95 * 8192 / duration_seconds) - audio_kbps
```

`scripts/compress-target-size.sh` computes that with awk (not `bc`) and runs two libx264 passes. Audio is 96 kbps AAC. The script refuses to overwrite the output.

```bash
bash scripts/compress-target-size.sh input.mp4 25
# explicit output:
bash scripts/compress-target-size.sh input.mp4 25 "${MEDIA_OUTPUT_DIR:-./output}/under-25.mp4"
```

If the video bitrate would fall under 64 kbps, the clip is too long for that budget. Cut it first or raise the budget.

## Trim: fast vs accurate

Fast copy cuts on keyframes. The start can land earlier than you asked. Accurate mode re-encodes so the cut follows the timestamps.

```bash
# Fast. -ss before -i. Near-instant. Keyframe aligned.
bash scripts/trim.sh input.mp4 00:01:15 00:03:45 fast

# Accurate. Decode, then cut.
bash scripts/trim.sh input.mp4 75 225 accurate
```

Raw commands:

```bash
OUT="${MEDIA_OUTPUT_DIR:-./output}"
ffmpeg -nostdin -ss 00:01:15 -to 00:03:45 -i input.mp4 -c copy "$OUT/fast.mp4"
ffmpeg -nostdin -i input.mp4 -ss 00:01:15 -to 00:03:45 \
  -c:v libx264 -crf 18 -preset veryfast -pix_fmt yuv420p -c:a aac -b:a 128k \
  "$OUT/accurate.mp4"
```

## GIF

A one-step `output.gif` uses a generic palette and bands. Generate a palette, then use it. `-update 1` is required so the single palette frame is actually written.

```bash
bash scripts/gif.sh input.mp4 "${MEDIA_OUTPUT_DIR:-./output}/demo.gif" 15 1080
```

The script runs:

```bash
ffmpeg -nostdin -y -i "$INPUT" \
  -vf "fps=15,scale=1080:-1:flags=lanczos,palettegen=stats_mode=diff" \
  -frames:v 1 -update 1 "$PALETTE"
ffmpeg -nostdin -y -i "$INPUT" -i "$PALETTE" \
  -filter_complex "fps=15,scale=1080:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
  -an "$OUTPUT"
```

`stats_mode=diff` spends palette entries on what moves. `dither=bayer` avoids the crawling look of error-diffusion and compresses better. `diff_mode=rectangle` redraws changed rectangles. If the GIF is too big, lower fps, then width, then trim the clip.

## Audio

Local files are encoded to MP3, same as the skill default. Stream-copy is a different request; do not label a copy as MP3.

```bash
bash scripts/audio-extract.sh input.mp4
# same command:
ffmpeg -nostdin -i input.mp4 -vn -c:a libmp3lame -q:a 2 "${MEDIA_OUTPUT_DIR:-./output}/output.mp3"
```

Speech loudness (EBU R128, about -16 LUFS):

```bash
ffmpeg -nostdin -i input.mp3 -af loudnorm=I=-16:TP=-1.5:LRA=11 \
  -c:a libmp3lame -q:a 2 "${MEDIA_OUTPUT_DIR:-./output}/normalized.mp3"
```

## Subtitles

Soft subtitles stay as a track. Burned subtitles are pixels and cannot be turned off.

```bash
OUT="${MEDIA_OUTPUT_DIR:-./output}"
ffmpeg -nostdin -i input.mp4 -i captions.srt -c copy -c:s mov_text "$OUT/soft.mp4"
ffmpeg -nostdin -i input.mp4 -vf "subtitles=captions.srt" -c:a copy "$OUT/burned.mp4"
```

## Concat and scale

Concat with `-c copy` only works when the streams match (codec, size, frame rate, audio layout).

```bash
printf "file '%s'\nfile '%s'\n" "$PWD/a.mp4" "$PWD/b.mp4" > "${MEDIA_OUTPUT_DIR:-./output}/list.txt"
ffmpeg -nostdin -f concat -safe 0 -i "${MEDIA_OUTPUT_DIR:-./output}/list.txt" -c copy "${MEDIA_OUTPUT_DIR:-./output}/joined.mp4"
```

`-2` keeps the aspect ratio and an even dimension for yuv420p:

```bash
ffmpeg -nostdin -i input.mp4 -vf "scale=1280:-2" -c:a copy "${MEDIA_OUTPUT_DIR:-./output}/scaled.mp4"
```

## Hardware encoders

Detect, do not assume:

```bash
ffmpeg -hide_banner -encoders | awk '/nvenc|vaapi|qsv|videotoolbox|libx264 |libx265 /'
```

| Name in `-encoders` | Typical machine | Notes |
| :--- | :--- | :--- |
| `h264_videotoolbox` / `hevc_videotoolbox` | macOS | Optional. `-b:v` more than CRF. |
| `h264_nvenc` / `hevc_nvenc` | NVIDIA driver + GPU | Optional. Fails if `libcuda` is missing. |
| `h264_vaapi` / `hevc_vaapi` | Linux DRM render node | Needs `/dev/dri/renderD128` and a hwupload filter. |
| `h264_qsv` / `hevc_qsv` | Intel Quick Sync | Optional. A listed encoder can still fail with no GPU. |
| `libx264` / `libx265` | CPU | Always the fallback. |

`scripts/encode.sh` tries a listed hardware encoder and, on failure, encodes with libx264 or libx265. A name in the encoder list is not a successful encode.

```bash
bash scripts/encode.sh input.mp4 "${MEDIA_OUTPUT_DIR:-./output}/encoded.mp4" h264
```

## ImageMagick 6 and 7

`scripts/doctor.sh` prints `magick` (v7) or `convert` (v6). Use that binary. `scripts/image-convert.sh` does the same choice.

```bash
# v7
magick input.png -auto-orient -resize "1920x1920>" -strip -quality 82 "${MEDIA_OUTPUT_DIR:-./output}/out.jpg"
# v6
convert input.png -auto-orient -resize "1920x1920>" -strip -quality 82 "${MEDIA_OUTPUT_DIR:-./output}/out.jpg"
```

`-strip` removes EXIF and GPS. `1920x1920>` only shrinks. Batch on v7 is `magick mogrify ...`. On v6 it is `mogrify ...`. Prefer the single-file script unless the user asked for a whole directory, because `mogrify` overwrites.

Probe:

```bash
ffprobe -v error -show_entries stream=codec_name,width,height,duration,bit_rate -of default=noprint_wrappers=1 input.mp4
```
