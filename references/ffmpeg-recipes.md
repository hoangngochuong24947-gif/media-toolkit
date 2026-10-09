# FFmpeg Production Recipes & Technical Reference

Curated, cross-platform production recipes for modern video, audio, and animation processing across macOS, Linux, and Windows.

---

## 1. PaletteGen High-Quality GIF Pipeline

Standard `ffmpeg -i input.mov output.gif` produces 256 generic web-safe colors with severe color banding, motion noise, and bloated file sizes (often 50MB+).

### The Mathematical Two-Pass Approach
1. **Pass 1 (`palettegen`)**: Analyzes all frames across time, computes the statistical color histogram, and constructs a customized 256-color palette image tailored specifically to the input video.
2. **Pass 2 (`paletteuse`)**: Muxes the video against the custom palette using Bayer dithering algorithms to eliminate gradient banding while maintaining compression efficiency.

### Production Shell Script (`gif-make.sh`)
```bash
#!/usr/bin/env bash
set -euo pipefail

INPUT="${1:-input.mov}"
OUTPUT="${2:-demo.gif}"
FPS="${3:-15}"
WIDTH="${4:-1080}"

# Create a secure temporary palette file
PALETTE_FILE="$(mktemp "${TMPDIR:-/tmp}/palette_XXXXXX.png" 2>/dev/null || echo "palette_temp.png")"
trap 'rm -f "$PALETTE_FILE"' EXIT

# Pass 1: Palette extraction with differential frame analysis
ffmpeg -y -v warning -i "$INPUT" \
  -vf "fps=${FPS},scale=${WIDTH}:-1:flags=lanczos,palettegen=stats_mode=diff" \
  "$PALETTE_FILE"

# Pass 2: Palette mapping with Bayer ordered dithering
ffmpeg -y -v warning -i "$INPUT" -i "$PALETTE_FILE" \
  -filter_complex "fps=${FPS},scale=${WIDTH}:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
  "$OUTPUT"

echo "Successfully generated $OUTPUT:"
ls -lh "$OUTPUT"
```

### Parameter Rationale:
- `flags=lanczos`: Highest quality sinc-based downscaling filter (yields sharper text in terminal, code, and UI screencasts than `bicubic` or `bilinear`).
- `stats_mode=diff`: Focuses palette color allocation primarily on moving pixels across frames, preserving moving cursor and text clarity.
- `dither=bayer:bayer_scale=5`: Bayer ordered dithering avoids "worm-like" crawling artifacts common in Floyd-Steinberg dithering and compresses significantly better in GIF LZW encoding.
- `diff_mode=rectangle`: Only redraws bounding boxes of regions that changed between consecutive frames, reducing GIF file size by 30–50%.

---

## 2. Cross-Platform Hardware Acceleration Matrix

Modern GPUs and SoCs contain dedicated fixed-function media engines that encode video with near-zero CPU load and high throughput:

| Platform / Vendor | Codec | Software Encoder (CPU) | Hardware Encoder | Key Parameters |
| :--- | :--- | :--- | :--- | :--- |
| **Apple Silicon (macOS)** | H.264 / AVC | `libx264` | `h264_videotoolbox` | `-b:v 2000k -pix_fmt yuv420p` |
| **Apple Silicon (macOS)** | H.265 / HEVC | `libx265` | `hevc_videotoolbox` | `-b:v 1500k -tag:v hvc1` |
| **NVIDIA (Linux / Windows)** | H.264 / AVC | `libx264` | `h264_nvenc` | `-preset p4 -cq 24` |
| **NVIDIA (Linux / Windows)** | H.265 / HEVC | `libx265` | `hevc_nvenc` | `-preset p4 -cq 26` |
| **Intel / AMD (Linux VAAPI)** | H.264 / AVC | `libx264` | `h264_vaapi` | `-vaapi_device /dev/dri/renderD128 -vf 'format=nv12,hwupload' -qp 23` |
| **Intel (Windows / Linux QSV)** | H.264 / AVC | `libx264` | `h264_qsv` | `-global_quality 23` |
| **Universal Fallback (CPU)** | H.264 / AVC | `libx264` | — | `-crf 23 -preset slow -pix_fmt yuv420p` |

### Encoder Detection Helper:
```bash
# Check available encoders in your local ffmpeg build
ffmpeg -encoders 2>/dev/null | grep -E "(videotoolbox|nvenc|vaapi|qsv|libx264)"
```

