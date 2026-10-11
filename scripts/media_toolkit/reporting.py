"""Publish host-authored notes only with traceable transcript evidence."""
import hashlib
import json
import math
import re
from pathlib import Path
from .runtime import Artifact, ToolkitError, input_file


def report(runner, source, output):
    source=input_file(source); data=json.loads(source.read_text(encoding='utf-8-sig'))
    if not isinstance(data,dict) or not isinstance(data.get('claims'),list) or not data['claims']:
        raise ToolkitError('Report requires nonempty authored claims','evidence_invalid')
    title=data.get('title')
    if not isinstance(title,str) or not title.strip(): raise ToolkitError('Report title required','evidence_invalid')
    lines=[f'# {title}', '', '本报告由宿主代理撰写；程序验证引文、时间锚点与数字支持，不认证语义正确性或科学结论。', '', '## 来源与处理范围', '',str(data.get('coverage','仅涵盖下列实际读取的字幕；不代表平台全部相关视频。')), '', '## 论点与证据', '']
    evidence=[]; cache={}
    for index,claim in enumerate(data['claims'],1):
        if not isinstance(claim,dict): raise ToolkitError('Each claim must be an object','evidence_invalid')
        path=Path(claim.get('transcript',''))
        if not path.is_absolute(): path=source.parent/path
        path=input_file(path)
        if path not in cache:
            raw=path.read_bytes(); document=json.loads(raw.decode('utf-8-sig'))
            if not isinstance(document,dict): raise ToolkitError('Transcript must be an object','evidence_invalid')
            cache[path]=(document,hashlib.sha256(raw).hexdigest())
        document,digest=cache[path]
        selected=document
        try:
            if 'subtitles' in document:
                subtitle=claim.get('subtitle',0)
                if type(subtitle)!=int or subtitle<0: raise ValueError()
                selected=document['subtitles'][subtitle]
            cue_index=claim['cue']
            if type(cue_index)!=int or cue_index<0: raise ValueError()
            cue=selected['cues'][cue_index]
            quote=claim['quote']; statement=claim['statement']; kind=claim.get('kind','speaker')
            start=float(cue['start']); end=float(cue['end'])
            if not math.isfinite(start) or not math.isfinite(end) or start<0 or end<=start: raise ValueError()
            if not isinstance(quote,str) or not quote.strip() or quote not in cue['text']: raise ValueError()
            if not isinstance(statement,str) or not statement.strip() or kind not in ('speaker','inference'): raise ValueError()
            if not set(re.findall(r'\d+(?:[.,]\d+)?',statement)) <= set(re.findall(r'\d+(?:[.,]\d+)?',quote)): raise ValueError()
        except (KeyError,IndexError,TypeError,ValueError):
            raise ToolkitError(f'Claim {index}: invalid cue, quote, time or unsupported numbers','evidence_invalid') from None
        url=document.get('source',str(path)); url=url if isinstance(url,str) else str(path)
        anchor=(url+('&' if '?' in url else '?')+'t='+str(int(start))) if url.startswith(('https://www.youtube.com/','https://youtu.be/')) else url
        label='演讲者陈述' if kind=='speaker' else '代理推论'
        lines += [f'### {index}. {label}', '', statement, '', '> '+quote.replace('\n','\n> '),'',f'来源：[{start:.3f}–{end:.3f} 秒]({anchor})；字幕类型：{selected.get("kind",document.get("kind","unknown"))}。','']
        evidence.append(dict(transcript=str(path),sha256=digest,cue=cue_index,start=start,end=end,quote=quote,statement=statement,kind=kind,source=url))
    lines+=['## 待核查与未处理项','',str(data.get('limitations','自动字幕或语音识别可能有错词；引文存在不等于论点得到外部证实。')),'']
    with Artifact(output,source) as artifact:
        artifact.path.write_text('\n'.join(lines),encoding='utf-8')
        return artifact.publish(dict(command='report',source=str(source),actual=dict(claims=len(evidence)),validated=dict(quote_match=True,numeric_support=True,semantic_accuracy_certified=False),evidence=evidence))
