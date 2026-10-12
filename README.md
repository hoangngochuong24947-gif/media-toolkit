# 🎬 Media Toolkit

<div align="center">

**面向 AI 智能体的全能音视频与图像自动化技能库**  
**The Universal Multimedia Automation Toolkit & Skill for AI Agents**

[中文文档](#-中文文档) • [English](#-english)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platforms: macOS | Linux | Windows](https://img.shields.io/badge/Platforms-macOS%20%7C%20Linux%20%7C%20Windows-green.svg)]()
[![Engines: ffmpeg | yt--dlp | ImageMagick](https://img.shields.io/badge/Engines-ffmpeg%20%7C%20yt--dlp%20%7C%20ImageMagick-orange.svg)]()

</div>

---

<a id="-中文文档"></a>
## 🇨🇳 中文文档

### 💡 什么是 Media Toolkit？
**Media Toolkit** 是一个让你的 AI Agent（Claude Code、Codex、Hermes、Cursor、Antigravity 等）拥有**本地音视频与图像深度自动化能力**的技能包（Skill）。它本身不调用外部闭源大模型，而是调度本地的 `ffmpeg`、`yt-dlp` 和 `ImageMagick`，为 Agent 提供精准、高速、零 API 成本的多媒体“手和脚”。

---

### 🚀 极简安装：复制提示词给你的 AI Agent
直接复制下面这段提示词，在聊天框发送给你的 Agent 即可自动安装与诊断：

```text
请帮我把 GitHub 仓库 https://github.com/hoangngochuong24947-gif/media-toolkit 完整克隆并安装为本地 Skill。
安装完成后，执行其内部的 bash scripts/doctor.sh 检查我电脑上的 ffmpeg、yt-dlp 和 ImageMagick 是否齐全；如果缺少依赖，请告诉我对应系统的安装命令。
```

#### 各平台技能目录速查
| 智能体平台 | 默认技能安装路径 |
| :--- | :--- |
| **Claude Code** | `~/.claude/skills/media-toolkit` |
| **Hermes Agent** | `~/.hermes/skills/media/media-toolkit` |
| **Codex / OpenCode / 通用** | `~/.agents/skills/media-toolkit` |
| **Antigravity** | `~/.gemini/config/skills/media-toolkit` |
| **Cursor / Windsurf** | 放在项目根目录下，提示 Agent：*“按照 SKILL.md 规范执行媒体操作”* |

---

### 🧭 能力边界全景解析（能做到什么程度？）

Media Toolkit 严格规范了 8 大核心能力分支的阈值、算法与临界条件：

#### 1. 关键词搜索与定向抓取 (Branch 0)
* **边界机制**：利用 `yt-dlp` 内置搜索引擎（`ytsearch[N]:`、`bilisearch[N]:`）直接搜 YouTube/B站，无需任何外部 API Key。
* **快速探测模式**：1 秒内返回视频标题、时长、UP 主与真实链接，不下载任何流媒体数据。
* **单步直达模式**：直接根据主题检索并下载最佳匹配的视频或音频。
* **提示词**：*“帮我在 YouTube 上搜一下 3Blue1Brown 讲傅里叶变换的视频，把前 3 个候选列出来，并把最高清的一条音频提取出来。”*

#### 2. 技术演讲与长视频“省流蒸馏” (Branch 1)
* **边界机制**：
  * **原生字幕优先（0 流量、秒级完成）**：优先提取平台自带中英软字幕（SRT/VTT），**绝不盲目下载几 GB 的庞大视频**。
  * **无字幕降级 ASR**：无字幕时仅拉取纯音频轨道，交由本地 `faster-whisper` 或音频接口进行转写。
  * **上下文防爆切片（12,000 字保护）**：字幕超过 12,000 字符自动分卷为 `part-001.txt`、`part-002.txt`，防止撑爆大模型上下文。
  * **零截图反废话准则**：默认严禁随意从视频抽帧插图，专注提炼架构演进、论点推导与带时间戳的里程碑记录。
* **提示词**：*“把这个视频链接（附 URL）的字幕提取出来，不用下载视频本身。读取字幕后，给我整理一份带时间戳核心论点、技术架构与金句的 Markdown 省流研报。”*

#### 3. 开源 Demo 高清动图 (Branch 2)
* **边界机制**：
  * **两阶段调色板算法（Two-Pass PaletteGen + Bayer 抖动）**：针对动态变化区域计算专属色阶，消除传统转码的色彩断层与噪点。
  * **GitHub 5MB 体积硬门禁**：若输出体积超标，自动触发降级门禁：15fps → 12fps、宽 1080px → 800px，并建议剪裁头尾无操作静止画面。
* **提示词**：*“把桌面的 `demo.mov` 录屏转成 1080p、15fps 的演示 GIF，用调色板消除噪点，体积帮我控制在 5MB 以内，方便我贴在 GitHub README 里。”*

#### 4. 视频脱脂与指定体积预算压缩 (Branch 3)
* **边界机制**：
  * **文字保真模式（CRF 22–24）**：专为代码、终端与会议录屏优化，文字边缘 100% 锐利不模糊，体积砍掉 70%~85%。
  * **硬件加速矩阵**：自动识别 macOS VideoToolbox、NVIDIA NVENC 或 Linux VAAPI 进行极速转码。
  * **体积预算反推**：按公式 `(目标MB * 8192 / 时长秒) - 音频码率` 跑两通精准压缩（如微信 25MB、邮件 50MB）。若算出的码率低于 64kbps 则主动拦截，防止严重马赛克。
* **提示词**：*“我这个会议录屏有 1.8GB，文字边缘一定要清晰，帮我用 CRF 23 压到 200MB 以内。”* 或 *“把 `demo.mp4` 严格压到 25MB 以内，我要微信发送。”*

#### 5. 视频随身“播客化”（抽音频） (Branch 4)
* **边界机制**：直接从 URL 剥离纯音频流，或将本地视频无损剥离转换为高品质 MP3。自动进行广播级 EBU R128（-16 LUFS）响度标准化，解决不同视频音量忽大忽小、爆音或听不清的痛点。
* **提示词**：*“把这个访谈视频里的音频抽出来转成 MP3，顺便跑一下人声响度均衡，我要放手机里通勤听。”*

#### 6. 全网音视频高清抓取与门禁 (Branch 5)
* **边界机制**：自动将最高画质视频轨与音频轨封装为 MP4。内置确认门禁：下载前先执行 `--simulate` 打印预估体积与分段数，避免盲目占满磁盘。
* **提示词**：*“帮我下载这个链接的视频，最高画质封装为 MP4，下载前先告诉我它有多大。”*

#### 7. 秒级无损剪切与媒体体检 (Branch 6)
* **边界机制**：
  * **极速模式（Fast Cut）**：基于关键帧流复制（`-c copy`），0.1 秒瞬时完成，零画质损失。
  * **精准模式（Accurate Cut）**：毫秒级帧对齐重编码切片。
  * **媒体体检**：利用 `ffprobe` 秒级透视编码器、分辨率、音频通道与坏帧损坏检测。
* **提示词**：*“帮我把视频从 01:15 到 03:45 剪切出来，用无损模式秒级完成；顺便用 ffprobe 告诉我它的真实码率和分辨率。”*

#### 8. 图片批处理与隐私脱敏 (Branch 7)
* **边界机制**：批量将苹果 `.heic` 照片转为 `.webp`，长边限制为 1920px（仅等比缩小，遇到小图绝不放大拉伸）。彻底抹除 GPS 经纬度定位、相机机型等 EXIF 隐私元数据。
* **提示词**：*“把当前目录下所有的 iPhone HEIC 照片批量转成 1920 宽度的 WebP，并彻底擦除里面包含的 GPS 和相机信息。”*

---

### ⚠️ 精简局限性（绝对做不到什么？）
1. **破不了 DRM 版权加密与未授权付费墙**：无法解密 Netflix/Spotify 的 Widevine DRM 加密流；未购买的 VIP 视频会被服务端直接返回 403。它不是黑客软件。
2. **变不出物理假细节（无法“去马赛克/老片超分”）**：`ffmpeg` 放大 360p 只能得到插值拉伸的模糊视频；麦克风严重炸麦削顶（Clipping）后，声波信息已物理损坏，无法逆向无损还原。
3. **机房 IP 无法单凭脚本绕过人机验证**：云端机房服务器（AWS、阿里云）直连易触发 YouTube Bot Check 或 B 站 HTTP 412。需在个人电脑宽带下运行，或手动挂载外部静态 `cookies.txt`。
4. **无法对无声、无字幕视频脑补画面剧情**：本工具的总结蒸馏依赖字幕文本与音频转写。完全无声、无字的纯画面视频需要视觉多模态大模型（VLM）逐帧推理，超出了编解码工具范畴。

---

<a id="-english"></a>
## 🌐 English

### 💡 What is Media Toolkit?
**Media Toolkit** gives your AI Agents (Claude Code, Codex, Hermes, Cursor, Antigravity, etc.) production-grade "hands and eyes" for local multimedia tasks. It is not an LLM itself—it operates locally using `ffmpeg`, `yt-dlp`, and `ImageMagick` so your agent can download videos, distill talks into timestamped notes, compress recordings, generate silk-smooth demo GIFs, and scrub image metadata without external API costs or bloat.

---

### 🚀 1-Click Installation via Agent Prompt
Simply copy and paste this prompt directly into your AI Agent:

```text
Please clone and install https://github.com/hoangngochuong24947-gif/media-toolkit into my local skills directory.
Once cloned, run `bash scripts/doctor.sh` (or check system PATH) to verify that ffmpeg, yt-dlp, and ImageMagick are available. If any dependencies are missing, output the exact install commands for my operating system.
```

#### Skill Directory Quick Reference
| Agent Platform | Default Skill Directory |
| :--- | :--- |
| **Claude Code** | `~/.claude/skills/media-toolkit` |
| **Hermes Agent** | `~/.hermes/skills/media/media-toolkit` |
| **Codex / OpenCode / General** | `~/.agents/skills/media-toolkit` |
| **Antigravity** | `~/.gemini/config/skills/media-toolkit` |
| **Cursor / Windsurf** | Put folder in repo root, prompt agent: *"Follow SKILL.md rules for media tasks"* |

---

### 🧭 Capability Boundaries (What Can It Do & Where Are the Limits?)

Media Toolkit defines clear thresholds and operational boundaries across 8 core branches:

#### 1. Query-Based Video Discovery & Download (Branch 0)
* **Boundaries & Mechanics**: Searches YouTube and Bilibili natively using `yt-dlp` (`ytsearch[N]:` / `bilisearch[N]:`) with zero API keys. 
* **Mode A (Flat Probe)**: Fetches title, duration, author, and URL in <1 second without downloading media bytes.
* **Mode B (Direct Pull)**: One-shot grabs the highest matching video or audio stream.
* **Prompt**: *"Search YouTube for recent talks on 'DeepSeek-V3 architecture', show the top 3 candidates, and download the audio for the best match."*

#### 2. Technical Talk Distillation (Branch 1)
* **Boundaries & Mechanics**: 
  * **Zero-Download Subtitle Priority**: Always extracts native SRT/VTT subtitles first. Never downloads gigabytes of video when captions exist.
  * **Fallback ASR**: If captions are absent, it downloads audio only and invokes local `faster-whisper` or Whisper API.
  * **Context-Safety Chunking**: Automatically splits transcripts over 12,000 characters into numbered chunks to prevent agent context overflow.
  * **Anti-Slop Invariant**: Strictly avoids unsolicited video screenshots; focuses entirely on architecture, arguments, formulas, and timestamped milestones.
* **Prompt**: *"Extract subtitles from this video URL (without downloading the video) and compile a high-density Markdown summary with timestamps and core arguments."*

#### 3. High-Aesthetic Demo GIFs (Branch 2)
* **Boundaries & Mechanics**: 
  * **Two-Pass PaletteGen**: Generates dynamic 256-color palettes with Lanczos downscaling and Bayer dithering (`stats_mode=diff`). Eliminates color banding completely.
  * **GitHub Size Guardrail (<5MB / 10MB)**: If output exceeds 5MB, it automatically steps down: 15fps → 12fps, 1080px → 800px width, and trims static lead-in/lead-out frames.
* **Prompt**: *"Convert `demo.mov` into a crisp 1080p GIF at 15fps, apply palette optimization, and ensure the size stays under 5MB for GitHub README."*

#### 4. Video Slimming & Target-Size Budget (Branch 3)
* **Boundaries & Mechanics**:
  * **Text/Code Screencast Mode (CRF 22–24)**: Drops 70–85% file size while preserving 100% sharp text edges for terminal/IDE recordings.
  * **Hardware Acceleration**: Automatically selects macOS VideoToolbox, NVIDIA NVENC, or Linux VAAPI when available.
  * **Target Size Inversion**: Calculates exact video bitrates via two-pass encoding for strict limits (e.g., Slack 50MB, WeChat 25MB). Refuses to encode if bitrate falls below 64kbps to avoid pixelation collapse.
* **Prompt**: *"Compress `meeting_recording.mov` (1.5GB) to under 100MB using CRF 23, keeping code and text sharp."*

#### 5. Podcast & Audio Extraction (Branch 4)
* **Boundaries & Mechanics**: Extracts high-bitrate MP3 or performs lossless stream copies (`.m4a`). Normalizes speech loudness to broadcast EBU R128 (-16 LUFS) so volume does not fluctuate during commute listening.
* **Prompt**: *"Extract the audio from this interview video into MP3 and normalize vocal loudness for podcast listening."*

#### 6. High-Resolution Stream Download (Branch 5)
* **Boundaries & Mechanics**: Automatically combines the highest available video track (4K/1080P) and highest audio track into MP4. Employs a confirmation gate (prints expected size and asks before downloading gigabytes).
* **Prompt**: *"Download this video in maximum quality MP4. Tell me the estimated file size before starting."*

#### 7. Instant Lossless Trimming & Diagnostics (Branch 6)
* **Boundaries & Mechanics**:
  * **Fast Cut (`-c copy`)**: Trims keyframes in 0.1s with zero re-encoding loss.
  * **Accurate Cut**: Re-encodes for millisecond-exact start/end boundaries.
  * **Diagnostics**: `ffprobe` surfaces real container codecs, bitrates, audio channels, and stream corruption.
* **Prompt**: *"Losslessly cut the clip from 01:15 to 03:45 from `input.mp4` without re-encoding, and print its codec info."*

#### 8. Batch Image Processing & Privacy Scrubbing (Branch 7)
* **Boundaries & Mechanics**: Batch-converts modern formats (iPhone HEIC/PNG) to WebP. Restricts bounding boxes to 1920px (downscales only; never upscales small images). Strips all GPS coordinates, camera model tags, and EXIF metadata.
* **Prompt**: *"Batch convert all `.heic` photos in this folder to WebP (max 1920px wide) and strip all camera and GPS metadata."*

---

### ⚠️ Hard Limitations (What Media Toolkit CANNOT Do)
1. **No DRM or Paid Paywall Decryption**: Cannot decrypt Widevine DRM streams (Netflix, Spotify, etc.) or access paid VIP videos without authorization.
2. **Cannot Synthesize Hallucinated Resolution**: `ffmpeg` cannot turn 360p into real 4K or remove blur/mosaics. Clipping distortion in audio cannot be magically restored.
3. **Datacenter IP Bot-Check Limitations**: Headless cloud VMs (AWS, Aliyun) may encounter YouTube/Bilibili bot checks (HTTP 412). Run locally or provide static `cookies.txt`.
4. **No Video Comprehension on Audio-less & Caption-less Videos**: Video distillation relies on transcripts and audio ASR. Completely silent, caption-less video comprehension requires multimodal vision models (VLM), which is outside the scope of codecs.

---

## 📁 目录结构 / Repository Layout

```text
media-toolkit/
├── SKILL.md                   # Agent 读取的技能规范主入口 / Skill spec & routing definition
├── README.md                  # 中英双语使用手册与能力边界 / Bilingual manual & boundaries guide
├── requirements-asr.txt       # 可选：本地 Whisper ASR 依赖 / Optional Whisper transcription deps
├── scripts/                   # 自动化运维与执行脚本 / Automation & operational scripts
│   ├── doctor.sh              # 环境依赖体检诊断 / Dependency healthcheck & diagnostic
│   ├── bootstrap.sh           # 自动化一键环境部署 / One-click setup & installer
│   ├── download.sh            # 安全下载门禁脚本 / Safe download gate
│   ├── transcribe.sh          # 本地轻量 ASR 转写 / Local Whisper ASR transcription
│   ├── subs_to_text.sh        # 字幕转时间戳纯文本 / Subtitle to clean timestamped text
│   ├── gif.sh                 # 两阶段高质量动图生成 / Two-pass palettegen GIF renderer
│   ├── compress-target-size.sh# 指定体积反推压缩计算器 / Two-pass target size compressor
│   ├── encode.sh              # 硬件加速重编码 / Hardware accelerated encoder
│   ├── trim.sh                # 快速/精准切片 / Lossless & accurate trimmer
│   ├── audio-extract.sh       # 音频剥离与响度均衡 / Audio extractor & loudness normalizer
│   ├── image-convert.sh       # 图片批处理与隐私抹除 / Batch image converter & EXIF scrubber
│   └── optional_tools.py      # 辅助分析与校验脚本 / Auxiliary validators & parsers
├── references/                # 详细工程参数与参考文档 / Detailed recipes & references
│   ├── yt-dlp.md              # 下载与风控处理指南 / Stream download & anti-bot reference
│   ├── ffmpeg.md              # 编解码硬件加速与两通算法 / Hardware acceleration & recipes
│   ├── distill-workflow.md    # 讲座省流提炼流水线 / Talk distillation & Whisper pipeline
│   ├── discovery.md           # 社交媒体发现协同规范 / Social & web discovery coordination
│   ├── report-template.md     # 结构化研报模板 / Structured study report template
│   └── troubleshooting.md     # 故障排除指南 / Troubleshooting & environment fixes
└── tests/                     # 自动化测试用例 / Automated test suites
    ├── test_gates.sh          # 门禁与确认测试 / Gate confirmation tests
    └── test_optional_tools.py # 脚本单元测试 / Unit tests
```

---

## ⚙️ 环境变量 / Environment Variables

| 变量名 (Variable) | 默认值 (Default) | 用途说明 (Description) |
| :--- | :--- | :--- |
| `MEDIA_OUTPUT_DIR` | `./output` | 媒体输出、字幕与转写文本目录 / Output directory for artifacts |
| `MEDIA_CONFIRM` | `0` | 设置为 1 时静默确认高成本门禁 / Set to 1 to bypass download confirmation |
| `OPENAI_API_KEY` | *(None)* | 可选：OpenAI 兼容 Whisper 接口密钥 / Optional API key for Whisper |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | 可选：Whisper 转写接口基础地址 / Optional API base URL |
| `COOKIE_FILE` | `~/.config/yt-dlp/cookies.txt` | 静态 Cookie 文件路径（避免弹窗） / Static cookies path |

---

## 📄 License

Distributed under the [MIT License](LICENSE).
