"""Opt-in, bounded network operations. No browser credential access."""
import json
import re
import hashlib
import os
from pathlib import Path
from .runtime import Artifact, ToolkitError
from .subtitles import parse_subtitles, clean_text


def options(cookies=None, js_runtime=None):
    args=['--ignore-config','--socket-timeout','10','--retries','1','--extractor-retries','1','--no-playlist','--no-progress']
    if cookies:
        from .runtime import input_file
        args+=['--cookies',str(input_file(cookies))]
    if js_runtime:
        args+=['--js-runtimes',js_runtime]
    return args


def url(value):
    if not re.match(r'^https?://',value,re.I):
        raise ToolkitError('Provide an explicit http(s) URL','invalid_argument')
    return value


def resolve_runtime(runner,value):
    if value in (None,'node') and getattr(runner,'tool_paths',{}).get('node'):
        return 'node:'+runner.tool('node')
    return value


def search(runner, query, *, platform='youtube', count=5, js_runtime=None, sort='relevance'):
    if not query.strip() or not 1<=count<=20:
        raise ToolkitError('Nonempty query and count 1..20 required','invalid_argument')
    if sort not in ('relevance','date') or (sort=='date' and platform!='youtube'):
        raise ToolkitError('Date search currently supports YouTube only','invalid_argument')
    prefix=('ytsearchdate' if sort=='date' else 'ytsearch') if platform=='youtube' else 'bilisearch'
    try:
        document=json.loads(runner.run('yt-dlp',[*options(js_runtime=resolve_runtime(runner,js_runtime)),'--flat-playlist','--dump-single-json',f'{prefix}{count}:{query}']))
    except ValueError:
        raise ToolkitError('Search returned malformed JSON','search_failed') from None
    entries=document.get('entries') or []
    candidates=[dict(id=e.get('id'),title=e.get('title'),url=e.get('webpage_url') or e.get('url'),uploader=e.get('uploader'),duration=e.get('duration')) for e in entries if e]
    if not candidates:
        raise ToolkitError('Search returned no candidates','search_empty')
    return dict(ok=True,command='search',preview=True,candidates=candidates,warning='Ranking does not establish official status or authority',events=runner.events)


def download(runner, source, output, *, cookies=None, js_runtime=None):
    return transfer(runner,source,output,cookies=cookies,js_runtime=js_runtime,audio=False)


def transfer(runner,source,output,*,cookies=None,js_runtime=None,audio=False):
    from .collection import job,write_json
    url(source)
    ffmpeg=runner.tool('ffmpeg');runner.tool('ffprobe')
    # Reserve publication before touching persistent state; never overwrite finals.
    artifact=Artifact(output)
    workspace=Path(str(artifact.output)+'.download')
    identity=dict(source=source,command='download-audio' if audio else 'download',schema=1)
    with job(workspace) as work:
        checkpoint=work/'transfer.json'
        if checkpoint.exists():
            if json.loads(checkpoint.read_text(encoding='utf-8'))!=identity:
                raise ToolkitError('Transfer checkpoint belongs to another source/settings','checkpoint_mismatch')
        elif any(p.name!='.job.lock' for p in work.iterdir()):
            raise ToolkitError('Unknown files in transfer workspace; choose a fresh output','checkpoint_invalid')
        else: write_json(checkpoint,identity)
        args=options(cookies,resolve_runtime(runner,js_runtime));args.remove('--no-progress')
        args+=['--continue','--part','--fragment-retries','1','--newline','--progress','--progress-delta','2',
               '--progress-template','download:MTK_PROGRESS:%(progress)j','--ffmpeg-location',ffmpeg]
        if audio:
            args+=['-f','bestaudio/best','-x','--audio-format','wav','-o',str(work/'audio.%(ext)s')]
            downloaded=work/'audio.wav'
        else:
            args+=['-f','bestvideo+bestaudio/best','--merge-output-format','mp4','--remux-video','mp4','-o',str(work/'download.%(ext)s')]
            downloaded=work/'download.mp4'
        with artifact:
            runner.run('yt-dlp',[*args,source])
            if not downloaded.exists(): raise ToolkitError('Expected completed transfer not found','download_failed')
            info=runner.validate_media(downloaded,video=not audio,audio=True)
            os.link(downloaded,artifact.path)
            from .operations import summary
            result=artifact.publish(dict(command=identity['command'],source=source,preview=True,
                                         requested=dict(quality='best available',four_k_guaranteed=False),
                                         actual=summary(info),validated=dict(decodable=True),events=runner.events,
                                         resumable_workspace=str(work)))
        # Remove only the extra link after verified publication. Preserve parts/logs.
        downloaded.unlink()
        return result


def fetch_subs(runner, source, output, *, languages='zh-Hans,zh-CN,en,en-US', cookies=None, js_runtime=None):
    url(source)
    with Artifact(output) as artifact:
        runner.run('yt-dlp',[*options(cookies,resolve_runtime(runner,js_runtime)),'--write-sub','--write-auto-sub','--write-info-json','--sub-format','vtt/srt/best','--sub-lang',languages,'--skip-download','-o',str(artifact.directory/'talk.%(ext)s'),source])
        metadata_path = artifact.directory/'talk.info.json'
        metadata = json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.exists() else {}
        candidates=sorted([*artifact.directory.glob('*.vtt'),*artifact.directory.glob('*.srt')])
        if not candidates:
            raise ToolkitError('No subtitle file obtained; transcription is a separate opt-in step','subtitles_unavailable')
        documents=[]
        for path in candidates:
            documents.append(caption_document(path, metadata))
        artifact.path.write_text(json.dumps(dict(source=source,video=dict(id=metadata.get('id'),title=metadata.get('title'),duration=metadata.get('duration')),subtitles=documents),ensure_ascii=False,indent=2),encoding='utf-8')
        return artifact.publish(dict(command='fetch-subs',source=source,preview=True,actual=dict(files=len(documents)),validated=dict(parsed=True),events=runner.events))


def caption_document(path, metadata):
    raw = path.read_text(encoding='utf-8-sig')
    cues = parse_subtitles(raw)
    language = path.name[len('talk.'):-len(path.suffix)]
    kind = 'manual' if language in (metadata.get('subtitles') or {}) else (
        'automatic' if language in (metadata.get('automatic_captions') or {}) else 'unknown')
    warnings = ['ASR errors may remain; no semantic corrections applied'] if kind != 'manual' else []
    duration = metadata.get('duration')
    intervals = sorted((c['start'], c['end']) for c in cues)
    covered = 0.0; end = 0.0
    for start, stop in intervals:
        covered += max(0, stop - max(start, end)); end = max(end, stop)
    text = clean_text(cues)
    return dict(file=path.name, language=language, kind=kind, raw=raw,
                raw_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), text=text, cues=cues,
                quality=dict(raw_lines=sum(len(c['text'].splitlines()) for c in cues),
                             cleaned_lines=len(text.splitlines()), speech_interval_seconds=round(covered,3),
                             timeline_fraction=min(1, covered/duration) if duration else None,
                             warnings=warnings, coverage_is_accuracy=False))


def download_audio(runner, source, output, *, js_runtime=None, cookies=None):
    return transfer(runner,source,output,cookies=cookies,js_runtime=js_runtime,audio=True)
