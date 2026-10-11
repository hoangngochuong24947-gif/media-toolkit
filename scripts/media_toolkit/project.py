"""Persistent customer task: explicit scope, verified artifacts, no hidden LLM."""
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path

from . import collection, online, transcription
from .reporting import report
from .runtime import Artifact, ToolkitError, input_file


def now():
    return datetime.now(timezone.utc).isoformat()


def read(root):
    try:
        data=json.loads((root/'project.json').read_text(encoding='utf-8'))
        if data['schema']!=1 or not isinstance(data['selected'],dict): raise ValueError('schema')
        for identity,item in data['selected'].items():
            if not collection.VIDEO_ID.fullmatch(identity) or item['url']!=f'https://www.youtube.com/watch?v={identity}': raise ValueError('video identity')
        return data
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise ToolkitError(f'Invalid project checkpoint: {exc}','checkpoint_invalid') from None


def save(root,state):
    state['updated']=now()
    collection.write_json(root/'project.json',state)
    summary=describe(root,state)
    rows=[]
    for identity,item in state['selected'].items():
        links=[]
        for stage,record in item['stages'].items():
            label=html.escape(stage+': '+record['status'])
            if record.get('file') and record['status']=='success': links.append(f'<a href="{html.escape(record["file"],quote=True)}">{label}</a>')
            else: links.append(label)
        rows.append(f'<tr><td><a href="{item["url"]}">{html.escape(identity)}</a></td><td>{html.escape(item["reason"])}</td><td>{" · ".join(links)}</td></tr>')
    doc=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>媒体任务</title>
