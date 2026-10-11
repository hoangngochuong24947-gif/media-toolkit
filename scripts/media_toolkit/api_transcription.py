"""Opt-in, bounded multipart ASR integration; credentials never enter receipts."""
import hashlib
import json
import math
import mimetypes
import os
import uuid
import urllib.error
import urllib.parse
import urllib.request
from .runtime import Artifact, ToolkitError, input_file


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


def transcribe_api(runner, source, output, *, endpoint, model='whisper-1', language=None, allow_network=False):
    if not allow_network: raise ToolkitError('Audio transfer requires --allow-network','network_not_authorized')
    parsed=urllib.parse.urlsplit(endpoint)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.hostname:
        raise ToolkitError('Endpoint must not embed credentials, query or fragment','invalid_argument')
    if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost','::1')):
        raise ToolkitError('Use HTTPS or a loopback HTTP endpoint','invalid_argument')
    key=os.environ.get('MEDIA_ASR_API_KEY','')
    if any(ord(c)<=32 or ord(c)>=127 for c in key):
        raise ToolkitError('Invalid API credential characters','configuration_invalid')
    if parsed.hostname not in ('127.0.0.1','localhost','::1') and not key:
        raise ToolkitError('Remote endpoint requires MEDIA_ASR_API_KEY','configuration_invalid')
    source=input_file(source)
    if not 0<source.stat().st_size<=25_000_000: raise ToolkitError('API input must be nonempty and <=25 MB','invalid_argument')
    boundary='media'+uuid.uuid4().hex; parts=[]
    fields={'model':model,'response_format':'verbose_json'}
    if language: fields['language']=language
    for name,value in fields.items():
        if not isinstance(value,str) or len(value)>200: raise ToolkitError('Invalid API field','invalid_argument')
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    raw=source.read_bytes(); mime=mimetypes.guess_type(source.name)[0] or 'application/octet-stream'
    # Fixed basename avoids injecting untrusted filenames into multipart headers.
    suffix=source.suffix.lower() if source.suffix.lower() in ('.wav','.mp3','.m4a','.mp4','.ogg','.flac','.webm') else '.bin'
    parts += [f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio{suffix}"\r\nContent-Type: {mime}\r\n\r\n'.encode(),raw,f'\r\n--{boundary}--\r\n'.encode()]
    headers={'Content-Type':f'multipart/form-data; boundary={boundary}'}
    if key: headers['Authorization']='Bearer '+key
    with Artifact(output,source) as artifact:
        request=urllib.request.Request(endpoint,data=b''.join(parts),headers=headers,method='POST')
        try:
            with urllib.request.build_opener(NoRedirect).open(request,timeout=runner.timeout) as response:
                result=response.read(16*1024*1024+1)
        except urllib.error.HTTPError as exc:
            code='rate_limit' if exc.code==429 else 'access_denied' if exc.code in (401,403) else 'api_failed'
            raise ToolkitError(f'ASR endpoint returned HTTP {exc.code}',code) from None
        except (urllib.error.URLError,TimeoutError,OSError):
            raise ToolkitError('ASR endpoint connection failed','network') from None
        if len(result)>16*1024*1024: raise ToolkitError('API output exceeds 16 MiB','output_too_large')
        try:
            document=json.loads(result); cues=[]
            for segment in document.get('segments') or []:
                start=float(segment['start']); end=float(segment['end']); text=segment['text']
                if not math.isfinite(start) or not math.isfinite(end) or start<0 or end<=start or not isinstance(text,str) or not text.strip(): raise ValueError()
                cues.append(dict(start=start,end=end,text=text))
            if not cues: raise ValueError()
        except (ValueError,TypeError,KeyError,AttributeError):
            raise ToolkitError('ASR API requires valid timed segments','asr_empty') from None
        artifact.path.write_text(json.dumps(dict(source=str(source),source_sha256=hashlib.sha256(raw).hexdigest(),kind='api_asr',language=document.get('language'),cues=cues,raw=document),ensure_ascii=False,indent=2),encoding='utf-8')
        return artifact.publish(dict(command='transcribe-api',source=str(source),actual=dict(segments=len(cues),model=model,endpoint=endpoint),validated=dict(parsed=True,accuracy_certified=False)))
