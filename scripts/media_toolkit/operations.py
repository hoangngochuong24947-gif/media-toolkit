"""Local media operations with validation before publication."""
import json
import math
import os
from pathlib import Path
from .runtime import Artifact, ToolkitError, input_file, positive, target_bitrate
from .subtitles import parse_subtitles, clean_text


def summary(info):
    duration = float(info.get('format', {}).get('duration', 0))
    video = next((s for s in info['streams'] if s.get('codec_type') == 'video'), {})
    return dict(duration=duration, width=video.get('width'), height=video.get('height'),
                codecs=[s.get('codec_name') for s in info['streams']])


def require_video(info):
    if not any(s.get('codec_type') == 'video' for s in info['streams']):
        raise ToolkitError('Input requires a video stream', 'video_missing')


def receipt(runner, command, source, requested, actual, validated):
    return dict(command=command, source=str(source), requested=requested, actual=actual,
                validated=validated, events=list(runner.events))


def subtitles(runner, source, output):
    source = input_file(source)
    cues = parse_subtitles(source.read_text(encoding='utf-8-sig'))
    document = dict(text=clean_text(cues), cues=cues, source=str(source))
    with Artifact(output, source) as artifact:
        artifact.path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf-8')
        return artifact.publish(receipt(runner, 'subtitles', source, {}, dict(cues=len(cues)), dict(parsed=True)))


