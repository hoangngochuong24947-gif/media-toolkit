# Media Toolkit

**Executable media workflows with verified outputs.** Version: `0.5.0-local`.
This is a maintained local revision of [the original media-toolkit](https://github.com/hoangngochuong24947-gif/media-toolkit), not an upstream release. Original Git history and MIT license are retained.

下载：[v0.5.0-local 发布页](https://github.com/cowboy596/media-toolkit/releases/tag/v0.5.0-local)。Windows 用户下载便携 ZIP；源码 ZIP 为已验收版本快照。测试结果与边界见 [验收摘要](validation/summary.json)。

Version 0.4 adds M4A stream copy, resumable image batches, runtime hardware
selection/H265, evidence-checked reports and opt-in compatible API transcription.
Commands, claim schema and validation boundaries are in
[capability additions](references/capability-parity.md).

本版本修复字幕正文丢失、体积超限仍报成功、剪切精度表述不清和缺少输出验收。
0.5 新增客户任务入口：保存原始需求与搜索范围，明确选择视频，自动获取字幕或回退本地转写，下载视频，并由宿主 AI 阅读证据、撰写研报。任务只有在所选交付物与报告通过校验后才标记完成。

Windows 便携包解压后先运行 `check.cmd`，通过 `media.cmd` 执行命令；安装 skill 时使用 `install-skill.cmd 安装目录 备份目录`。运行库保留在包内，无需修改全局 PATH。详细步骤见 [客户工作流](references/customer-workflow.md)。下载支持保留分片、断点续传与进度记录；网络或平台限制会明确记录。

## Install and dependencies

Copy the entire directory, including scripts/ and references/, into the host's
skill directory, e.g. ~/.codex/skills/media-toolkit/. Back up existing installations
before replacement. The CLI can run without an agent.

- Python 3.10+; CLI runtime uses only the standard library.
- FFmpeg and ffprobe for audio/video.
- ImageMagick v7 `magick` with WebP support; HEIC needs a working decoder.
- yt-dlp for optional online commands. Site changes may require updates.
- YouTube may need compatible JavaScript runtime/extractor dependencies. Merely
  installing Node does not automatically enable it in yt-dlp.

No dependency installation, global PATH changes, browser credential access or
paid transcription calls are performed by the CLI.

```powershell
winget install --id Gyan.FFmpeg --exact
winget install --id ImageMagick.ImageMagick --exact
winget install --id yt-dlp.yt-dlp --exact
python scripts/media.py doctor
```

macOS with Homebrew: `brew install ffmpeg imagemagick yt-dlp`.
On Linux install supported packages, checking that ImageMagick is v7:
distributions with v6 `convert` do not satisfy the `magick` dependency.
Only dependencies needed by the selected command are required.

Tools outside PATH can be configured without changing global settings:

```powershell
$env:MEDIA_FFMPEG = 'C:\tools\ffmpeg.exe'
$env:MEDIA_FFPROBE = 'C:\tools\ffprobe.exe'
$env:MEDIA_MAGICK = 'C:\tools\magick.exe'
$env:MEDIA_YT_DLP = 'C:\tools\yt-dlp.exe'
python scripts/media.py doctor
```

The same variable names work in Unix shells. No machine-specific paths are
embedded in the implementation.

## Commands

The Python CLI works with PowerShell or Unix shells without Bash translation.
Use an absolute path to scripts/media.py when running from another directory.
`--timeout SECONDS` precedes the command and bounds each subprocess, not the
whole command. Defaults: 1800 seconds for download/project/batch, 900 for local
transcription, 300 for other commands. Progress snapshots are opt-in globally
and enabled automatically for downloads and project runs.

```powershell
python scripts/media.py inspect input.mp4
python scripts/media.py subtitles captions.vtt -o output/transcript.json
python scripts/media.py gif input.mp4 -o output/demo.gif --max-mb 5
python scripts/media.py compress input.mp4 -o output/small.mp4 --target-mb 25
python scripts/media.py compress input.mp4 -o output/quality.mp4 --crf 23
python scripts/media.py compress input.mp4 -o output/fast.mp4 --encoder nvenc
python scripts/media.py audio input.mp4 -o output/audio.mp3
python scripts/media.py trim input.mp4 -o output/cut.mp4 --start 1.3 --end 3.1 --mode accurate
python scripts/media.py trim input.mp4 -o output/fast-cut.mp4 --start 1.3 --end 3.1 --mode fast
python scripts/media.py image input.heic -o output/image.webp --max-side 1920
python scripts/media.py image input.png -o output/lossless.webp --lossless
```

| Command | Implemented behavior | Boundary |
|---|---|---|
| subtitles | SRT/VTT cue parsing, numbers/timestamps preserved, tag cleanup, overlapping repeated-line removal | Conservative line deduplication; caption errors need review |
| gif | Two-pass palette, up to 5 width/FPS attempts, byte/decode checks | May fail if content cannot fit; no promised reduction or banding elimination |
| compress --target-mb | Decimal budget, CPU two-pass, up to 3 attempts, size/stream/decode checks | Infeasible budgets fail; no automatic duration/audio/geometry sacrifice |
| compress --crf | H.264/AAC quality-oriented compression | No fixed ratio, perceptual quality or text-readability guarantee |
| compress --encoder auto | Try platform-specific hardware candidates, then CPU; record actual encoder | Successful encode/decode establishes this input only; other machines need acceptance |
| trim --mode accurate | Re-encode with accurate seeking; duration tolerance 0.15 s | Frame/audio quantization; no millisecond guarantee |
| trim --mode fast | Stream copy; report actual duration/error | Keyframe/preroll limits; no precise boundary guarantee |
| audio | MP3 or AAC M4A encoding; --format m4a --copy verifies AAC/ALAC packet hashes | Copy rejects incompatible codecs; encoding is lossy |
| image | Primary frame, auto-orient, shrink-only, EXIF/profile strip/check | Visible faces/text/context are not anonymized; extra HEIC frames not preserved |
| image --lossless | Require <=8-bit and no resize; verify pixel identity | Reject incompatible/pixel-changing conversions |
| inspect | ffprobe container/stream JSON | Diagnostics, not perceptual assessment |

**MB = 1,000,000 bytes.** Compression and resizing can visibly change media.
Receipts record settings actually used.

## Output contract

Successful operations return JSON with `ok: true`, requested constraints, actual
settings, validation and subprocess timing. Each published output has
`<output>.result.json` containing its SHA-256. Errors return JSON with
`ok: false`, an error code and nonzero exit status.

Intermediates/pass logs are isolated under the output parent and cleaned up.
Existing outputs/receipts are refused: choose a fresh name. Source media is never
overwritten. Publication requires filesystem hard-link support (NTFS/APFS and
typical Linux filesystems); unsupported destinations fail explicitly.

Full decode checks add runtime and verify integrity, not perceptual quality.
Subtitle JSON stores timestamped cues and cleaned text. No transcript means no
video-derived report.

## Online preview

```powershell
python scripts/media.py search 'NVIDIA DGX Spark' --count 5 --js-runtime node
python scripts/media.py search 'ffmpeg' --platform bilibili --count 5
python scripts/media.py download 'https://example.org/video.mp4' -o output/video.mp4
python scripts/media.py fetch-subs 'https://example.org/watch' -o output/subtitles.json --languages en
```

Search ranking is not proof of official status or authority. Downloads select
best available streams and remux to MP4; source resolution cannot be upgraded.
Site changes, format compatibility, login, geography, TLS and rate limits may
block completion. Retries are bounded; errors distinguish rate limits, access,
network and formats on a best-effort basis.

Static cookies only when explicitly supplied/authorized: `--cookies FILE`.
No command uses `--cookies-from-browser`. Local ASR/model downloads are optional
and explicit. API ASR requires an explicit endpoint and --allow-network; remote
endpoints also require MEDIA_ASR_API_KEY. No credentials enter receipts.
See [transcript workflow](references/distill-workflow.md).

## Keyword collection and batch processing

Customers can ask their installed host agent: “汇总 YouTube 上 NVIDIA DGX Spark
相关视频，批量提取字幕，按来源整理报告，只下载 NVIDIA 官方视频”。
The host runs commands; customers do not need PowerShell.

```text
python scripts/media.py collect "NVIDIA DGX Spark" -o "D:/Media/DGX Spark" --js-runtime node
python scripts/media.py batch "D:/Media/DGX Spark" --stage subtitles --limit 10 --languages en --js-runtime node
python scripts/media.py batch "D:/Media/DGX Spark" --stage download --channel-id UCHuiy8bXnmK5nisYHUd1J5g --limit 5 --js-runtime node
```

Discovery writes an offline Chinese searchable HTML catalog, CSV and atomic JSON
checkpoint. Defaults: 500 unique IDs, 50 per slice, 20 slices per invocation.
Repeat with larger budgets to resume, or repeated `--query` to set aliases at
creation. Queries cannot be changed in-place. `source_exhausted` means this search
returned no more entries; it NEVER certifies every matching video on YouTube.
Rankings may change during pagination. Limit/failure states remain partial.
No full videos are downloaded just by discovery. Candidates may be unrelated.

Batch acquisition has independent per-item success/failure states. Repeated
`--video-id` selects entries. Receipts and content hashes are checked before
skipping. `--retry-failed` explicitly retries. Authentication/rate/network errors
stop the batch. A lock prevents concurrent writers; after an externally killed
process, inspect the lock PID and remove only a stale lock. Damaged artifacts
are preserved, not overwritten. Channel-ID allowlists constrain bulk downloads;
the host verifies who owns the channel before labeling it official.

### Optional local ASR

An installer/host can create tool-paths.local.json in the skill root mapping
ffmpeg, ffprobe, magick, yt-dlp and asr-python to validated executable paths.
Environment overrides take priority. This local machine profile is excluded
from the source package, so relocated customers must provision their own paths.

Use a separate Python 3.13 environment and requirements-asr-lock.txt. Set
MEDIA_ASR_PYTHON to its interpreter. Model cache location is explicit, and
downloads require `--allow-model-download`; later runs use cached files only.

```text
python scripts/media.py download-audio "VIDEO_URL" -o "D:/Media/audio.wav" --js-runtime node
python scripts/media.py transcribe "D:/Media/audio.wav" -o "D:/Media/asr.json" --model small --language en --cache-dir "D:/Media/models" --hotwords "DGX Spark NVLink" --allow-model-download
```

Raw platform captions, manual/automatic provenance, language and conservative
rolling deduplication are retained. Speech timeline coverage is not accuracy.
Local ASR includes word timestamps, model/runtime/source provenance and warnings.
It may still misrecognize names, quantities or jargon. Reports are written by
the host agent from actual obtained transcripts, not generated by this CLI.
This is an agent skill package, not a standalone desktop application or a
guarantee that anonymous platform acquisition always works.

## Tests

```powershell
python -m unittest discover -s tests -v
# Configure executable paths, then enable real-tool tests:
$env:MEDIA_INTEGRATION = '1'
python -m unittest discover -s tests -v
```

Unit tests have no third-party Python dependencies. Image fixture integration
tests need Pillow, a test-only dependency: install tests/requirements.txt into an
isolated venv. Integration tests use generated local media and localhost HTTP,
with no external platform access required.

Release gate: integration tests with no skips, plus syntax checks. This local
release is tested on Windows; macOS/Linux execution is not yet certified.