### Quality vs. Speed Guidelines:
- **High-Fidelity Archival / Code Demos**: Software encoding (`-c:v libx264 -crf 22-24 -preset slow`) achieves the smallest bitrates with sharpest line rendering.
- **Fast Bulk Meeting / Screen Recordings**: Hardware acceleration (`videotoolbox` or `nvenc`) provides 10x–25x real-time encoding speeds with minimal battery and CPU consumption.

---

## 3. Strict Target Size Compression Formula

When preparing videos for strict file-size limits (e.g., Slack 50MB, WeChat 25MB, Discord 25MB/50MB, or Feishu 100MB):

$$\text{Bitrate}_{\text{total}} (\text{kbps}) = \frac{\text{Target Size (MB)} \times 8192}{\text{Duration in Seconds}}$$
$$\text{Bitrate}_{\text{video}} = \text{Bitrate}_{\text{total}} - \text{Bitrate}_{\text{audio}}$$

### Two-Pass Automated Shell Script (`compress-target-size.sh`):
```bash
#!/usr/bin/env bash
set -euo pipefail

INPUT="${1:?Usage: $0 <input_file> <target_size_mb> [output_file]}"
TARGET_MB="${2:?Error: Specify target size in MB}"
OUTPUT="${3:-compressed_${TARGET_MB}MB.mp4}"

# Safety margin: allocate 95% of requested limit to prevent container overhead overshoot
BUDGET_MB=$(awk -v mb="$TARGET_MB" 'BEGIN { printf "%.2f", mb * 0.95 }')

# 1. Probe input duration
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$INPUT")
if [ -z "$DURATION" ] || [ "$(echo "$DURATION <= 0" | bc 2>/dev/null || true)" = "1" ]; then
  echo "Error: Unable to determine file duration." >&2
  exit 1
fi

# 2. Compute bitrates (kbps)
AUDIO_K=96
TOTAL_K=$(awk -v mb="$BUDGET_MB" -v dur="$DURATION" 'BEGIN { printf "%d", (mb * 8192) / dur }')
VIDEO_K=$(( TOTAL_K - AUDIO_K ))

if [ "$VIDEO_K" -le 64 ]; then
  echo "Warning: Target size is too small for given video duration. Minimum video bitrate set to 64k." >&2
  VIDEO_K=64
fi

echo "Input duration: ${DURATION}s | Budget: ${BUDGET_MB}MB | Target Video: ${VIDEO_K}kbps | Audio: ${AUDIO_K}kbps"

# 3. Two-pass encoding
PASSLOG="$(mktemp "${TMPDIR:-/tmp}/ffmpeg2pass_XXXXXX")"
rm -f "$PASSLOG"

ffmpeg -y -v warning -i "$INPUT" -c:v libx264 -b:v "${VIDEO_K}k" -pass 1 -passlogfile "$PASSLOG" -an -f null /dev/null
ffmpeg -y -v warning -i "$INPUT" -c:v libx264 -b:v "${VIDEO_K}k" -pass 2 -passlogfile "$PASSLOG" -c:a aac -b:a "${AUDIO_K}k" -pix_fmt yuv420p "$OUTPUT"

rm -f "${PASSLOG}"*
echo "Compression completed: $OUTPUT"
ls -lh "$OUTPUT"
```

---

## 4. Lossless Operations Cheat Sheet

Never transcode when stream copying is possible:

```bash
# 1. Millisecond-accurate lossless trim (no re-encoding, near-instant)
# Placing -ss before -i enables fast keyframe seeking
ffmpeg -ss 00:01:15 -to 00:03:45 -i input.mp4 -c copy trimmed.mp4

# 2. Lossless audio track demuxing
# (Probe codec first: if aac -> .m4a; if mp3 -> .mp3; if opus -> .opus)
ffmpeg -i input.mp4 -vn -c:a copy extracted_audio.m4a

# 3. Fast video-only stream extraction (mute/strip audio)
ffmpeg -i input.mp4 -c:v copy -an video_no_audio.mp4

# 4. Instant container remuxing (e.g. MKV/MOV to MP4)
ffmpeg -i input.mkv -codec copy -movflags +faststart output.mp4
```

---

## 5. Audio Normalization & Enhancement

For lectures, podcasts, and recordings with uneven speech levels:

```bash
# EBU R128 two-pass loudnorm for standardized broadcast loudness (-16 LUFS for podcasts / -14 LUFS for web)
ffmpeg -i input.mp3 -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:a libmp3lame -q:a 2 normalized.mp3

# Downmix multi-channel audio to mono/stereo for speech clarity
ffmpeg -i input.mp4 -vn -c:a aac -ac 1 -b:a 96k speech_mono.m4a
```
