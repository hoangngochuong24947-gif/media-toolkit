"""Runtime-tested hardware selection; capability presence is not readiness."""
import sys
from .runtime import ToolkitError

ENCODERS=('cpu','auto','nvenc','videotoolbox','qsv','vaapi')


def encode(runner, source, output, audio_args, *, encoder, codec, crf, hw_device):
    if encoder not in ENCODERS or codec not in ('h264','h265'):
        raise ToolkitError('Unsupported encoder or codec','invalid_argument')
    prefix='h264' if codec=='h264' else 'hevc'
    cpu='libx264' if codec=='h264' else 'libx265'
    if encoder=='auto':
        candidates=['videotoolbox','cpu'] if sys.platform=='darwin' else ['nvenc','qsv','cpu']
        if sys.platform.startswith('linux'): candidates=['nvenc','vaapi','qsv','cpu']
    else: candidates=[encoder] if encoder=='cpu' else [encoder,'cpu']
    scale='scale=trunc(iw/2)*2:trunc(ih/2)*2'
    for attempt, candidate in enumerate(candidates,1):
        chosen=cpu if candidate=='cpu' else prefix+'_'+candidate
        pre=[]; filt=scale; pix=['-pix_fmt','yuv420p']
        if candidate=='cpu':
            params=['-preset','slow','-crf',str(crf)]
            if codec=='h265': params+=['-x265-params','pools=2:frame-threads=2']
        elif candidate=='nvenc': params=['-preset','p4','-cq',str(crf)]
        elif candidate=='qsv': params=['-preset','medium','-global_quality',str(crf)]; pix=['-pix_fmt','nv12']
        elif candidate=='videotoolbox': params=['-b:v','2000k','-allow_sw','0']
        else:
            pre=['-vaapi_device',hw_device]; filt=scale+',format=nv12,hwupload'; pix=[]
            params=['-qp',str(crf)]
        try:
            runner.ffmpeg([*pre,'-i',source,'-map','0:v:0','-map','0:a:0?', '-vf',filt,*pix,'-c:v',chosen,*params,*audio_args,output])
            info=runner.validate_media(output,video=True)
            expected='h264' if codec=='h264' else 'hevc'
            if next(s for s in info['streams'] if s['codec_type']=='video')['codec_name']!=expected:
                raise ToolkitError('Encoder produced unexpected codec','validation_failed')
            runner.events.append(dict(encoder=chosen,status='validated',hardware=candidate!='cpu'))
            return chosen, attempt>1, attempt
        except ToolkitError as exc:
            if candidate=='cpu' or exc.code not in ('process_failed','timeout','validation_failed'): raise
            runner.events.append(dict(encoder=chosen,status='failed',reason=exc.code,detail=str(exc)[-1000:]))
            if candidates[attempt]=='cpu': runner.events.append(dict(fallback=candidate+'_to_cpu',reason=exc.code))
    raise ToolkitError('No encoder completed','process_failed')
