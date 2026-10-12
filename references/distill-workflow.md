# Distill a talk

The host agent does the reading and the writing. This skill only fetches evidence and turns it into timestamped plain text. It does not call an LLM and it does not summarize.

Output root: `${MEDIA_OUTPUT_DIR:-./output}/<task>/`.

## Confirmation gates

Cheap reads go ahead. Costly steps stop until the user agrees.

| Step | Ask first? | What the agent does |
| :--- | :--- | :--- |
| Search, list formats, list subs, `doctor.sh` | No | Run it |
| Fetch platform subtitles (`--skip-download`) | No | Run it |
| `subs_to_text.sh` on files already downloaded | No | Run it |
| Full video or audio download | Yes | `download.sh` prints count and size and exits 0. Show that. After a yes, re-run with `--yes` |
| Local ASR | Yes | `transcribe.sh` prints videos, duration, model, download size, and a rough time estimate, then exits 0. After a yes, re-run with `--yes` |
| System packages / sudo | Yes | `bootstrap.sh` is a dry-run. After a yes, `--yes` |
| Browser cookies | Yes, once | Ask which browser and profile. Pass them only with `--yes` |
| A loop over many files | Yes | Show the count, then wait |

`--yes` and `MEDIA_CONFIRM=1` mean the user already agreed. Do not pass them first.

## Data handed between steps

| Step | Reads | Writes |
| :--- | :--- | :--- |
| Search | A query | Lines whose last field is `webpage_url` |
| Select | The user asked for N items, or picks from the list | `sources.txt`, one URL per line |
| Subtitles | Those URLs | `subs/*.srt` |
| Text | Those subtitle files | `text/*.txt` or `text/<stem>/part-NNN.txt` |
| ASR, only after a yes | The same URLs, if subs were missing | `asr/*.json`, then more text files |
| Report | The text files | `report.md` from `references/report-template.md` |

Keep `webpage_url` as returned. Do not build `https://www.youtube.com/watch?v=ID`.

## 1. Search

```bash
yt-dlp --flat-playlist --print "%(title)s | %(duration_string)s | %(uploader)s | %(webpage_url)s" "ytsearch8:QUERY"
yt-dlp --flat-playlist --print "%(title)s | %(duration_string)s | %(uploader)s | %(webpage_url)s" "bilisearch8:QUERY"
```

Show the list. If the user said "3 videos", choose three of these URLs and write them to `sources.txt`. If they did not say how many, ask.

## 2. Subtitles

No confirmation. This does not download the video.

```bash
TASK="${MEDIA_OUTPUT_DIR:-./output}/TASK"
mkdir -p "$TASK/subs"
while IFS= read -r url; do
  yt-dlp --write-sub --write-auto-sub \
    --sub-langs "zh-Hans,zh-CN,en.*,en" \
    --convert-subs srt \
    --skip-download \
    -P "$TASK/subs" -o "%(id)s.%(ext)s" "$url"
done < "$TASK/sources.txt"
```

Manual subtitles beat automatic captions. Say which kind you used in the report.

## 3. Timestamped text

```bash
bash scripts/subs_to_text.sh "$TASK"/subs/*.srt -o "$TASK/text"
```

Each cue becomes:

```text
[00:01:15.000 --> 00:01:18.200]
the words, including lines that start with numbers
```

Default chunk size is 12000 characters. A short file is one `.txt`. A long file becomes `text/<stem>/part-001.txt` plus `INDEX.txt`. Read the parts in order. Do not run `sed '/^[0-9]/d'` on subtitles; that deletes real lines such as "2026 results".

## 4. ASR only when subtitles are missing

Tell the user, with the script's own plan:

```bash
bash scripts/transcribe.sh --model small --probe-url "URL"
```

That exits 0 and prints:

- which URL
- duration
- model (`small` unless they asked otherwise)
- whether the weights are cached, or the first-download size (`large-v3` is about 2.9 GiB)
- estimated audio size
- a rough CPU time note (order of the audio duration for `small` int8, not a quote)

Wait. After they agree:

```bash
bash scripts/bootstrap.sh --yes --with-asr   # only if the plan said the venv is missing; ask first
bash scripts/transcribe.sh --yes --model small --probe-url "URL"
bash scripts/subs_to_text.sh "$TASK"/asr/*.json -o "$TASK/text"
```

`--yes` on transcribe downloads the audio and may download the model. Both sizes were in the plan.

## 5. The agent writes the report

Read `text/`. Copy `references/report-template.md` to `$TASK/report.md`. Fill it. Cite timestamps from the text. This is the agent's job. Do not call another model from a script.

## Worked example

User: `帮我搜 3 个关于 X 的视频并总结`

```bash
# skill root, for example ~/.hermes/skills/media/media-toolkit
bash scripts/doctor.sh

TASK="${MEDIA_OUTPUT_DIR:-./output}/x-topic"
mkdir -p "$TASK"

# search: no ask
yt-dlp --flat-playlist --print "%(title)s | %(duration_string)s | %(uploader)s | %(webpage_url)s" \
  "ytsearch8:X" | tee "$TASK/search.txt"
# agent picks 3 webpage_url lines into "$TASK/sources.txt"

# subtitles: no ask
mkdir -p "$TASK/subs"
while IFS= read -r url; do
  yt-dlp --write-sub --write-auto-sub --sub-langs "zh-Hans,zh-CN,en.*,en" \
    --convert-subs srt --skip-download -P "$TASK/subs" -o "%(id)s.%(ext)s" "$url"
done < "$TASK/sources.txt"

bash scripts/subs_to_text.sh "$TASK"/subs/*.srt -o "$TASK/text"

# if one URL had no subtitles, stop and show the plan:
bash scripts/transcribe.sh --model small --probe-url "THAT_URL"
# wait for the user, then and only then:
# bash scripts/transcribe.sh --yes --model small --probe-url "THAT_URL"

# do not download the full videos unless the user also wants the files.
# if they do:
bash scripts/download.sh URL1 URL2 URL3
# show count and known-bytes, wait, then:
# bash scripts/download.sh --yes URL1 URL2 URL3

# agent reads "$TASK/text" and writes "$TASK/report.md"
# template: references/report-template.md
```

Cookies, if a page asks for a login: ask once which browser and profile, then `bash scripts/download.sh --yes --cookies-from-browser "chrome:Profile 1" URL`.