<style>body{{font:16px system-ui;max-width:1050px;margin:40px auto;padding:20px;background:#fafafa}}td,th{{padding:15px;text-align:left;border-bottom:1px solid #ddd}}a{{color:#175ca4}}pre{{white-space:pre-wrap}}.note{{background:#fff2ce;padding:16px}}</style>
<h1>媒体任务</h1><p>{html.escape(state['request']['request'])}</p>
<p class="note">状态：{summary['status']}。发现清单、实际阅读和视频下载分别记录。不是全平台穷尽搜索。</p>
<p>查询：{html.escape(' / '.join(state['request']['queries']))}；范围：{html.escape(json.dumps(state['request']['search'],ensure_ascii=False))}</p>
<p><a href="discovery/index.html">搜索候选</a> · <a href="project.json">任务记录</a> · <a href="report.md">研报</a> · <a href="progress/current.json">当前进度</a></p>
<table><tr><th>视频</th><th>选取原因</th><th>结果</th></tr>{''.join(rows)}</table>
<h2>后续步骤</h2><pre>{html.escape(summary['next_action'])}</pre></html>'''
    (root/'index.html').write_text(doc,encoding='utf-8')


def init(request,directory):
    data=json.loads(input_file(request).read_text(encoding='utf-8-sig'))
    if not isinstance(data,dict) or not isinstance(data.get('request'),str) or not data['request'].strip():
        raise ToolkitError('Request JSON must contain original request text','invalid_argument')
    queries=data.get('queries')
    if not isinstance(queries,list) or not queries or any(not isinstance(q,str) or not q.strip() for q in queries):
        raise ToolkitError('Request requires explicit nonempty query strings','invalid_argument')
    data['queries']=list(dict.fromkeys(q.strip() for q in queries))
    if not isinstance(data.get('search',{}),dict): raise ToolkitError('search must be an object','invalid_argument')
    scope={'page_size':10,'max_videos':50,'max_pages':10,'sort':'relevance',**data.get('search',{})}
    if any(type(scope[k])!=int or not 1<=scope[k]<=limit for k,limit in [('page_size',100),('max_videos',100000),('max_pages',10000)]) or scope['sort'] not in ('relevance','date'):
        raise ToolkitError('Invalid search scope','invalid_argument')
    if set(scope)-{'page_size','max_videos','max_pages','sort'}: raise ToolkitError('Unsupported search filter; do not pretend it is applied','invalid_argument')
    data['search']=scope
    data.setdefault('report_required',True)
    if type(data['report_required'])!=bool: raise ToolkitError('report_required must be boolean','invalid_argument')
    data.setdefault('subtitles_languages','zh-Hans,zh-CN,en,en-US')
    if not isinstance(data['subtitles_languages'],str) or not data['subtitles_languages'].strip():raise ToolkitError('subtitles_languages must be nonempty text','invalid_argument')
    if data.get('js_runtime') is not None and not isinstance(data['js_runtime'],str):raise ToolkitError('js_runtime must be text','invalid_argument')
    data.setdefault('asr',{'enabled':True})
    if not isinstance(data['asr'],dict): raise ToolkitError('asr must be an object','invalid_argument')
    if type(data['asr'].get('enabled',True))!=bool or type(data['asr'].get('allow_model_download',False))!=bool:
        raise ToolkitError('ASR permission flags must be boolean','invalid_argument')
    for key in ('model','cache_dir','hotwords','language'):
        if key in data['asr'] and not isinstance(data['asr'][key],str):raise ToolkitError(f'ASR {key} must be text','invalid_argument')
    if not isinstance(data.get('seed_videos',[]),list):raise ToolkitError('seed_videos must be a list','invalid_argument')
    for item in data.get('seed_videos',[]):
        if not isinstance(item,dict) or not collection.VIDEO_ID.fullmatch(str(item.get('id',''))): raise ToolkitError('Invalid seed video','invalid_argument')
    root=Path(directory).expanduser().resolve()
    with collection.job(root):
        if any(p.name!='.job.lock' for p in root.iterdir()): raise ToolkitError('New project needs an empty directory','output_exists')
        state={'schema':1,'created':now(),'request':data,'selected':{},'search':None,'report':None}
        save(root,state)
    return {**describe(root,state),'ok':True}


def select(directory,video_ids,download_ids,reason):
    root=Path(directory).resolve()
    if not isinstance(reason,str) or not reason.strip(): raise ToolkitError('Record why these videos were selected','invalid_argument')
    with collection.job(root):
        state=read(root)
        candidates={i['id']:i for i in state['request'].get('seed_videos',[])}
        if (root/'discovery/state.json').exists(): candidates.update(collection.load(root/'discovery')['videos'])
        selected=list(dict.fromkeys([*video_ids,*download_ids]))
        if not selected: raise ToolkitError('Selection must name at least one video','invalid_argument')
        if any(identity not in candidates for identity in selected): raise ToolkitError('Select only discovered or explicitly recorded seed IDs','invalid_argument')
        for identity in selected:
            item=state['selected'].setdefault(identity,{'url':f'https://www.youtube.com/watch?v={identity}','reason':reason,'transcript':bool(state['request']['report_required'] or identity in video_ids),'download':False,'stages':{}})
            item['download']=item['download'] or identity in download_ids
            item['transcript']=item['transcript'] or identity in video_ids
        save(root,state)
    return {**describe(root,state),'ok':True}


def verified(root,record):
    if not isinstance(record,dict) or record.get('status')!='success':return False
    path=Path(record.get('file',''))
    if path.is_absolute() or '..' in path.parts:return False
    return collection.verified_artifact(root/path,command=record.get('command'),source=record.get('source'))


def describe(root,state):
    failed=[];pending=[]
    for identity,item in state['selected'].items():
        for stage,wanted in [('transcript',item['transcript']),('video',item['download'])]:
            if not wanted:continue
            record=item['stages'].get(stage,{})
            if not verified(root,record):
                (failed if record.get('status') in ('failed','cancelled','success') else pending).append(f'{identity}:{stage}')
    needed={i for i,item in state['selected'].items() if item['transcript']}
    report_ok=verified(root,state.get('report')) and set(state['report'].get('videos',[]))>=needed
    if not state['selected']:
        status='awaiting_selection';next_action='Read discovery/index.html; select video IDs and download IDs with a recorded reason.'
    elif failed or pending:
        status='partial';next_action='Run project run again; failed/cancelled stages require --retry-failed. Damaged outputs are preserved; choose a fresh project to regenerate.'
    elif state['request']['report_required'] and not report_ok:
        status='awaiting_report';next_action='Read verified transcripts, author claims JSON, then project report --claims CLAIMS.json. Do not invent conclusions from titles.'
    else:
        status='success';next_action='Requested selected artifacts verified; open index.html. Search coverage remains bounded as recorded.'
    return {'ok':status=='success','complete':status=='success','command':'project','status':status,'selected':len(state['selected']),'failed':failed,'pending':pending,'search':state['search'],'scope':state['request']['search'],'output':str(root/'index.html'),'next_action':next_action}


def status(directory):
    root=Path(directory).resolve();return describe(root,read(root))


def stage(runner,root,state,item,key,target,fn,*,source,command,retry_failed=False,**kwargs):
    previous=item['stages'].get(key,{})
    if verified(root,previous):return True
    if previous.get('status')=='success':
        item['stages'][key]={**previous,'status':'failed','error':{'code':'artifact_damaged','message':'Published artifact/receipt changed; preserved'}};save(root,state);return False
    if previous.get('status') in ('failed','cancelled') and not retry_failed:return False
    target=root/target
    # Recover publication/checkpoint gap without re-running a successful command.
    if collection.verified_artifact(target,source=source,command=command):
        item['stages'][key]={'status':'success','file':str(target.relative_to(root)).replace('\\','/'),'source':source,'command':command};save(root,state);return True
    item['stages'][key]={'status':'running','started':now()};save(root,state)
    try:
        fn(runner,source,target,**kwargs)
        if not collection.verified_artifact(target,source=source,command=command):raise ToolkitError('Published receipt did not validate','artifact_invalid')
        item['stages'][key]={'status':'success','file':str(target.relative_to(root)).replace('\\','/'),'source':source,'command':command}
        success=True
    except (ToolkitError,OSError,ValueError) as exc:
        if not isinstance(exc,ToolkitError):exc=ToolkitError(str(exc),'io_or_data_error')
        item['stages'][key]={'status':'cancelled' if exc.code=='cancelled' else 'failed','error':{'code':exc.code,'message':str(exc)}};success=False
    save(root,state);return success


def run(runner,directory,*,retry_failed=False):
    root=Path(directory).resolve()
    with collection.job(root):
        state=read(root);request=state['request']
        runner.progress_dir=root/'progress';runner.progress_dir.mkdir(exist_ok=True)
        # Discovery is its own bounded coverage; it never cancels explicit selections.
        if state['search'] is None:
            budget=runner.timeout;runner.timeout=min(budget,90)
            try: state['search']=collection.collect(runner,request['queries'],root/'discovery',js_runtime=request.get('js_runtime'),**request['search'])
            finally:runner.timeout=budget
            save(root,state)
        for identity,item in state['selected'].items():
            url=item['url'];target=f'transcripts/{identity}.json'
            previous=item['stages'].get('transcript',{})
            retry_blocked=previous.get('status') in ('failed','cancelled','success') and not retry_failed
            if item['transcript'] and not verified(root,previous) and not retry_blocked:
                budget=runner.timeout;runner.timeout=min(budget,90)
                try:caption_ok=stage(runner,root,state,item,'transcript',target,online.fetch_subs,source=url,command='fetch-subs',retry_failed=retry_failed,languages=request['subtitles_languages'],js_runtime=request.get('js_runtime'))
                finally:runner.timeout=budget
                failure=item['stages'].get('transcript',{}).get('error',{})
                if not caption_ok and request['asr'].get('enabled',True) and failure.get('code') not in ('cancelled','output_exists','artifact_damaged','artifact_invalid'):
                    # Preserve caption failure as a distinct attempt, not overwrite history.
                    item['stages']['captions']=item['stages']['transcript']
                    audio_target=f'audio/{identity}.wav'
                    ready=stage(runner,root,state,item,'audio',audio_target,online.download_audio,source=url,command='download-audio',retry_failed=retry_failed,js_runtime=request.get('js_runtime'))
                    if ready:
                        asr=request['asr'];cache=Path(asr.get('cache_dir','models'))
                        if not cache.is_absolute():cache=root/cache
                        def speech(r,source,destination,**unused):
                            raw=root/f'raw-asr/{identity}.json'
                            if not collection.verified_artifact(raw,source=str(root/audio_target),command='transcribe'):
                                transcription.transcribe(r,root/audio_target,raw,model=asr.get('model','small'),language=asr.get('language'),hotwords=asr.get('hotwords',''),cache_dir=cache,allow_model_download=asr.get('allow_model_download',False))
                            doc=json.loads(raw.read_text(encoding='utf-8'));original=doc.get('source')
                            doc['source']=url;doc['provenance']={'audio_source':original,'raw_asr':str(raw.relative_to(root)),'raw_asr_sha256':hashlib.sha256(raw.read_bytes()).hexdigest()}
                            with Artifact(destination) as a:
                                a.path.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8')
                                return a.publish({'source':url,'command':'video-transcript','validated':{'cues_unchanged':True,'accuracy_certified':False}})
                        stage(runner,root,state,item,'transcript',target,speech,source=url,command='video-transcript',retry_failed=True)
                    else:
                        item['stages']['transcript']={'status':'failed','error':item['stages']['audio'].get('error',{})};save(root,state)
            # Continue selected downloads even if this video's transcript failed.
            if item['download']:
                stage(runner,root,state,item,'video',f'videos/{identity}.mp4',online.download,source=url,command='download',retry_failed=retry_failed,js_runtime=request.get('js_runtime'))
            if any(r.get('status')=='cancelled' for r in item['stages'].values()):break
        save(root,state);return describe(root,state)


def publish_report(runner,directory,claims):
    root=Path(directory).resolve()
    with collection.job(root):
        state=read(root);source=input_file(claims);data=json.loads(source.read_text(encoding='utf-8-sig'))
        if not isinstance(data,dict) or not isinstance(data.get('claims'),list) or any(not isinstance(c,dict) for c in data['claims']):raise ToolkitError('Claims input must contain a list of objects','evidence_invalid')
        covered=set(); normalized=[]
        for claim in data.get('claims',[]):
            path=Path(claim.get('transcript',''))
            if not path.is_absolute():path=source.parent/path
            path=path.resolve()
            matches=[identity for identity,item in state['selected'].items() if verified(root,item['stages'].get('transcript')) and path==(root/item['stages']['transcript']['file']).resolve()]
            if not matches:raise ToolkitError('Report may cite only verified selected video transcripts','evidence_invalid')
            covered.update(matches);normalized.append({**claim,'transcript':str(path.relative_to(root)).replace('\\','/')})
        required={identity for identity,item in state['selected'].items() if item['transcript']}
        if not required<=covered:raise ToolkitError('Report omits selected transcript sources','evidence_invalid')
        if (root/'claims.json').exists():
            if collection.verified_artifact(root/'report.md',source=str(root/'claims.json'),command='report'):
                old=json.loads((root/'claims.json').read_text(encoding='utf-8'))
                if old.get('claims')==normalized:
                    state['report']={'status':'success','file':'report.md','source':str(root/'claims.json'),'command':'report','videos':sorted(covered)}
                    save(root,state);return describe(root,state)
            raise ToolkitError('Report already authored; preserve it or use a new project','output_exists')
        data['claims']=normalized;data['coverage']=str(data.get('coverage',''))+'\nRecorded search scope: '+json.dumps(state['request']['search'])+'; selected videos: '+', '.join(sorted(required))
        (root/'claims.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        try:report(runner,root/'claims.json',root/'report.md')
        except (ToolkitError,OSError,ValueError):
            # Preserve rejected authoring input; allow corrected claims on retry.
            (root/'claims.json').rename(root/f'claims-rejected-{datetime.now().strftime("%Y%m%d%H%M%S%f")}.json');raise
        state['report']={'status':'success','file':'report.md','source':str(root/'claims.json'),'command':'report','videos':sorted(covered)}
        save(root,state);return describe(root,state)


def execute(runner,args):
    if args.action=='init':
        if not args.output:raise ToolkitError('project init requires -o JOB_DIR','invalid_argument')
        return init(args.input,args.output)
    if args.action=='select':return select(args.input,args.video_ids,args.download_ids,args.reason)
    if args.action=='run':return run(runner,args.input,retry_failed=args.retry_failed)
    if args.action=='report':
        if not args.claims:raise ToolkitError('project report requires --claims JSON','invalid_argument')
        return publish_report(runner,args.input,args.claims)
    return status(args.input)
