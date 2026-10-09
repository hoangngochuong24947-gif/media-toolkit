# Technical Talk Distillation Pipeline

A systematic workflow to extract, transcribe, synthesize, and compile long technical video/audio talks into high-density structured knowledge artifacts.

---

## 1. Zero-Download Subtitle Acquisition (Fast Path)

Always inspect whether the hosting platform already provides native or auto-generated subtitles before pulling heavy video/audio streams:

```bash
# 1. List available subtitle languages
yt-dlp --list-subs "<URL>"

# 2. Download subtitles without downloading video media
yt-dlp --write-sub --write-auto-sub \
  --sub-lang "zh-Hans,zh-CN,en,en-US" \
  --skip-download \
  -P "${MEDIA_OUTPUT_DIR:-./downloads}" \
  -o "talk_sub.%(ext)s" "<URL>"
```

### Cleaning Subtitles (VTT/SRT to Clean Text)
VTT and SRT subtitle files contain timestamps, line numbers, and repeated rolling caption blocks. Use this quick one-liner to strip cue artifacts into continuous dialogue:

```bash
sed '/^[0-9]/d; /^$/d; /-->/d; /^WEBVTT/d; /^Kind:/d; /^Language:/d' "${MEDIA_OUTPUT_DIR:-./downloads}/talk_sub.zh-Hans.vtt" | uniq > "${MEDIA_OUTPUT_DIR:-./downloads}/clean_transcript.txt"
```

---

## 2. Decoupled Audio Transcription (When No Subtitles Exist)

When no soft subtitles are available, fetch the lightweight audio stream anonymously:

```bash
# Download pure audio stream (no cookies required, zero keychain popup risk)
yt-dlp -x --audio-format m4a -P "${MEDIA_OUTPUT_DIR:-./downloads}" -o "talk_audio.%(ext)s" "<URL>"
```

### Option A: Local `faster-whisper` (Recommended for Local GPU/MPS/CPU)

Run transcription locally using the high-performance CTranslate2 engine:

```bash
# Install dependency
pip install faster-whisper

# Run standalone Python transcription CLI
python -c '
import sys
from faster_whisper import WhisperModel

audio_path = sys.argv[1] if len(sys.argv) > 1 else "talk_audio.m4a"
# device can be "cuda", "mps", or "cpu"; compute_type can be "float16", "int8", or "default"
model = WhisperModel("large-v3", device="auto", compute_type="default")

segments, info = model.transcribe(audio_path, beam_size=5, vad_filter=True)
print(f"Detected language: {info.language} with probability {info.language_probability:.2f}")

with open("talk_transcript.srt", "w", encoding="utf-8") as srt_file, \
     open("talk_transcript.txt", "w", encoding="utf-8") as txt_file:
    for i, segment in enumerate(segments, start=1):
        # Format SRT timestamp
        def fmt(ts):
            h = int(ts // 3600); m = int((ts % 3600) // 60); s = int(ts % 60); ms = int((ts % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        srt_file.write(f"{i}\n{fmt(segment.start)} --> {fmt(segment.end)}\n{segment.text.strip()}\n\n")
        txt_file.write(f"[{fmt(segment.start)}] {segment.text.strip()}\n")

print("Transcription saved to talk_transcript.srt and talk_transcript.txt")
' "${MEDIA_OUTPUT_DIR:-./downloads}/talk_audio.m4a"
```

### Option B: Standard OpenAI-Compatible Audio API

Use standard cloud or self-hosted OpenAI-compatible transcription endpoints (OpenAI Whisper, Groq, local vLLM, or whisper.cpp server):

```bash
# Ensure OPENAI_API_KEY and OPENAI_BASE_URL are configured
# Example: https://api.openai.com/v1 or https://api.groq.com/openai/v1 or http://localhost:8080/v1
curl -s "${OPENAI_BASE_URL:-https://api.openai.com/v1}/audio/transcriptions" \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  -H "Content-Type: multipart/form-data" \
  -F file="@${MEDIA_OUTPUT_DIR:-./downloads}/talk_audio.m4a" \
  -F model="whisper-1" \
  -F response_format="verbose_json" \
  > "${MEDIA_OUTPUT_DIR:-./downloads}/talk_transcript.json"
```

### Option C: Lightweight Standalone CLI (`whisper.cpp`)

For completely self-contained C/C++ execution without Python dependencies:

```bash
# Convert audio to 16kHz WAV required by whisper.cpp
ffmpeg -i "${MEDIA_OUTPUT_DIR:-./downloads}/talk_audio.m4a" -ar 16000 -ac 1 -c:a pcm_s16le /tmp/talk_16k.wav

# Run whisper.cpp binary
whisper-cli -m models/ggml-large-v3.bin -f /tmp/talk_16k.wav -osrt -otxt -of "${MEDIA_OUTPUT_DIR:-./downloads}/talk_transcript"
rm /tmp/talk_16k.wav
```

---

## 3. Knowledge Synthesis & Distillation Standards

### 🌟 Core Quality Invariants
1. **Zero Screenshots by Default**: Do not extract video frames or insert image placeholders into the report unless explicitly requested by the user. Keep artifacts lightweight, pure text, and focused on core reasoning.
2. **Deep Anchor on Dialogue & Reasoning**:
   - Synthesize chronologically with precise timestamp anchors (`[mm:ss]`).
   - Extract underlying system design trade-offs, empirical benchmarks, and counter-intuitive insights.
   - Preserve direct quotes for punchy or controversial claims.

### Structured Synthesis Template

```markdown
# [Talk Title]: Technical Distillation & Key Takeaways

- **Speaker / Organization**: [Name / Lab / Organization]
- **Original Link**: [URL]
- **Distilled At**: [YYYY-MM-DD]
- **Tags**: #ai #systems #architecture

---

## 1. Executive Summary (一分钟核心速览)
- **Problem Statement**: What core technical bottleneck or industry pain point does this talk address?
- **Core Proposal**: What novel paradigm, architecture, algorithm, or methodology was introduced?
- **Key Outcomes**: What concrete metrics, speedups, or benchmark gains were validated?

---

## 2. Technical Architecture & Core Primitives (核心系统原理与机制)
- **Mechanics & Workflow**: Step-by-step breakdown of the technical components (include Mermaid diagrams where applicable).
- **Architectural Trade-offs**: What compromises were made (e.g. latency vs. throughput, consistency vs. availability)?
- **Key Equations / Algorithms**: Mathematical foundations or core pseudocode logic.

---

## 3. Timestamped Milestones & Deep Insights (带时间戳的推演脉络)
- `[04:20]` **Problem Discovery & Historical Context**: ...
- `[12:45]` **Core Mechanism Walkthrough**: ...
- `[23:10]` **Benchmarking & Empirical Validation**: ...
- `[35:00]` **Limitations, Caveats & Future Outlook**: ...

---

## 4. Entity & Concept Extraction (概念实体萃取)
- [[Core Concept A]]: Definition, role, and practical application in this architecture.
- [[Core Concept B]]: Comparison against traditional paradigms.
```

---

## 4. Output Storage & Organization

Save generated artifacts to the designated output folder:

```bash
# Output directory can be customized via $MEDIA_OUTPUT_DIR (defaults to ./output)
DEST_DIR="${MEDIA_OUTPUT_DIR:-./output}/distill"
mkdir -p "$DEST_DIR"

# Save distillation report
# e.g., ${DEST_DIR}/YYYYMMDD_<Topic_Slug>.md
```
