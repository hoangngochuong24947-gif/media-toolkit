# Media Toolkit

面向 AI 宿主的媒体处理 Skill，也提供可独立运行的 Python CLI。当前实现版本：**0.5.0-local**。

支持从关键词查找视频、获取字幕或本地转写、下载视频/音频、整理有时间锚点的报告，以及处理本地视频、音频和图像。安装到支持 Skill 的 AI 宿主后，可以直接用中文提出任务；CLI 负责执行和校验，宿主 AI 负责选取来源、阅读内容和撰写报告。

本仓库基于 [原 media-toolkit 项目](https://github.com/hoangngochuong24947-gif/media-toolkit) 修复和扩展，保留原始 Git 历史及 MIT 许可证，版本号不代表原作者的上游发布。

**下载入口：[v0.5.0-local Release](https://github.com/cowboy596/media-toolkit/releases/tag/v0.5.0-local)**。仓库为私有，需要有访问权限的 GitHub 账号。

## 能实现哪些功能

| 功能 | 当前能力 | 使用说明 |
|---|---|---|
| 视频搜索 | YouTube 关键词搜索；多关键词轮流分页、去重；按相关性或日期排序 | 输出候选清单、CSV、HTML 和搜索状态；日期排序不等于日期范围过滤 |
| B 站搜索 | 提供 Bilibili 关键词搜索接口 | 依赖本机网络和平台可用性，当前版本没有完成恢复网络后的成功验收 |
| 视频下载 | 通过 yt-dlp 选择最高可用视频/音频流并封装为 MP4 | 保留分片以便续传，记录实时进度；成功前检查音视频流并完整解码 |
| 音频下载 | 从在线视频获取音频并转换为 WAV | 可用于后续本地转写 |
| 字幕获取与整理 | 获取平台人工/自动字幕；解析本地 SRT/VTT | 保留原字幕、语言、时间、数字和来源信息，输出 JSON，保守清理滚动重复文本 |
| 本地语音转写 | faster-whisper 本地 ASR，支持语言、热词、时间片段和词级时间 | 模型缓存可复用；保留原始识别结果和运行来源，重要名字与数值需核对 |
| 视频研报 | 宿主 AI 阅读实际获得的字幕/转写，撰写论点；CLI 校验引文、时间和论点数字并生成 Markdown | 报告附来源链接和时间锚点；程序没有内置独立写作模型，也不自动读取视频画面 |
| 持久任务 | 保存原始需求、搜索范围、选取原因和字幕/下载/报告阶段 | 恢复前校验回执与哈希；所选交付项和所需报告全部通过后才算完成 |
| 视频压缩 | H.264/H.265；按质量参数或目标文件大小压缩 | 大小模式使用 CPU H.264；不可达到的目标会明确失败，不承诺固定缩小比例 |
| 硬件编码 | CPU、auto、NVENC、QSV、VideoToolbox、VAAPI 接口，失败时记录 CPU 回退 | Windows NVENC H.264/H.265、QSV H.264 已实测；macOS/Linux 硬件路径未实机验收 |
| 视频剪切 | 精确模式重编码；快速模式复制码流 | 快速剪切受关键帧限制，会记录实际时长差异 |
| GIF | 调色板生成、宽度/FPS 调整和目标体积检查 | 内容无法满足目标体积时返回失败 |
| 音频提取 | MP3、AAC M4A 编码；AAC/ALAC 直接复制到 M4A | 复制模式逐包比对哈希；不兼容编码会拒绝复制 |
| 图像处理 | 单张/批量转 WebP、自动方向、缩小尺寸、去除 EXIF/配置文件；符合条件的像素无损转换 | HEIC 需要解码器且仅处理主帧；批处理记录逐文件结果、支持校验后恢复 |
| 媒体检查 | ffprobe 容器、编码、尺寸、时长信息；工具和安装自检 | 返回 JSON 诊断，方便排错与复核 |
| 可选 API 转写 | 兼容 multipart 音频转写接口 | 必须显式开启网络调用；仅本地模拟服务验收通过，真实云服务需单独验证 |

## 快速开始：Windows 便携包

适合希望直接使用工具、无需自行配置 Python 和媒体依赖的用户。

1. 在 [Release](https://github.com/cowboy596/media-toolkit/releases/tag/v0.5.0-local) 下载 `media-toolkit-0.5.0-local-Windows.zip`。
2. **完整解压**到固定目录，例如 `D:\MediaToolkit`。进入其中包含 `media.cmd`、`check.cmd` 和 `runtime` 的 `media-toolkit` 文件夹。
3. 在该文件夹打开 PowerShell，执行：

```powershell
.\check.cmd
.\media.cmd --help
```

`check.cmd` 校验包内文件以及已配置的媒体/转写运行库，成功时输出 `"ok": true`。在终端执行可以保留诊断信息，避免双击后窗口关闭而看不到结果。

便携包包含 Python、FFmpeg/ffprobe、ImageMagick、yt-dlp、Node 和本地 ASR 依赖，不需要修改全局 PATH。**语音模型权重未包含**，首次转写需要指定已有缓存，或明确允许下载模型。

### 安装为 AI Skill

以 Codex 的用户技能目录为例，在便携包目录执行：

```powershell
.\install-skill.cmd "$env:USERPROFILE\.codex\skills\media-toolkit" "D:\MediaToolkitBackup"
```

已有 skill 会先备份，安装结果会给出备份路径。让宿主重新加载技能后，可以提出类似任务：

- “在 YouTube 查找最近 30 天的 AI 模型跑分对比，核对视频日期，阅读几条相关来源并整理比较报告。”
- “查找 DGX Spark 的官方视频和评测，整理技术研报，并下载选中的官方完整视频。”
- “把这段视频剪出指定时间段，转成不超过 5 MB 的 GIF。”
- “把这个文件夹的图片批量转为 WebP，去掉 EXIF，保留处理记录。”

宿主需要记录搜索范围、核对来源、选择视频、读取字幕/转写并撰写报告。**只搜索到候选不算报告或下载完成。** 安装后的轻量 skill 指向包内运行库，请保留完整便携目录；移动后重新安装可刷新路径。

## 常用命令

以下示例在 Windows 便携包目录执行。请替换输入路径和 `VIDEO_URL`，为输出选择未使用的文件名。

### 搜索、下载与字幕

```powershell
# 搜索五条 YouTube 候选，按日期排序
.\media.cmd search "AI model benchmark comparison" --count 5 --sort date

# B 站关键词搜索接口
.\media.cmd search "AI 模型跑分" --platform bilibili --count 5

# 多关键词收集：每页十条，本次最多四页、四十个唯一视频
.\media.cmd collect "NVIDIA DGX Spark" --query "DGX Spark benchmarks" -o "D:\MediaTasks\DGX-candidates" --page-size 10 --max-pages 4 --max-videos 40

# 从候选目录批量获取字幕；批量下载需要显式频道 ID 白名单
.\media.cmd batch "D:\MediaTasks\DGX-candidates" --stage subtitles --limit 5 --languages en
.\media.cmd batch "D:\MediaTasks\DGX-candidates" --stage download --channel-id "CHANNEL_ID" --limit 2

# 下载完整视频、音频，或仅获取英文字幕
.\media.cmd download "VIDEO_URL" -o "D:\MediaOutput\video.mp4"
.\media.cmd download-audio "VIDEO_URL" -o "D:\MediaOutput\speech.wav"
.\media.cmd fetch-subs "VIDEO_URL" -o "D:\MediaOutput\captions.json" --languages en

# 解析本地字幕，保留时间片段与数字
.\media.cmd subtitles "D:\MediaInput\captions.srt" -o "D:\MediaOutput\transcript.json"
```

`CHANNEL_ID` 必须替换为核对过归属的实际频道 ID；候选目录中其他频道的视频不会被该批量下载处理。

`collect` 只建立候选目录，不自动下载全部视频。范围由平台、关键词、排序和数量/页数预算共同决定；日期排序不是“最近 30 天”过滤，近期要求还需要核对候选发布日期。

### 视频、音频和图像处理

```powershell
.\media.cmd inspect "D:\MediaInput\video.mp4"

# 按质量压缩，或设置目标大小；MB 为 1,000,000 字节
.\media.cmd compress "D:\MediaInput\video.mp4" -o "D:\MediaOutput\quality.mp4" --crf 23
.\media.cmd compress "D:\MediaInput\video.mp4" -o "D:\MediaOutput\small.mp4" --target-mb 25

# 尝试硬件编码，记录实际使用的编码器和回退情况
.\media.cmd compress "D:\MediaInput\video.mp4" -o "D:\MediaOutput\h265.mp4" --codec h265 --encoder auto

# 剪切 1.3 至 3.1 秒；fast 模式可换取快速码流复制
.\media.cmd trim "D:\MediaInput\video.mp4" -o "D:\MediaOutput\clip.mp4" --start 1.3 --end 3.1 --mode accurate
.\media.cmd gif "D:\MediaOutput\clip.mp4" -o "D:\MediaOutput\clip.gif" --max-mb 5

# 音频编码与符合条件的码流复制
.\media.cmd audio "D:\MediaInput\video.mp4" -o "D:\MediaOutput\audio.mp3"
.\media.cmd audio "D:\MediaInput\video.mp4" -o "D:\MediaOutput\audio.m4a" --format m4a
.\media.cmd audio "D:\MediaInput\video.mp4" -o "D:\MediaOutput\copied.m4a" --format m4a --copy

# 转 WebP；批处理输出目录须为空，并位于输入目录树之外
.\media.cmd image "D:\MediaInput\photo.heic" -o "D:\MediaOutput\photo.webp" --max-side 1920
.\media.cmd image "D:\MediaInput\image.png" -o "D:\MediaOutput\lossless.webp" --lossless
.\media.cmd images "D:\MediaInput\photos" -o "D:\MediaOutput\webp-batch" --recursive
```

去除 EXIF 不会隐藏图片中的人脸、文字或场景。无损 WebP 模式要求兼容的位深且不缩放；音频直接复制要求 AAC/ALAC 输入，已有有损音频不会因此恢复原始质量。

### 本地语音转写

```powershell
# 首次允许下载 small 模型，转写中文音频
.\media.cmd transcribe "D:\MediaOutput\speech.wav" -o "D:\MediaOutput\asr-first.json" --model small --language zh --cache-dir "D:\MediaModels" --allow-model-download

# 后续复用同一缓存，不允许再下载模型；使用新的输出文件名
.\media.cmd transcribe "D:\MediaInput\another.wav" -o "D:\MediaOutput\asr-next.json" --model small --language zh --cache-dir "D:\MediaModels" --hotwords "DGX Spark GB10"
```

联网获取视频与本地识别是不同阶段。模型就绪后可以本地转写已有音频；识别结果可能误写名字和数字，报告应保留原文不确定性。API 转写不会被本地流程隐式启用，参数和授权要求见 [能力扩展说明](references/capability-parity.md#compatible-api-asr)。

## 关键词 → 视频 → 技术报告：持久任务流程

安装 skill 后，这些步骤通常由宿主 AI 执行。需要手动控制任务时，可使用下面的 CLI 流程；当前 `project` 的发现流程面向 YouTube。

### 1. 保存需求并检索

在包目录之外保存 `D:\MediaTasks\request.json`，内容例如：

```json
{
  "request": "查找 DGX Spark 视频，整理技术研报并下载选中的官方视频",
  "queries": ["NVIDIA DGX Spark official", "DGX Spark benchmarks"],
  "search": {"page_size": 10, "max_videos": 50, "max_pages": 10, "sort": "relevance"},
  "report_required": true,
  "subtitles_languages": "en",
  "asr": {"enabled": true, "model": "small", "cache_dir": "D:/MediaModels", "allow_model_download": false}
}
```

此示例只允许使用已有模型缓存。若第一次需要下载模型，可在明确允许下载后将 `allow_model_download` 改为 `true`。

```powershell
.\media.cmd project init "D:\MediaTasks\request.json" -o "D:\MediaTasks\DGX-job"
.\media.cmd project run "D:\MediaTasks\DGX-job"
```

第一次 `run` 会生成 `discovery/index.html` 候选目录，然后返回 `awaiting_selection`。这是等待选取，不是成功完成；非零退出码表示任务仍未完成。

### 2. 选取来源并获取内容

阅读候选清单、核对官方来源后，将下面的 `VIDEO_ID` 替换为清单中实际存在的视频 ID：

```powershell
.\media.cmd project select "D:\MediaTasks\DGX-job" --video-id "VIDEO_ID" --download-id "VIDEO_ID" --reason "已核对来源，选取该视频用于报告与完整下载"
.\media.cmd project run "D:\MediaTasks\DGX-job"
```

`--video-id` 指定要获取文字内容的视频，`--download-id` 指定要下载完整视频的条目，两者可分别重复。请求需要报告时，下载选中的视频也会纳入文字证据处理；选取操作是追加，不会静默取消先前选取。

字幕获取失败且 ASR 启用时，流程尝试获取音频并做本地转写。失败会记录原因，所选视频下载仍会被尝试。成功恢复阶段只在哈希与回执匹配后跳过。

### 3. 读取证据并发布报告

文字内容在 `transcripts/`，本地识别原文在 `raw-asr/`，视频在 `videos/`。宿主 AI 阅读实际文件后，编写 `D:/MediaTasks/claims.json`。字段示意如下，**不能直接使用示意引文**；请填写实际视频 ID、片段索引和逐字匹配的引文，多来源报告应包含每个选中来源的论点。

```json
{
  "title": "DGX Spark 视频研报",
  "coverage": "实际阅读的来源、搜索范围与未处理项",
  "claims": [{
    "transcript": "DGX-job/transcripts/VIDEO_ID.json",
    "subtitle": 0,
    "cue": 0,
    "quote": "实际字幕中的逐字引文",
    "statement": "这条引文支持的陈述",
    "kind": "speaker"
  }],
  "limitations": "字幕识别不确定性和未独立验证的结论"
}
```

`subtitle` 选择平台字幕语言文档，`cue` 选择其中的片段；本地 ASR 直接使用顶层 `cues`。引文必须出现在对应片段，陈述中的数字也必须得到引文支持。详细规则见 [论点与引文格式](references/capability-parity.md#evidence-report)。完成后运行：

```powershell
.\media.cmd project report "D:\MediaTasks\DGX-job" --claims "D:\MediaTasks\claims.json"
.\media.cmd project status "D:\MediaTasks\DGX-job"
```

每条论点包含字幕文件、片段索引、原文引文、陈述和类型；每个选中的文字来源都要有引用。校验通过后生成 `report.md`。引文、时间及论点数字匹配不等于语义、科学结论或语音识别准确性得到认证。

任务入口是 `index.html`，状态是 `project.json`。**只有 `status: "success"` 且 `complete: true`，才表示所选交付项及所需报告全部校验通过。** `init/select` 的 `ok: true` 只表示操作已接受。

## 进度、恢复和常见问题

| 情况 | 如何处理 |
|---|---|
| 下载暂时没有可见增长 | 查看 `<输出文件>.progress/current.json`，项目任务查看 `progress/current.json`；工具可能仍在获取格式、传输或完整解码 |
| 网络失败、字幕缺失或模型未缓存 | 阅读 JSON 的错误码或 `project.json` 阶段记录；需要时允许本地模型下载，或解决网络问题后明确重试 |
| 继续失败/取消的项目 | 运行 `project run JOB_DIR --retry-failed`；保留原任务目录与 `.download` 分片 |
| 继续 `collect` | 使用相同目录、关键词和排序，可增大数量/页数预算；不得在原目录更换关键词或排序 |
| 同名输出或回执已存在 | 使用新的文件名；直接命令不会覆盖已有输出，项目恢复会先校验已有成果 |
| 已完成文件损坏或被修改 | 保留现场，使用新输出或新任务重新生成；不会覆盖损坏证据并悄悄报成功 |
| 提示任务被锁定 | 确认是否仍有进程运行；只有核实原进程已退出后，才移除对应目录的失效 `.job.lock` |
| 找不到工具 | 便携包先运行 `check.cmd`；源码方式配置依赖和本机工具路径，使用 `doctor` 检查 |

直接下载失败后，可对同一 URL 和未发布的同一输出重新运行 `download`；平台支持时会复用保留的分片。每个已发布文件旁有 `<输出>.result.json`，记录 SHA256、实际参数和校验结果。

默认单个子进程预算：下载/项目/批处理 1800 秒，本地转写命令 900 秒，其他命令 300 秒。完整任务可能包含多个子进程。全局参数必须放在子命令之前，例如：

```powershell
.\media.cmd --timeout 3600 download "VIDEO_URL" -o "D:\MediaOutput\large-video.mp4"
.\media.cmd --progress-dir "D:\MediaOutput\progress" compress "D:\MediaInput\video.mp4" -o "D:\MediaOutput\tracked.mp4"
```

## 从源码使用

Git 克隆或源码 ZIP **不包含便携运行库**。核心 CLI 使用 Python 3.10+ 标准库；媒体处理需要 FFmpeg/ffprobe、ImageMagick 7，网络获取需要 yt-dlp。YouTube 还可能需要兼容的 JavaScript 运行库与提取器依赖。

配置这些依赖后，在仓库根目录运行：

```powershell
python .\scripts\media.py doctor
python .\scripts\media.py --help
python .\scripts\media.py inspect "D:\MediaInput\video.mp4"
```

前面的 `.\media.cmd` 示例在源码方式下应换成 `python .\scripts\media.py`。

若工具不在 PATH，可在根目录创建不提交的 `tool-paths.local.json`，例如：

```json
{
  "ffmpeg": "D:/Tools/ffmpeg.exe",
  "ffprobe": "D:/Tools/ffprobe.exe",
  "magick": "D:/Tools/ImageMagick/magick.exe",
  "yt-dlp": "D:/Tools/yt-dlp.exe",
  "node": "D:/Tools/node.exe",
  "asr-python": "D:/MediaASR/Scripts/python.exe"
}
```

填写本机真实存在的路径；未配置的工具从 PATH 查找。环境变量 `MEDIA_FFMPEG`、`MEDIA_FFPROBE`、`MEDIA_MAGICK`、`MEDIA_YT_DLP`、`MEDIA_ASR_PYTHON` 等优先于配置文件。配置好的 `node` 会用于在线提取；自行依赖 PATH 时可显式加 `--js-runtime node`。

源码方式需要本地 ASR 时，自行安装 Python 3.13 后可创建独立环境：

```powershell
py -3.13 -m venv "D:\MediaASR"
& "D:\MediaASR\Scripts\python.exe" -m pip install -r .\requirements-asr-lock.txt
```

将配置里的 `asr-python` 指向该环境的 `Scripts/python.exe`。测试所需的额外依赖在 `tests/requirements.txt`。完整验收记录和日志见 [validation](validation/summary.json)。

## 当前验收范围

- 源码与含中文/空格路径的迁移 Windows 包各 **94 项测试通过，零跳过**；受限 PATH、自检、依赖一致性、真实 HTTP 续传和本地中文转写验证通过。
- 真实 YouTube 任务完成两条新字幕、一个完整解码的视频及十条引文报告；安装版恢复与任务目录迁移校验通过。
- **另一台物理干净客户机**的安装验收尚未执行；语音模型、实际云端转写服务和 macOS/Linux 硬件加速不是本次已验证范围。
- 画质取决于源视频和编码设置，下载选择最高可用流不代表任意视频都有 4K。不承诺固定压缩比例、速度、全平台穷尽搜索或识别准确率。
- 只使用显式提供并授权的静态 cookies 文件，不自动读取浏览器凭据；云端音频上传和可能的费用必须显式授权。

更多资料：[Skill 路由](SKILL.md) · [客户工作流](references/customer-workflow.md) · [媒体处理配方](references/ffmpeg-recipes.md) · [变更记录](CHANGELOG.md)。

## 许可证

核心项目使用 [MIT License](LICENSE)。Windows 包内的 Python、FFmpeg、ImageMagick、yt-dlp、Node 和转写依赖适用各自许可证，通知位于包内 `RUNTIME-NOTICES.md`、`runtime/licenses` 及各发行包元数据。核心 MIT 许可证不替代这些组件的许可证。
