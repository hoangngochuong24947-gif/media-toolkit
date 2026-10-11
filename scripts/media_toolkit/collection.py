"""Checkpointed keyword discovery and batch acquisition; no completeness claim."""
import csv
import hashlib
import html
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import online
from .runtime import ToolkitError

VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')


def write_json(path, document):
    fd, name = tempfile.mkstemp(prefix='.checkpoint-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextmanager
def job(directory):
    root = Path(directory).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = root / '.job.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ToolkitError('Job is locked; check that no process is running before removing .job.lock', 'job_locked') from None
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(str(os.getpid()))
        yield root
    finally:
        lock.unlink(missing_ok=True)


def load(root):
    try:
        state = json.loads((root/'state.json').read_text(encoding='utf-8'))
        if state['schema'] != 1 or not isinstance(state['videos'], dict):
            raise ValueError('Unsupported job schema')
        if any(not VIDEO_ID.fullmatch(key) for key in state['videos']):
            raise ValueError('Invalid video ID in checkpoint')
        return state
    except (ValueError, KeyError, OSError) as exc:
        raise ToolkitError(f'Invalid collection checkpoint: {exc}', 'checkpoint_invalid') from None


def search_page(runner, query, start, size, js_runtime=None, sort='relevance'):
    args = online.options(js_runtime=online.resolve_runtime(runner,js_runtime))
    args.remove('--no-playlist')
    output = runner.run('yt-dlp', [*args, '--flat-playlist', '--dump-single-json',
                                  '-I', f'{start}:{start+size-1}', f'{"ytsearchdateall" if sort=="date" else "ytsearchall"}:{query}'])
    try:
        document = json.loads(output)
        entries = document.get('entries')
        if not isinstance(entries, list) or any(e is None for e in entries):
            raise ValueError('Search contains unavailable entries; exhaustion cannot be inferred')
        return entries
    except (ValueError, AttributeError) as exc:
        raise ToolkitError(f'Invalid search page: {exc}', 'search_failed') from None


def collect(runner, queries, directory, *, page_size=50, max_videos=500, max_pages=20, js_runtime=None, sort='relevance'):
    queries = list(dict.fromkeys(q.strip() for q in queries if q.strip()))
    if sort not in ('relevance','date') or not queries or not 1 <= page_size <= 100 or not 1 <= max_videos <= 100000 or not 1 <= max_pages <= 10000:
        raise ToolkitError('Query/budgets invalid (page 1..100, videos 1..100000, pages 1..10000)', 'invalid_argument')
    with job(directory) as root:
        if (root/'state.json').exists():
            state = load(root)
            if [q['query'] for q in state['queries']] != queries:
                raise ToolkitError('Use a new directory for changed queries', 'query_mismatch')
            if state.get('sort','relevance') != sort:
                raise ToolkitError('Use a new directory for changed search ordering','query_mismatch')
        else:
            if any(p.name != '.job.lock' for p in root.iterdir()):
                raise ToolkitError('New collection requires an empty directory', 'output_exists')
            state = dict(schema=1, created=datetime.now(timezone.utc).isoformat(),
                         queries=[dict(query=q, next_start=1, exhausted=False) for q in queries], videos={},sort=sort,next_query=0)
        state['status'] = 'partial'; state['stop_reason'] = 'page_limit'
        state['error'] = None
        save(root, state)
        pages = 0
        try:
            while pages < max_pages and any(not q['exhausted'] for q in state['queries']):
                index=state.get('next_query',0)%len(state['queries'])
                query=state['queries'][index]
                if query['exhausted']:
                    state['next_query']=(index+1)%len(state['queries']); continue
                if not query['exhausted']:
                    if pages >= max_pages:
                        break
                    if len(state['videos']) >= max_videos:
                        state['stop_reason'] = 'video_limit'; break
                    extra={} if sort=='relevance' else {'sort':sort}
                    entries = search_page(runner, query['query'], query['next_start'], page_size, js_runtime,**extra)
                    pages += 1
                    overflow = False
                    for entry in entries:
                        identity = entry.get('id')
                        if not isinstance(identity, str) or not VIDEO_ID.fullmatch(identity):
                            raise ToolkitError('Search returned an invalid video ID', 'search_failed')
                        if identity not in state['videos']:
                            if len(state['videos']) >= max_videos:
                                overflow = True; break
                            state['videos'][identity] = dict(id=identity, title=entry.get('title') or identity,
                                uploader=entry.get('uploader'), channel_id=entry.get('channel_id'),
                                duration=entry.get('duration'), url=f'https://www.youtube.com/watch?v={identity}',
                                queries=[], stages={})
                        origins = state['videos'][identity]['queries']
                        if query['query'] not in origins:
                            origins.append(query['query'])
                    if overflow:
                        state['stop_reason'] = 'video_limit'
                        save(root, state); break
                    query['next_start'] += len(entries)
                    query['exhausted'] = len(entries) < page_size
                    state['next_query']=(index+1)%len(state['queries'])
                    save(root, state)
                if pages >= max_pages or state['stop_reason'] == 'video_limit':
                    break
            if all(q['exhausted'] for q in state['queries']):
                state['status'] = 'source_exhausted'; state['stop_reason'] = 'search_returned_no_more'
        except ToolkitError as exc:
            state['stop_reason'] = exc.code
            state['error'] = dict(code=exc.code, message=str(exc))
        save(root, state)
        return result(root, state, 'collect')


def verified_artifact(path, *, source=None, command=None):
    try:
        receipt = json.loads(Path(str(path)+'.result.json').read_text(encoding='utf-8'))
        with path.open('rb') as stream:
            checksum = hashlib.sha256()
            for block in iter(lambda: stream.read(1024*1024), b''):
                checksum.update(block)
        return bool(receipt.get('ok') and path.stat().st_size == receipt['bytes'] and
                    checksum.hexdigest() == receipt['sha256'] and
                    (source is None or receipt.get('source') == source) and
                    (command is None or receipt.get('command') == command))
    except (OSError, ValueError, KeyError):
        return False


def batch(runner, directory, *, stage='subtitles', limit=10, languages='en', js_runtime=None,
          channel_ids=None, video_ids=None, retry_failed=False):
    if stage not in ('subtitles', 'download') or not 1 <= limit <= 10000:
        raise ToolkitError('Invalid stage or batch limit', 'invalid_argument')
    if stage == 'download' and not channel_ids:
        raise ToolkitError('Bulk download requires an explicit channel-ID allowlist', 'invalid_argument')
    with job(directory) as root:
        state = load(root)
        if video_ids and any(i not in state['videos'] for i in video_ids):
            raise ToolkitError('Selected video IDs must exist in this collection', 'invalid_argument')
        processed = 0; blocked = None
        for identity, item in state['videos'].items():
            if video_ids and identity not in video_ids:
                continue
            extension = '.json' if stage == 'subtitles' else '.mp4'
            path = root / stage / (identity + extension)
            command = 'fetch-subs' if stage == 'subtitles' else 'download'
            record = item['stages'].get(stage, {})
            if stage == 'download' and record.get('status') == 'excluded' and not retry_failed:
                continue
            if verified_artifact(path, source=item['url'], command=command):
                item['stages'][stage] = dict(status='success', file=str(path.relative_to(root)))
                continue
            if record.get('status') == 'failed' and not retry_failed:
                continue
            if processed >= limit:
                break
            processed += 1
            try:
                if path.exists() or Path(str(path)+'.result.json').exists():
                    raise ToolkitError('Existing artifact is incomplete or damaged; preserve it and use a new job', 'artifact_damaged')
                if stage == 'download':
                    info = json.loads(runner.run('yt-dlp', [*online.options(js_runtime=js_runtime), '--skip-download', '--dump-single-json', item['url']]))
                    item['channel_id'] = info.get('channel_id')
                    item['channel_is_verified'] = info.get('channel_is_verified')
                    if item['channel_id'] not in channel_ids:
                        item['stages'][stage] = dict(status='excluded', reason='channel_not_in_allowlist')
                        save(root, state); continue
                    receipt = online.download(runner, item['url'], path, js_runtime=js_runtime)
                else:
                    receipt = online.fetch_subs(runner, item['url'], path, languages=languages, js_runtime=js_runtime)
                if not receipt.get('ok') or not verified_artifact(path, source=item['url'], command=command):
                    raise ToolkitError('Batch artifact failed receipt validation', 'artifact_damaged')
                item['stages'][stage] = dict(status='success', file=str(path.relative_to(root)))
            except (ToolkitError, ValueError) as exc:
                code = exc.code if isinstance(exc, ToolkitError) else 'metadata_invalid'
                item['stages'][stage] = dict(status='failed', error=dict(code=code, message=str(exc)))
                if code in ('rate_limit', 'access_denied', 'network', 'timeout'):
                    blocked = code
            save(root, state)
            if blocked:
                break
        save(root, state)
        selected = [v for k,v in state['videos'].items() if not video_ids or k in video_ids]
        counts = {s: sum(v['stages'].get(stage, {}).get('status', 'pending') == s for v in selected)
                  for s in ('success', 'failed', 'pending', 'excluded')}
        status = 'success' if counts['pending'] == counts['failed'] == 0 else 'partial'
        return dict(ok=status == 'success', command='batch', status=status, stage=stage,
                    counts=counts, processed=processed, stop_reason=blocked or ('item_limit_or_unretried_failures' if status=='partial' else 'selected_items_finished'),
                    output=str(root/'index.html'), coverage=dict(all_platform_videos=False))


def result(root, state, command):
    return dict(ok=state.get('error') is None, command=command, status=state['status'],
                stop_reason=state['stop_reason'], counts=dict(videos=len(state['videos'])),
                coverage=dict(all_platform_videos=False, queries=state['queries'],
                              explanation='Search exhaustion is not proof of complete YouTube topic coverage; rankings may change during resume'),
                output=str(root/'index.html'), error=state.get('error'))


def save(root, state):
    write_json(root/'state.json', state)
    rows = []
    with (root/'videos.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['video_id','title','uploader','url','subtitle_status','download_status'])
        for item in state['videos'].values():
            # Neutralize spreadsheet formulas in untrusted external text.
            def cell(value):
                text = str(value or '')
                return "'"+text if text.lstrip().startswith(('=','+','-','@')) else text
            statuses = [item['stages'].get(s, {}).get('status','pending') for s in ('subtitles','download')]
            writer.writerow([cell(item['id']),cell(item['title']),cell(item.get('uploader')),item['url'],*statuses])
            title = html.escape(str(item['title'])); uploader = html.escape(str(item.get('uploader') or '未知频道'))
            links = []
            for stage in ('subtitles','download'):
                record = item['stages'].get(stage, {})
                label = {'success':'完成','failed':'失败','pending':'待处理','excluded':'范围外'}.get(record.get('status','pending'))
                error = html.escape(str(record.get('error',{}).get('message','')))
                stage_label = '字幕' if stage == 'subtitles' else '视频'
                if record.get('file'):
                    safe_path = html.escape(record['file'], quote=True)
                    links.append(f'<a href="{safe_path}">{stage_label}: {label}</a>')
                else:
                    links.append(f'<span title="{error}">{stage_label}: {label}</span>')
            rows.append(f'<tr><td><a href="{item["url"]}">{title}</a></td><td>{uploader}</td><td>{" · ".join(links)}</td></tr>')
    status = {'partial':'尚未采集完','source_exhausted':'本次搜索已无更多返回'}.get(state.get('status'),'需要检查')
    reason = {'page_limit':'达到本轮处理页数，可继续汇总','video_limit':'达到本轮视频数量，可提高数量后继续',
              'search_returned_no_more':'平台本次搜索已无更多返回','rate_limit':'平台限制访问频率，已停止',
              'access_denied':'平台拒绝访问，已停止','network':'网络连接失败，已停止',
              'timeout':'请求超时，已保留进度'}.get(state.get('stop_reason'),'采集发生异常，请查看核验记录')
    query = html.escape(' / '.join(q['query'] for q in state['queries']))
    document = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>YouTube 视频汇总</title><link rel="icon" href="data:,"><style>body{{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px;background:#fafafa;color:#222}}table{{width:100%;border-collapse:collapse}}td,th{{text-align:left;padding:14px;border-bottom:1px solid #ddd}}a{{color:#175ca4}}input{{padding:12px;width:80%}}.note{{background:#fff2ce;padding:18px}}</style>
<h1>YouTube 视频汇总</h1><p>{query} · 已发现 {len(state['videos'])} 条</p>
<p class="note">采集状态：{status}；停止原因：{reason}。这是平台搜索返回的视频清单，不保证全站无遗漏，也不代表所有候选相关或官方。字幕与下载状态独立记录；字幕自动识别可能有误。</p>
<p><a href="videos.csv">下载清单 CSV</a> · <a href="state.json">查看核验与续跑记录</a></p>
<input id="filter" placeholder="按标题或频道筛选"><table><thead><tr><th>视频</th><th>频道</th><th>处理结果</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<script>document.getElementById('filter').addEventListener('input',function(){{const q=this.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q))}})</script></html>'''
    (root/'index.html').write_text(document, encoding='utf-8')
