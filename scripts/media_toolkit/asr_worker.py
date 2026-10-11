"""Run with MEDIA_ASR_PYTHON; never installs packages or reads credentials."""
import importlib.metadata
import hashlib
import json
import sys
from pathlib import Path


def run(request):
    from faster_whisper import WhisperModel
    from faster_whisper.utils import download_model
    model_path = Path(request['model'])
    if not model_path.is_dir():
        model_path = Path(download_model(request['model'], cache_dir=request['cache_dir'],
                                        local_files_only=not request['allow_model_download']))
    model_files = {}
    for path in sorted(model_path.iterdir()):
        if path.is_file():
            checksum = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024*1024), b''):
                    checksum.update(block)
            model_files[path.name] = checksum.hexdigest()
    model = WhisperModel(str(model_path), device=request['device'], compute_type=request['compute_type'],
                         local_files_only=True,
                         cpu_threads=4)
    segments, info = model.transcribe(request['input'], language=request['language'],
                                     beam_size=5, vad_filter=True, word_timestamps=True,
                                     hotwords=request['hotwords'] or None, condition_on_previous_text=False)
    cues = []
    for segment in segments:
        if segment.text.strip():
            cues.append(dict(start=segment.start,end=segment.end,text=segment.text.strip(),
                             avg_logprob=segment.avg_logprob,no_speech_prob=segment.no_speech_prob,
                             words=[dict(start=w.start,end=w.end,text=w.word,probability=w.probability) for w in (segment.words or [])]))
    document = dict(kind='local_asr', language=info.language, language_probability=info.language_probability,
                    duration=info.duration, cues=cues, text='\n'.join(c['text'] for c in cues)+'\n',
                    model=request['model'], model_files_sha256=model_files, hotwords=request['hotwords'],
                    runtime={name:importlib.metadata.version(name) for name in ('faster-whisper','ctranslate2','av')},
                    quality=dict(accuracy_certified=False,warnings=['ASR output can contain omissions or hallucinations; numeric and technical claims need verification']))
    Path(request['output']).write_text(json.dumps(document,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__ == '__main__':
    try:
        run(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
        print(json.dumps(dict(ok=True)))
    except ImportError as exc:
        print(json.dumps(dict(ok=False,code='asr_dependency_missing',message=str(exc))))
    except Exception as exc:
        print(json.dumps(dict(ok=False,code='asr_failed',message=str(exc))))
