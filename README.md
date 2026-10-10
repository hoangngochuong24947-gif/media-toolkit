# Media Toolkit

> **The universal multimedia automation toolkit for developers, researchers, and AI agents.** Powered by `ffmpeg`, `yt-dlp`, and `ImageMagick`.

`media-toolkit` provides production-grade recipes, automated shell scripts, and an AI Agent skill specification to transform unstructured video, audio, and image assets into clean knowledge artifacts, publication-ready project assets, and lightweight media files.

---
先安装本 skill，和其他 skill 一样，然后下面是相关的依赖


## 🔰 小白 3 分钟极速上手指南 (Beginner Quick Start)

即使你刚接触 AI Agent、不会复杂的配置或终端指令，也可以轻松把这个工具包接入你的 AI 助手（如 Claude Code、Codex、WorkBuddy、Cursor，甚至普通网页版 ChatGPT/Claude）。

### 第一步：你的电脑需要准备什么？（只需装一次）

这个 Skill 由三个业界最成熟的开源多媒体引擎驱动：`ffmpeg`（音视频转码）、`yt-dlp`（视频下载）、`ImageMagick`（图片处理）。请在终端/命令行窗口敲入一行对应系统的命令安装：

- **🍎 macOS 苹果电脑用户**（打开系统自带“终端”应用）：
  ```bash
  brew install ffmpeg yt-dlp imagemagick
  ```
- **🪟 Windows 用户**（按 `Win + R` 键，输入 `powershell` 回车打开）：
  ```powershell
  winget install Gyan.FFmpeg yt-dlp.yt-dlp ImageMagick.ImageMagick
  ```
- **🐧 Linux 用户**（Ubuntu / Debian）：
  ```bash
  sudo apt update && sudo apt install -y ffmpeg imagemagick && pip install --upgrade yt-dlp
  ```

---

### 第二步：如何安装到你的 AI 助手里？（挑选你正在用的工具）

#### 方案 1：Claude Code / Antigravity 用户
在终端执行克隆，直接装进官方 Skill 目录：
```bash
# Claude Code 技能目录：
git clone https://github.com/hoangngochuong24947-gif/media-toolkit.git ~/.claude/skills/media-toolkit

# Antigravity 技能目录：
git clone https://github.com/hoangngochuong24947-gif/media-toolkit.git ~/.gemini/config/skills/media-toolkit
```

#### 方案 2：Codex / WorkBuddy / CodeBuddy 用户
大部分 Agent 工具默认认 `~/.agents/skills/` 目录：
```bash
git clone https://github.com/hoangngochuong24947-gif/media-toolkit.git ~/.agents/skills/media-toolkit
```
*💡 如果不习惯敲命令：直接点击 GitHub 页面右上角的绿色按钮 **`Code` -> `Download ZIP`**，解压后把整个 `media-toolkit` 文件夹拖进你项目工程里的 `.agents/skills/` 目录即可。*

#### 方案 3：Cursor / Windsurf / VSCode 用户
把解压后的 `media-toolkit` 文件夹直接复制到你当前的项目根目录下，在聊天对话框里跟 AI 说：
> “请严格参照项目中 `media-toolkit/SKILL.md` 的规范来帮我下载、压缩或处理多媒体文件。”

#### 方案 4：普通网页版用户（ChatGPT / Claude / DeepSeek 网页端，无本地 Agent 也能用！）
直接打开本仓库中的 [`SKILL.md`](SKILL.md) 文件，把全部文字复制粘贴给网页里的 AI，并对它说：
> “你现在是专业音视频自动化专家，请阅读以上规范。请按照这份规范里的最佳命令，帮我处理以下视频需求……”

---

### 第三步：真实案例实战 —— 怎么一句话触发它？

以一个最实用的日常场景为例：**“听说英伟达发布了新硬件 DGX Spark，想让 AI 去 YouTube 找视频，整理一份技术研报并下载最高画质视频”**。

你只需要在聊天框对你的 AI Agent 发送这**一句话**：

> 💬 **触发提示词（Prompt 模板）：**  
> **“帮我在 YouTube 上找一下 NVIDIA DGX Spark 相关的视频，用媒体处理工具提取字幕做一份技术省流研报，并把官方最高画质视频下载下来。”**

#### AI 接到指令后会自动完成全套动作：
1. **自动搜索定位**：AI 会自动执行 `ytsearch5:NVIDIA DGX Spark` 快速列出候选，无需你手动去网页找链接。
2. **零成本极速蒸馏**：AI 不下载沉重的完整视频，而是 1 秒内抓取原声字幕，自动总结出：
   - 核心硬件规格：20 核 ARM CPU、Blackwell GPU（6,144 核心）、128GB 统一显存、1 PFLOP 算力；
   - 自动生成结构化的 Markdown 深度学习研报。
