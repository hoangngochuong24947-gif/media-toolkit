"""Cross-platform CLI. Successful and failed commands return JSON."""
import argparse
import json
import sys
from pathlib import Path
from . import __version__, operations, online, collection, transcription
from .runtime import Runner, ToolkitError, input_file
from .encoding import ENCODERS


class Parser(argparse.ArgumentParser):
    def error(self,message):
        raise ToolkitError(message,'invalid_argument')


def parser():
    p=Parser(description='Validated local media recipes; online commands are preview')
    p.add_argument('--timeout',type=float,help='Per-process timeout; default downloads/project 1800s, ASR 900s, others 300s')
    p.add_argument('--progress-dir',help='Live current.json and events.jsonl directory')
    p.add_argument('--tool-config',help='Task-local tool-path profile')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor'); s=sub.add_parser('inspect'); s.add_argument('input')
    for name in ['subtitles','compress','gif','audio','trim','image','download','fetch-subs','download-audio','report']:
        s=sub.add_parser(name); s.add_argument('input'); s.add_argument('-o','--output',required=True)
        if name=='compress':
            s.add_argument('--target-mb',type=float); s.add_argument('--crf',type=int,default=23)
            s.add_argument('--encoder',choices=ENCODERS,default='cpu'); s.add_argument('--audio-kbps',type=int,default=96)
            s.add_argument('--codec',choices=['h264','h265'],default='h264'); s.add_argument('--hw-device',default='/dev/dri/renderD128')
        if name=='audio':
            s.add_argument('--format',choices=['mp3','m4a'],default='mp3'); s.add_argument('--copy',action='store_true')
        if name=='gif':
            s.add_argument('--fps',type=int,default=15); s.add_argument('--width',type=int,default=1080); s.add_argument('--max-mb',type=float,default=5)
        if name=='trim':
            s.add_argument('--start',required=True,type=float); s.add_argument('--end',required=True,type=float)
            s.add_argument('--mode',choices=['fast','accurate'],default='accurate')
        if name=='image':
            s.add_argument('--max-side',type=int,default=1920); s.add_argument('--quality',type=int,default=82); s.add_argument('--lossless',action='store_true')
        if name in ['download','fetch-subs','download-audio']:
            s.add_argument('--cookies'); s.add_argument('--js-runtime')
        if name=='fetch-subs': s.add_argument('--languages',default='zh-Hans,zh-CN,en,en-US')
    s=sub.add_parser('images'); s.add_argument('input'); s.add_argument('-o','--output',required=True)
    s.add_argument('--max-side',type=int,default=1920); s.add_argument('--quality',type=int,default=82)
    s.add_argument('--lossless',action='store_true'); s.add_argument('--recursive',action='store_true'); s.add_argument('--retry-failed',action='store_true')
    s=sub.add_parser('search'); s.add_argument('query'); s.add_argument('--platform',choices=['youtube','bilibili'],default='youtube')
    s.add_argument('--count',type=int,default=5); s.add_argument('--js-runtime')
    s.add_argument('--sort',choices=['relevance','date'],default='relevance')
    s=sub.add_parser('collect'); s.add_argument('query'); s.add_argument('-o','--output',required=True)
    s.add_argument('--query',action='append',default=[],dest='extra_queries')
    s.add_argument('--page-size',type=int,default=50); s.add_argument('--max-videos',type=int,default=500)
    s.add_argument('--max-pages',type=int,default=20); s.add_argument('--js-runtime')
    s.add_argument('--sort',choices=['relevance','date'],default='relevance')
    s=sub.add_parser('project');s.add_argument('action',choices=['init','select','run','status','report']);s.add_argument('input')
    s.add_argument('-o','--output');s.add_argument('--video-id',action='append',default=[],dest='video_ids')
    s.add_argument('--download-id',action='append',default=[],dest='download_ids');s.add_argument('--reason',default='')
    s.add_argument('--claims');s.add_argument('--retry-failed',action='store_true')
    s=sub.add_parser('batch'); s.add_argument('input'); s.add_argument('--stage',choices=['subtitles','download'],default='subtitles')
    s.add_argument('--limit',type=int,default=10); s.add_argument('--languages',default='en'); s.add_argument('--js-runtime')
    s.add_argument('--channel-id',action='append',dest='channel_ids'); s.add_argument('--video-id',action='append',dest='video_ids')
    s.add_argument('--retry-failed',action='store_true')
    s=sub.add_parser('transcribe'); s.add_argument('input'); s.add_argument('-o','--output',required=True)
    s.add_argument('--model',default='small'); s.add_argument('--language'); s.add_argument('--hotwords',default='')
    s.add_argument('--cache-dir',required=True); s.add_argument('--allow-model-download',action='store_true')
    s.add_argument('--device',choices=['cpu','cuda'],default='cpu'); s.add_argument('--compute-type',choices=['int8','float16','float32'],default='int8')
    s=sub.add_parser('transcribe-api'); s.add_argument('input'); s.add_argument('-o','--output',required=True)
    s.add_argument('--endpoint',required=True); s.add_argument('--model',default='whisper-1'); s.add_argument('--language')
    s.add_argument('--allow-network',action='store_true')
    return p


