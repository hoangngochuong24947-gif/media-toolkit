---
name: media-toolkit
description: "Process, distill, compress, and download audio/video/images using ffmpeg, yt-dlp, and ImageMagick (magick). Use when the user wants to: (1) distill technical talks or lectures into markdown notes or transcripts; (2) convert screen recordings (.mov/.mp4) into high-quality, lightweight GIFs for GitHub READMEs or PRs; (3) compress large screen recordings or meetings without visible quality loss; (4) extract clean audio/mp3 from videos or links for podcasts; (5) download videos or audio streams from 1800+ sites (Bilibili, YouTube, X, etc.); (6) trim, transcode, or inspect media files with ffprobe; or (7) batch convert images (HEIC -> WebP), resize, compress, and strip EXIF/GPS metadata via magick."
---

# Media Toolkit

The universal multimedia automation toolkit powered by `ffmpeg`, `yt-dlp`, and `magick`. Operates across 7 dedicated branches to transform unstructured video/audio/image assets into clean knowledge artifacts, publication-ready project assets, and shareable media files.

## Invariant Foundations & Environment

- **Core Executables (Dynamic PATH Detection)**:
  - `ffmpeg` & `ffprobe`: Discovered dynamically via `command -v ffmpeg` and `command -v ffprobe`. Leverages system hardware acceleration when available:
    - **macOS (Apple Silicon / Intel)**: `h264_videotoolbox` / `hevc_videotoolbox`
    - **NVIDIA GPU (Linux / Windows)**: `h264_nvenc` / `hevc_nvenc`
    - **Intel / AMD (Linux VAAPI / QSV)**: `h264_vaapi` / `h264_qsv`
    - **Universal Fallback (CPU)**: `libx264` / `libx265`
  - `yt-dlp`: Discovered dynamically via `command -v yt-dlp`. Keep up-to-date via package manager or `yt-dlp -U`.
  - `magick`: Discovered dynamically via `command -v magick` (ImageMagick v7, built-in libheif for iPhone HEIC decoding and libwebp for WebP encoding).
- **Workspace Hygiene (Clean Root Standard)**:
  - All temporary downloads, raw caches, and intermediate palettes MUST reside in designated scratch directories (e.g., `${TMPDIR:-/tmp}` or `$MEDIA_OUTPUT_DIR/scratch/`).
  - **Strict Prohibition**: Never write raw media files or temporary video clips into repository root directories.
  - Set `MEDIA_OUTPUT_DIR` (e.g. `export MEDIA_OUTPUT_DIR="./output"`) to control target artifacts location. Defaults to `./output` or current directory.

---

## Routing Matrix

Identify the user intent and execute the corresponding branch:

| Intent | Leading Trigger Words | Target Output | Branch |
| :--- | :--- | :--- | :--- |
| **技术演讲省流蒸馏** | 视频总结, 讲座笔记, 提取字幕, 演讲提炼, distill talk | Markdown 结构化研报 / 知识卡片 | [Branch 1](#branch-1-technical-talk-distillation-视频讲座省流蒸馏) |
| **开源 Demo 动图** | 录屏转gif, demo gif, 演示动图, PR动图, make gif | 高清超清循环 GIF (<5MB / <10MB) | [Branch 2](#branch-2-high-aesthetic-demo-gif-录屏制作高清-gif) |
| **视频脱脂瘦身** | 压缩视频, 录屏压缩, 会议视频太大了, 视频瘦身 | 高画质低体积 MP4 (压缩率 70-90%) | [Branch 3](#branch-3-video-slimming--compression-录屏与会议脱脂瘦身) |
| **随身播客化** | 提取音频, 抽mp3, 通勤听, podcast, audio extract | 独立 MP3/M4A 音频文件 | [Branch 4](#branch-4-podcast--audio-extraction-随身播客化与音频提取) |
| **全网视频抓取** | 下载视频, download video, bilibili, youtube | 1080P/4K 无损封装 MP4 | [Branch 5](#branch-5-stream-download-全网音视频下载) |
| **无损剪切与体检** | 剪切视频, 视频截取, ffprobe, 诊断视频格式, 旋转 | 秒级剪切片段 / 媒体元数据报告 | [Branch 6](#branch-6-lossless-trimming--diagnostics-精准剪切与体检) |
| **图像批处理与脱敏** | heic转webp, 批量转图, 抹掉GPS, 压图, magick, 转换webp | 高画质脱敏 WebP / 图像套件 | [Branch 7](#branch-7-batch-image-processing--privacy-scrubbing-图像批处理与隐私脱敏) |

---

## Branch 1: Technical Talk Distillation (视频/讲座省流蒸馏)

When user provides a link to a conference talk, keynote, or technical interview and wants a concise distillation:

### 🌟 Core Execution Invariants
1. **默认不截图（Zero Screenshots by Default）**：
   - 除非用户当次明确提出“帮我截图/配几张图”，否则**严禁主动从视频抽帧或插入截图**。
2. **核心交付物聚焦字幕与内容推演**：
   - 第一优先级：提取平台原声字幕（软字幕直下）；若无字幕，匿名提取音频流并交由本地 `faster-whisper` 或 OpenAI-compatible Whisper API 转写。
   - 核心任务：对字幕内容进行结构化提炼，紧扣演讲人核心论点、技术架构、反直觉推论与量化指标，输出高信息密度的 Markdown 研报与时间戳纪要。

### 🛡️ Zero-Keychain Popup Invariant (系统弹窗免打扰军规)
- **严格禁令**：**严禁使用 `--cookies-from-browser chrome`**！
  - *原因*：在 macOS / Linux GUI 环境下，读取浏览器 Cookies 会唤起系统 Keychain / 凭据存储密码弹窗（例如请求访问 `Chrome Safe Storage`），导致自动化流程中断并严重打扰用户。
- **纯净免密下载**：Bilibili、YouTube 等公网视频/音频流完全支持匿名抓取，默认绝不追加任何 cookie 参数。
- **受限内容静态降级**：若必须使用 Cookie（如大会员 4K/私有视频），一律读取用户提供的静态文本文件：`--cookies "${COOKIE_FILE:-~/.config/yt-dlp/cookies.txt}"`，读取纯文本绝不弹窗。

---

### Step-by-Step Distillation Flow:

1. **Lightweight Subtitle & Audio Acquisition**:
   Attempt to fetch native subtitles first without downloading heavy video media:
   ```bash
   OUT_DIR="${MEDIA_OUTPUT_DIR:-./output}"
   mkdir -p "$OUT_DIR"

   # Check & fetch native subtitles (SRT / VTT)
   yt-dlp --write-sub --write-auto-sub --sub-lang "zh-Hans,zh-CN,en,en-US" --skip-download -P "$OUT_DIR" "<URL>"
   ```
   If no subtitles are available, fetch the pure audio track anonymously:
   ```bash
   yt-dlp -x --audio-format m4a -P "$OUT_DIR" -o "talk_audio.%(ext)s" "<URL>"
   ```

2. **Transcription & Parsing**:
   - For subtitle files: Parse timestamped dialogue, strip VTT cues and formatting markup into clean text.
   - For audio files: Run standard local `faster-whisper` or OpenAI-compatible transcription endpoint (see [`references/distill-workflow.md`](references/distill-workflow.md)).

3. **Synthesis & Markdown Generation**:
   Compile the transcript into a high-density, anti-slop knowledge document:
   - **Executive Summary** (Core problem, proposed solution, key metrics).
   - **Technical Architecture & Core Primitives** (Mechanisms, trade-offs, algorithms).
   - **Critical Milestones & Timestamped Highlights** (e.g. `[12:35] Model routing logic`).
   - **Entity / Wikilink Extraction** (`[[Concept]]` for knowledge base linkage).

4. **Storage**:
   - Save to `${MEDIA_OUTPUT_DIR:-./output}/distill/YYYYMMDD_<topic>.md`.

---

## Branch 2: High-Aesthetic Demo GIF (录屏制作高清 GIF)

Transform rough `.mov` or `.mp4` recordings into silky, color-accurate, lightweight GIFs for GitHub READMEs, PRs, or docs.

### Two-Pass PaletteGen Pipeline (Golden Rule)
Direct conversion produces muddy colors and huge files. **ALWAYS** use the two-pass palette algorithm:

```bash
INPUT="input.mov"
OUTPUT="demo.gif"
FPS=15
WIDTH=1080  # 1080 for desktop, 720 for mobile/sub-panels

PALETTE_TMP="$(mktemp "${TMPDIR:-/tmp}/palette_XXXXXX.png" 2>/dev/null || echo "palette_temp.png")"

# Pass 1: Generate specialized color palette with diff detection
ffmpeg -y -v warning -i "$INPUT" -vf "fps=$FPS,scale=$WIDTH:-1:flags=lanczos,palettegen=stats_mode=diff" "$PALETTE_TMP"

# Pass 2: Render GIF with Bayer dithering to eliminate banding while keeping file small
ffmpeg -y -v warning -i "$INPUT" -i "$PALETTE_TMP" -filter_complex "fps=$FPS,scale=$WIDTH:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" "$OUTPUT"

rm -f "$PALETTE_TMP"
```

### Size Guardrails
- **GitHub Target**: Keep under **5MB** (or max 10MB).
- If the output exceeds 5MB:
  1. Reduce FPS to 12.
  2. Scale width down to 800px (`scale=800:-1:flags=lanczos`).
  3. Trim unnecessary lead-in/lead-out using `-ss` and `-to`.

---

## Branch 3: Video Slimming & Compression (录屏与会议脱脂瘦身)

Compress bloated screen recordings (e.g. 2GB meeting records or 500MB QuickTime videos) for seamless transmission via messaging platforms or email.

### Mode A: Constant Quality (CRF) - Best Quality/Size Balance (CPU)
Preserves razor-sharp code/text readability while dropping 70–85% file size:
```bash
# Code / Text / UI Screen Recordings (CRF 22-24, high text sharpness)
ffmpeg -i input.mov -c:v libx264 -crf 23 -preset slow -pix_fmt yuv420p -c:a aac -b:a 128k compressed.mp4
```

### Mode B: Cross-Platform Hardware Acceleration (Ultra-Fast)
For 1hr+ long recordings where encoding speed is priority:
```bash
# macOS (Apple Silicon / Intel VideoToolbox)
ffmpeg -i input.mp4 -c:v h264_videotoolbox -b:v 2000k -pix_fmt yuv420p -c:a aac -b:a 128k output_fast.mp4

# NVIDIA GPU (Linux / Windows NVENC)
ffmpeg -i input.mp4 -c:v h264_nvenc -preset p4 -cq 24 -pix_fmt yuv420p -c:a aac -b:a 128k output_fast.mp4

# Intel / AMD (Linux VAAPI)
ffmpeg -vaapi_device /dev/dri/renderD128 -i input.mp4 -vf 'format=nv12,hwupload' -c:v h264_vaapi -qp 24 -c:a aac -b:a 128k output_fast.mp4
```

### Mode C: Target Size Budget (e.g. "Compress to under 50MB")
Calculate target video bitrate using formula:
$$\text{Bitrate (kbps)} = \frac{\text{Target\_Size\_MB} \times 8192}{\text{Duration\_Seconds}} - \text{Audio\_Bitrate(96)}$$
See [`references/ffmpeg-recipes.md`](references/ffmpeg-recipes.md) for the automated two-pass script.

---

## Branch 4: Podcast & Audio Extraction (随身播客化与音频提取)

Convert talks, interviews, and roundtables into pure audio files for commute listening:

```bash
OUT_DIR="${MEDIA_OUTPUT_DIR:-./output}"

# From Web URL directly (extracts native high-quality audio stream)
yt-dlp -x --audio-format mp3 --audio-quality 0 -P "$OUT_DIR" -o "%(title)s.%(ext)s" "<URL>"

# From Local Video File (lossless stream copy if already AAC, or encode to MP3)
ffmpeg -i input.mp4 -vn -c:a libmp3lame -q:a 2 "$OUT_DIR/output.mp3"
```

---

## Branch 5: Stream Download (全网音视频下载)

Download videos with optimal track selection and muxing:

```bash
OUT_DIR="${MEDIA_OUTPUT_DIR:-./output}"

# Highest quality video + highest quality audio merged into MP4
yt-dlp -f "bestvideo+bestaudio/best" --merge-output-format mp4 -P "$OUT_DIR" "<URL>"

# If platform triggers HTTP 412 or anti-crawler errors:
# 1. Update yt-dlp: yt-dlp -U (or brew/apt/winget upgrade)
# 2. If login is strictly required, use static cookies file (NEVER use --cookies-from-browser):
#    yt-dlp --cookies ~/.config/yt-dlp/cookies.txt "<URL>"
```

---

## Branch 6: Lossless Trimming & Diagnostics (精准剪切与体检)

### 1. Instant Lossless Cut (No Re-encoding, 0.1s execution)
```bash
# Keep 00:01:15 to 00:03:45 without re-encoding
ffmpeg -ss 00:01:15 -to 00:03:45 -i input.mp4 -c copy trimmed.mp4
```

### 2. Media Diagnostics (`ffprobe`)
Extract technical container, codec, resolution, and bit rate details:
```bash
ffprobe -v error -show_entries stream=codec_name,width,height,duration,bit_rate -of default=noprint_wrappers=1 input.mp4
```

---

## Branch 7: Batch Image Processing & Privacy Scrubbing (图像批处理与隐私脱敏)

Powered by `magick` (ImageMagick v7). Optimized for batch format conversion, geometry resizing, and metadata scrubbing without memory explosion.

### 1. Batch HEIC to WebP with Geometry Constraints & Privacy Scrubbing
Converts all `.heic` in the directory, scales long side to 1920 (only shrinking, never enlarging), and strips GPS/camera metadata:
```bash
magick mogrify -format webp -resize "1920x1920>" -strip -quality 82 *.heic
```

### 2. High-Fidelity Lossless WebP Compression (PNG -> WebP)
```bash
magick input.png -strip -define webp:lossless=true output.webp
```

### 3. Image Identification & Inspection
```bash
magick identify -format "%f: %m %wx%h %b\n" input.webp
```

---

## Progressive Disclosure & Reference Pointers

- Hardware acceleration matrix, target-size two-pass compression script, and lossless stream recipes: [`references/ffmpeg-recipes.md`](references/ffmpeg-recipes.md)
- Step-by-step lecture synthesis, local Whisper / API setup, and structured note schema: [`references/distill-workflow.md`](references/distill-workflow.md)
