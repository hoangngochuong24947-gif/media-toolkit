"""Batch images with per-item evidence, writer lock and verified resume."""
import hashlib
import json
from pathlib import Path
from .runtime import ToolkitError
from .collection import job, write_json, verified_artifact
from .operations import image


def images(runner, source, output, *, max_side=1920, quality=82, lossless=False, recursive=False, retry_failed=False):
    source=Path(source).expanduser().resolve(); output=Path(output).expanduser().resolve()
    if not source.is_dir(): raise ToolkitError('Input must be an image directory','input_missing')
    if output==source or source in output.parents or output in source.parents:
        raise ToolkitError('Image source and output directories must not overlap','source_protection')
    files=sorted(p for p in (source.rglob('*') if recursive else source.iterdir()) if p.is_file() and p.suffix.lower() in ('.heic','.heif','.png','.jpg','.jpeg','.webp','.tif','.tiff','.bmp'))
    if not files: raise ToolkitError('No supported image files','input_missing')
    names=[p.relative_to(source).with_suffix('.webp') for p in files]
    if len({str(n).casefold() for n in names})!=len(names): raise ToolkitError('Multiple inputs map to one WebP output','output_collision')
    settings=dict(max_side=max_side,quality=quality,lossless=lossless,recursive=recursive)
    with job(output) as root:
        state_path=root/'images-state.json'
        state=json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else dict(source=str(source),settings=settings,items={})
        if state.get('source')!=str(source) or state.get('settings')!=settings:
            raise ToolkitError('Resume source/settings differ; use a new output directory','job_mismatch')
        if not state_path.exists() and any(p.name!='.job.lock' for p in root.iterdir()):
            raise ToolkitError('New image batch requires an empty output directory','output_exists')
        processed=skipped=0; current=[]
        for path,name in zip(files,names):
            key=str(path.relative_to(source)); dest=root/name; old=state['items'].get(key,{})
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            try:
                if old.get('status')=='success':
                    if old.get('source_sha256')==digest and verified_artifact(dest,source=str(path),command='image'):
                        skipped+=1; current.append(old); continue
                    raise ToolkitError('Source/output changed; preserved existing files','artifact_changed')
                if old.get('status')=='failed' and not retry_failed:
                    current.append(old); continue
                receipt=image(runner,path,dest,max_side=max_side,quality=quality,lossless=lossless)
                item=dict(status='success',source_sha256=digest,output=str(dest),sha256=receipt['sha256'])
                processed+=1
            except ToolkitError as exc:
                item=dict(status='failed',source_sha256=digest,error=dict(code=exc.code,message=str(exc)))
            state['items'][key]=item; current.append(item); write_json(state_path,state)
        failed=sum(i['status']=='failed' for i in current)
        return dict(ok=failed==0,command='images',status='partial' if failed else 'success',processed=processed,skipped=skipped,failed=failed,total=len(files),state=str(state_path),items=state['items'])