def execute(args,runner):
    command=args.command
    if command=='doctor':
        tools={}
        for name in ['ffmpeg','ffprobe','magick','yt-dlp']:
            try:
                path=runner.tool(name)
                text=runner.run(name,['--version'] if name=='yt-dlp' else ['-version'])
                tools[name]=dict(available=True,path=path,version=text.splitlines()[0])
            except ToolkitError as exc:
                tools[name]=dict(available=False,error=str(exc))
        ready=all(tools[n]['available'] for n in ['ffmpeg','ffprobe','magick'])
        return dict(ok=ready,command=command,version=__version__,local_ready=ready,tools=tools)
    if command=='inspect':
        return dict(ok=True,command=command,media=runner.probe(input_file(args.input)))
    if command=='project':
        from .project import execute as project_execute
        return project_execute(runner,args)
    if command=='search': return online.search(runner,args.query,platform=args.platform,count=args.count,js_runtime=args.js_runtime,sort=args.sort)
    if command=='collect':
        return collection.collect(runner,[args.query,*args.extra_queries],args.output,page_size=args.page_size,
                                  max_videos=args.max_videos,max_pages=args.max_pages,js_runtime=args.js_runtime,sort=args.sort)
    if command=='batch':
        return collection.batch(runner,args.input,**{k:v for k,v in vars(args).items() if k not in ('command','input','timeout','progress_dir','tool_config')})
    if command=='images':
        from .image_batch import images
        return images(runner,args.input,args.output,**{k:v for k,v in vars(args).items() if k not in ('command','input','output','timeout','progress_dir','tool_config')})
    extensions={'subtitles':'.json','compress':'.mp4','gif':'.gif','audio':'.'+getattr(args,'format','mp3'),'trim':'.mp4','image':'.webp','download':'.mp4','fetch-subs':'.json','transcribe':'.json','download-audio':'.wav','report':'.md','transcribe-api':'.json'}
    if Path(args.output).suffix.lower()!=extensions[command]:
        raise ToolkitError(f'{command} output must end in {extensions[command]}','invalid_argument')
    extras={key:value for key,value in vars(args).items() if key not in ['command','input','output','timeout','progress_dir','tool_config']}
    if command=='transcribe-api':
        from .api_transcription import transcribe_api
        return transcribe_api(runner,args.input,args.output,**extras)
    if command=='report':
        from .reporting import report
        return report(runner,args.input,args.output)
    if command=='transcribe':
        return transcription.transcribe(runner,args.input,args.output,**extras)
    if command in ['download','fetch-subs','download-audio']:
        return getattr(online,command.replace('-','_'))(runner,args.input,args.output,**extras)
    return getattr(operations,command)(runner,args.input,args.output,**extras)


def default_timeout(command):
    return 1800 if command in ('download','download-audio','project','batch') else 900 if command=='transcribe' else 300


def main(argv=None):
    try:
        args=parser().parse_args(argv)
        progress=args.progress_dir
        if not progress and args.command in ('download','download-audio'):
            progress=str(Path(args.output).resolve())+'.progress'
        runner=Runner(args.timeout if args.timeout is not None else default_timeout(args.command),tool_config=args.tool_config,progress_dir=progress)
        result=execute(args,runner)
        print(json.dumps(result,ensure_ascii=False)); return 0 if result.get('ok') else 1
    except ToolkitError as exc:
        result=dict(ok=False,error=dict(code=exc.code,message=str(exc)))
    except (OSError,UnicodeError,ValueError) as exc:
        result=dict(ok=False,error=dict(code='io_or_data_error',message=str(exc)))
    print(json.dumps(result,ensure_ascii=False)); return 1