def compress(runner, source, output, *, target_mb=None, crf=23, encoder='cpu', audio_kbps=96, codec='h264', hw_device='/dev/dri/renderD128'):
    source = input_file(source); info = runner.probe(source); require_video(info)
    if not 0 <= crf <= 51:
        raise ToolkitError('CRF must be between 0 and 51', 'invalid_argument')
    audio = any(s.get('codec_type') == 'audio' for s in info['streams'])
    positive(audio_kbps, 'audio-kbps')
    limit = int(positive(target_mb, 'target-mb') * 1_000_000) if target_mb is not None else None
    if limit is not None and (encoder != 'cpu' or codec != 'h264'):
        raise ToolkitError('Target-size mode requires CPU two-pass H264', 'invalid_argument')
    bitrate = target_bitrate(limit, summary(info)['duration'], audio_kbps*1000 if audio else 0) if limit is not None else None
    chosen = 'libx264'; fallback = False
    with Artifact(output, source) as artifact:
        audio_args = ['-c:a', 'aac', '-b:a', f'{audio_kbps}k'] if audio else ['-an']
        base = ['-i', source, '-map', '0:v:0', '-map', '0:a:0?', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-pix_fmt', 'yuv420p']
        if limit is None:
            from .encoding import encode
            chosen, fallback, attempts = encode(runner, source, artifact.path, audio_args,
                                                 encoder=encoder, codec=codec, crf=crf, hw_device=hw_device)
        else:
            for attempts in range(1, 4):
                log = artifact.directory/'passlog'
                video_args = ['-c:v','libx264','-b:v',str(bitrate),'-passlogfile',log]
                runner.ffmpeg([*base, *video_args, '-pass','1','-an','-f','null',os.devnull])
                runner.ffmpeg([*base, *video_args, '-pass','2',*audio_args,artifact.path])
                size = artifact.path.stat().st_size
                if size <= limit:
                    break
                new_rate = int(bitrate * limit / size * 0.90)
                if new_rate < 64_000:
                    raise ToolkitError('Output cannot meet budget at minimum video bitrate', 'budget_unreachable')
                bitrate = new_rate
            else:
                raise ToolkitError('Output still exceeds budget after 3 attempts', 'budget_exceeded')
        verified = runner.validate_media(artifact.path, video=True, audio=audio, max_bytes=limit)
        actual = summary(verified); actual.update(encoder=chosen, fallback=fallback, attempts=attempts)
        return artifact.publish(receipt(runner,'compress',source,dict(max_bytes=limit,encoder=encoder,codec=codec),actual,dict(decodable=True,budget_met=limit is None or artifact.path.stat().st_size<=limit)))


def gif(runner, source, output, *, fps=15, width=1080, max_mb=5):
    source=input_file(source); require_video(runner.probe(source))
    positive(fps,'fps'); positive(width,'width'); limit=int(positive(max_mb,'max-mb')*1_000_000)
    with Artifact(output,source) as artifact:
        # Bounded adaptation, always preserving the input aspect ratio.
        settings=[]
        for factor, cap in [(1, fps),(.75,min(fps,12)),(.5,min(fps,10)),(.3,min(fps,8)),(.2,min(fps,6))]:
            settings.append((max(32,int(width*factor)),cap))
        for attempts,(used_width,used_fps) in enumerate(settings,1):
            palette=artifact.directory/'palette.png'
            filters=f'fps={used_fps},scale={used_width}:-1:flags=lanczos'
            runner.ffmpeg(['-i',source,'-vf',filters+',palettegen=stats_mode=diff','-frames:v','1',palette])
            runner.ffmpeg(['-i',source,'-i',palette,'-filter_complex',filters+'[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle','-an',artifact.path])
            if artifact.path.stat().st_size<=limit:
                break
        else:
            raise ToolkitError('GIF exceeds byte limit after 5 attempts; reduce duration or relax limit','budget_exceeded')
        info=runner.validate_media(artifact.path,video=True,max_bytes=limit)
        actual=summary(info); actual.update(fps=used_fps,attempts=attempts)
        return artifact.publish(receipt(runner,'gif',source,dict(max_bytes=limit,width=width,fps=fps),actual,dict(decodable=True,budget_met=True)))


def audio(runner, source, output, *, format='mp3', copy=False):
    source=input_file(source); info=runner.probe(source)
    if not any(s.get('codec_type')=='audio' for s in info['streams']):
        raise ToolkitError('Input has no audio stream','audio_missing')
    stream=next(s for s in info['streams'] if s.get('codec_type')=='audio')
    if copy and (format!='m4a' or stream.get('codec_name') not in ('aac','alac')):
        raise ToolkitError('M4A stream copy requires AAC or ALAC input; use encoding otherwise','lossless_unavailable')
    with Artifact(output,source) as artifact:
        args=['-c:a','copy'] if copy else (['-c:a','aac','-b:a','192k'] if format=='m4a' else ['-c:a','libmp3lame','-q:a','2'])
        runner.ffmpeg(['-i',source,'-map','0:a:0','-vn',*args,artifact.path])
        verified=runner.validate_media(artifact.path,audio=True)
        identity=False
        if copy:
            def packets(path):
                data=json.loads(runner.run('ffprobe',['-v','error','-select_streams','a:0','-show_packets','-show_data_hash','sha256','-show_entries','packet=data_hash','-of','json',path]))
                return [p.get('data_hash') for p in data.get('packets',[])]
            before=packets(source); after=packets(artifact.path)
            identity=bool(before) and all(before) and before==after
            if not identity: raise ToolkitError('Copied audio packet hashes differ','lossless_unavailable')
        actual=summary(verified); actual['reencoded']=not copy
        return artifact.publish(receipt(runner,'audio',source,dict(format=format,lossless=copy),actual,dict(decodable=True,packet_identity=identity)))


def trim(runner, source, output, *, start, end, mode='accurate'):
    source=input_file(source); info=runner.probe(source); require_video(info)
    duration=summary(info)['duration']
    if not math.isfinite(start) or start<0 or not math.isfinite(end) or end<=start or end>duration:
        raise ToolkitError('Require 0 <= start < end <= input duration','invalid_argument')
    target=end-start; tolerance=.15
    with Artifact(output,source) as artifact:
        args=['-ss',str(start),'-i',source,'-t',str(target),'-map','0:v:0','-map','0:a:0?']
        args+=['-c','copy'] if mode=='fast' else ['-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac']
        runner.ffmpeg([*args,artifact.path])
        verified=runner.validate_media(artifact.path,video=True)
        actual=summary(verified); actual['duration_error_seconds']=abs(actual['duration']-target)
        if mode=='accurate' and actual['duration_error_seconds']>tolerance:
            raise ToolkitError('Trimmed duration exceeds declared tolerance','trim_precision')
        return artifact.publish(receipt(runner,'trim',source,dict(start=start,end=end,mode=mode,exact_boundaries=False,reencoded=mode=='accurate',tolerance_seconds=tolerance),actual,dict(decodable=True,duration_met=actual['duration_error_seconds']<=tolerance)))


def image_info(runner, source):
    output=runner.run('magick',['identify','-format','%w %h %z\n%[EXIF:*]\n%[profiles]',str(source)+'[0]'])
    first,*rest=output.splitlines()
    w,h,depth=map(int,first.split())
    return dict(width=w,height=h,depth=depth,metadata='\n'.join(rest))


def image(runner, source, output, *, max_side=1920, quality=82, lossless=False):
    source=input_file(source); positive(max_side,'max-side')
    if not 0<=quality<=100:
        raise ToolkitError('Quality must be between 0 and 100','invalid_argument')
    before=image_info(runner,source)
    if lossless and (before['depth']>8 or max(before['width'],before['height'])>max_side):
        raise ToolkitError('Pixel-preserving WebP requires <=8-bit input and no resizing','lossless_unavailable')
    with Artifact(output,source) as artifact:
        args=[str(source)+'[0]','-auto-orient','-resize',f'{max_side}x{max_side}>','-strip']
        args+=['-define','webp:lossless=true'] if lossless else ['-quality',str(quality)]
        runner.run('magick',[*args,artifact.path])
        actual=image_info(runner,artifact.path)
        if max(actual['width'],actual['height'])>max_side or actual['metadata'].strip():
            raise ToolkitError('Image dimensions or stripped metadata failed verification')
        runner.run('magick',[artifact.path,'null:'])
        if lossless:
            try:
                runner.run('magick',['compare','-metric','AE',str(source)+'[0]',artifact.path,'null:'])
            except ToolkitError:
                raise ToolkitError('Output pixels differ; lossless requirement was not met','lossless_unavailable') from None
        actual.pop('metadata')
        return artifact.publish(receipt(runner,'image',source,dict(max_side=max_side,lossless=lossless,frame='primary'),actual,dict(decodable=True,privacy_scrubbed=True,pixel_identity=lossless)))