3. **最高画质无损抓取**：AI 会自动调度 `yt-dlp` 将最佳画质视频轨与音频轨无损合并为 4K UHD 的 MP4 视频存入下载目录。

全程无需你手动找链接、换下载器，真正实现“动动嘴皮子，产物全到手”！

---

## 🌟 Core Engineering Principles

1. **🛡️ Zero-Keychain Popup Invariant**:
   - Automated pipelines and background agents strictly avoid `--cookies-from-browser` to prevent OS modal prompts (`Chrome Safe Storage` / Keychain access) that stall unattended execution.
   - Public streams are downloaded anonymously without cookies. Restricted streams accept static text cookie files (`--cookies cookies.txt`).
2. **🎨 Mathematical Two-Pass PaletteGen GIF Pipeline**:
   - Produces silky 60/30/15 FPS demo GIFs with tailored 256-color palettes, Lanczos downscaling, and Bayer dithering, shrinking file sizes by 30–50% while completely eliminating color banding.
3. **⚡ Cross-Platform Hardware Acceleration Matrix**:
   - Dynamic support for Apple Silicon VideoToolbox, NVIDIA NVENC, Intel/AMD VAAPI & QSV, alongside optimized CPU software encoding (`libx264`/`libx265`).
4. **📐 Target Size Bitrate Inversion Formula**:
   - Accurately fits videos into strict platform budget limits (Slack 50MB, WeChat 25MB, Discord 25MB/50MB, Feishu 100MB) via automated two-pass bitrate allocation.
5. **🔒 Privacy-First Batch Image Scrubbing**:
   - Batch converts modern formats (e.g. iPhone HEIC) to WebP while automatically stripping sensitive camera model, GPS coordinates, and EXIF metadata.

---

## 📦 Cross-Platform Installation

Ensure `ffmpeg`, `yt-dlp`, and `magick` (ImageMagick v7) are installed and accessible in your system `PATH`:

### macOS (Homebrew)
```bash
brew install ffmpeg yt-dlp imagemagick
```

### Linux (Ubuntu / Debian)
```bash
sudo apt update
sudo apt install -y ffmpeg imagemagick python3-pip
# yt-dlp is best installed via pip or official binary to stay current with site changes
pip install --upgrade yt-dlp
```

### Linux (Arch Linux)
```bash
sudo pacman -S ffmpeg yt-dlp imagemagick
```

### Linux (Fedora / RHEL)
```bash
sudo dnf install ffmpeg yt-dlp ImageMagick
```

### Windows (Winget / Scoop / Chocolatey)
```powershell
# Using Winget
winget install Gyan.FFmpeg
winget install yt-dlp.yt-dlp
winget install ImageMagick.ImageMagick

# Or using Scoop
scoop install ffmpeg yt-dlp imagemagick
```

---

## 🚀 8 Core Routing Branches

