"""Optional ASR in a separate interpreter, with explicit model-download control."""
import hashlib
import json
import math
from pathlib import Path

from .runtime import Artifact, ToolkitError, input_file


def transcribe(runner, source, output, *, model='small', language=None, hotwords='',
               cache_dir=None, allow_model_download=False, device='cpu', compute_type='int8'):
    source = input_file(source)
    if not cache_dir or len(hotwords) > 4000:
        raise ToolkitError('ASR requires an explicit model cache directory; hotwords max 4000 chars', 'invalid_argument')
    cache = Path(cache_dir).expanduser().resolve()
    cache.mkdir(parents=True, exist_ok=True)
    with Artifact(output, source) as artifact:
        request = dict(input=str(source), output=str(artifact.path), model=model, language=language,
                       hotwords=hotwords, cache_dir=str(cache), allow_model_download=allow_model_download,
                       device=device, compute_type=compute_type)
        config = artifact.directory/'request.json'
        config.write_text(json.dumps(request), encoding='utf-8')
        worker = Path(__file__).with_name('asr_worker.py')
        try:
            status = json.loads(runner.run('asr-python', [worker, config]))
        except ValueError:
            raise ToolkitError('ASR worker returned invalid JSON', 'asr_failed') from None
        if not status.get('ok'):
            raise ToolkitError(status.get('message','ASR failed'), status.get('code','asr_failed'))
        document = json.loads(artifact.path.read_text(encoding='utf-8'))
        cues = document.get('cues') or []
        if not cues or any(not math.isfinite(c['start']) or not math.isfinite(c['end']) or c['end'] <= c['start'] for c in cues):
            raise ToolkitError('ASR returned no valid speech segments', 'asr_empty')
        with source.open('rb') as stream:
            h = hashlib.sha256()
            for block in iter(lambda: stream.read(1024*1024), b''):
                h.update(block)
        document['source'] = str(source)
        document['source_sha256'] = h.hexdigest()
        artifact.path.write_text(json.dumps(document,ensure_ascii=False,indent=2),encoding='utf-8')
        return artifact.publish(dict(command='transcribe', source=str(source),
                                     actual=dict(segments=len(cues),language=document['language']),
                                     validated=dict(parsed=True,accuracy_certified=False),events=runner.events))