| Branch | Description | Typical Use Case |
| :--- | :--- | :--- |
| **Branch 0** | [Topic & Keyword Discovery](#branch-0-topic--keyword-discovery) | Search YouTube/Bilibili by keywords, list candidate links, or one-shot download |
| **Branch 1** | [Technical Talk Distillation](#branch-1-technical-talk-distillation) | Summarize keynote videos, extract dialogue, and produce Markdown study reports |
| **Branch 2** | [High-Aesthetic Demo GIF](#branch-2-high-aesthetic-demo-gif) | Convert terminal/UI screen recordings into crisp, lightweight GIFs (<5MB) |
| **Branch 3** | [Video Slimming & Compression](#branch-3-video-slimming--compression) | Compress meeting recordings or screen captures by 70–90% without visible loss |
| **Branch 4** | [Podcast & Audio Extraction](#branch-4-podcast--audio-extraction) | Extract high-fidelity audio (MP3/M4A) for on-the-go podcast listening |
| **Branch 5** | [High-Resolution Stream Download](#branch-5-stream-download) | Download 1080P/4K video streams with automated audio/video multiplexing |
| **Branch 6** | [Lossless Trimming & Diagnostics](#branch-6-lossless-trimming--diagnostics) | Trim media in 0.1 seconds without re-encoding; inspect codecs with `ffprobe` |
| **Branch 7** | [Batch Image Processing & Privacy Scrubbing](#branch-7-batch-image-processing--privacy-scrubbing) | Convert HEIC/PNG to WebP, resize geometries, and wipe GPS/EXIF tags |

---

### Branch 0: Topic & Keyword Discovery
Search and discover videos directly without pre-existing URLs:
```bash
# 1. Flat list top 5 candidates (<1s, zero-download metadata probe)
yt-dlp --flat-playlist --print "%(id)s | %(title)s | %(duration_string)s | %(uploader)s | https://www.youtube.com/watch?v=%(id)s" "ytsearch5:<KEYWORD>"

# 2. One-shot search and download best match into 1080P/4K MP4
yt-dlp -f "bestvideo+bestaudio/best" --merge-output-format mp4 "ytsearch1:<KEYWORD>"

# 3. Search and extract MP3 podcast audio from the top match
yt-dlp -x --audio-format mp3 --audio-quality 0 -o "%(title)s.%(ext)s" "ytsearch1:<KEYWORD>"
```
*Note: Seamlessly coordinates with search skills (e.g. `agent-reach` or Exa) for multi-platform web/social intelligence.*

### Branch 1: Technical Talk Distillation
Extract native subtitles without downloading heavy video streams:
```bash
yt-dlp --write-sub --write-auto-sub --sub-lang "zh-Hans,zh-CN,en,en-US" --skip-download "<URL>"
```
If subtitles are unavailable, anonymously extract audio and run local `faster-whisper` or an OpenAI-compatible audio API (see [`references/distill-workflow.md`](references/distill-workflow.md)).

### Branch 2: High-Aesthetic Demo GIF
Generate pixel-perfect GIFs for GitHub READMEs:
```bash
# Two-pass palette generation
ffmpeg -y -v warning -i input.mov -vf "fps=15,scale=1080:-1:flags=lanczos,palettegen=stats_mode=diff" palette.png
ffmpeg -y -v warning -i input.mov -i palette.png -filter_complex "fps=15,scale=1080:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" demo.gif
rm palette.png
```

### Branch 3: Video Slimming & Compression
- **Sharp Text / Code Screencast (Software CRF)**:
  ```bash
  ffmpeg -i input.mov -c:v libx264 -crf 23 -preset slow -pix_fmt yuv420p -c:a aac -b:a 128k compressed.mp4
  ```
- **Hardware Acceleration**:
  ```bash
  # macOS VideoToolbox
  ffmpeg -i input.mp4 -c:v h264_videotoolbox -b:v 2000k -pix_fmt yuv420p -c:a aac -b:a 128k output.mp4

  # NVIDIA NVENC
  ffmpeg -i input.mp4 -c:v h264_nvenc -preset p4 -cq 24 -pix_fmt yuv420p -c:a aac -b:a 128k output.mp4
  ```
- **Target Size Budget (e.g. Under 50MB)**:
  See automated two-pass script in [`references/ffmpeg-recipes.md`](references/ffmpeg-recipes.md).

### Branch 4: Podcast & Audio Extraction
```bash
# Extract audio track from URL
yt-dlp -x --audio-format mp3 --audio-quality 0 -o "%(title)s.%(ext)s" "<URL>"

# Lossless audio copy from local file
ffmpeg -i input.mp4 -vn -c:a copy audio.m4a
```

### Branch 5: Stream Download
```bash
# Best video + best audio muxed into MP4
yt-dlp -f "bestvideo+bestaudio/best" --merge-output-format mp4 "<URL>"
```

### Branch 6: Lossless Trimming & Diagnostics
```bash
# Instant trim without re-encoding (milliseconds duration, 0.1s execution)
ffmpeg -ss 00:01:15 -to 00:03:45 -i input.mp4 -c copy trimmed.mp4

# Inspect stream codec and metadata
ffprobe -v error -show_entries stream=codec_name,width,height,duration,bit_rate -of default=noprint_wrappers=1 input.mp4
```

### Branch 7: Batch Image Processing & Privacy Scrubbing
```bash
# Convert iPhone HEIC to WebP, restrict bounding box to 1920px, strip GPS/EXIF
magick mogrify -format webp -resize "1920x1920>" -strip -quality 82 *.heic

# Lossless PNG to WebP
magick input.png -strip -define webp:lossless=true output.webp
```

---

## 📁 Repository Layout

```text
media-toolkit/
├── README.md                   # Project overview & cross-platform guide
├── SKILL.md                    # Agent Skill specification & routing definitions
└── references/
    ├── distill-workflow.md     # Technical talk distillation pipeline & Whisper integration
    └── ffmpeg-recipes.md       # Deep production recipes & automated shell scripts
```

---

## ⚙️ Environment Variables

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `MEDIA_OUTPUT_DIR` | `./output` | Target folder for processed media, transcripts, and notes |
| `OPENAI_API_KEY` | *(None)* | Optional API key for OpenAI-compatible transcription |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Optional API base URL for Whisper endpoints |
| `COOKIE_FILE` | `~/.config/yt-dlp/cookies.txt` | Optional static cookies path for authenticated streams |

---

## 📄 License

Distributed under the [MIT License](LICENSE).
