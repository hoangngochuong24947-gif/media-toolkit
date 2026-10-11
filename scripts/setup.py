"""Validate or install this skill without system PATH/dependency modifications."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--check',action='store_true')
    p.add_argument('--install-to')
    p.add_argument('--backup-dir')
    args=p.parse_args()
    archive=None
    manifest=ROOT/'MANIFEST.json'
    if manifest.exists():
        files=json.loads(manifest.read_text(encoding='utf-8'))
        if 'files' in files: files=files['files']
        if isinstance(files,list):files={f['path']:f['sha256'] for f in files}
        for relative,checksum in files.items():
            path=(ROOT/relative).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=checksum:
                raise ValueError(f'Package integrity check failed: {relative}')
    result=subprocess.run([sys.executable,str(ROOT/'scripts/media.py'),'doctor'],capture_output=True,text=True,encoding='utf-8',timeout=60)
    check=json.loads(result.stdout)
    if result.returncode or not check['ok']:
        print(json.dumps({'ok':False,'doctor':check},ensure_ascii=False));return 1
    from media_toolkit.runtime import Runner,ToolkitError
    runner=Runner(timeout=60)
    extras={}
    for name,arguments in [('node',['--version']),('asr-python',['-I','-c','import faster_whisper,ctranslate2,av,onnxruntime; print(faster_whisper.__version__)'])]:
        if name in runner.tool_paths:
            try:extras[name]={'available':True,'version':runner.run(name,arguments).strip()}
            except ToolkitError as exc:extras[name]={'available':False,'error':str(exc)}
    check['runtime_checks']=extras
    if any(not item['available'] for item in extras.values()) or ('yt-dlp' in runner.tool_paths and not check['tools']['yt-dlp']['available']):
        print(json.dumps({'ok':False,'doctor':check},ensure_ascii=False));return 1
    if args.install_to:
        target=Path(args.install_to).expanduser().resolve()
        if target==ROOT or target.is_relative_to(ROOT) or ROOT.is_relative_to(target):raise ValueError('Install target must be separate from package')
        if target.exists():
            if not args.backup_dir:raise ValueError('Existing installation requires --backup-dir DIR')
            backup=Path(args.backup_dir).resolve()
            if backup==target or backup.is_relative_to(target):raise ValueError('Backup directory must be outside installation')
            backup.mkdir(parents=True,exist_ok=True)
            archive=backup/f'media-toolkit-before-{datetime.now().strftime("%Y%m%d%H%M%S%f")}.zip'
            with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
                for path in target.rglob('*'):
                    if path.is_file() and '__pycache__' not in path.parts:z.write(path,path.relative_to(target))
            # Preserve client-local executable profile; install only declared files.
        target.mkdir(parents=True,exist_ok=True)
        paths=list(files) if manifest.exists() else [str(path.relative_to(ROOT)) for base in ('scripts','references') for path in (ROOT/base).rglob('*') if path.is_file() and '__pycache__' not in path.parts]+['SKILL.md','README.md','LICENSE']
        for relative in paths:
            if relative=='tool-paths.local.json' or Path(relative).parts[0]=='runtime':continue
            destination=target/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/relative,destination)
        # Portable package profile is adjusted to absolute package paths when
        # installing its lightweight skill; full runtime remains with the package.
        if (ROOT/'tool-paths.local.json').exists():
            profile=json.loads((ROOT/'tool-paths.local.json').read_text(encoding='utf-8'))
            profile={key:str((ROOT/value).resolve()) if not Path(value).is_absolute() and (ROOT/value).is_file() else value for key,value in profile.items()}
            (target/'tool-paths.local.json').write_text(json.dumps(profile,indent=2),encoding='utf-8')
            interpreter=profile.get('asr-python')
            if interpreter and Path(interpreter).is_file():
                (target/'runtime-path.cmd').write_text('@for /f "tokens=2 delims=:" %%p in (\'chcp\') do @set "taskOldPage=%%p"\n@chcp 65001 >nul\n@set "taskRuntime='+interpreter.replace('%','%%')+'"\n@chcp %taskOldPage% >nul\n',encoding='utf-8')
        # The installed copy has different paths and excludes the full runtime;
        # never retain an older package manifest or one claiming absent binaries.
        installed_files=[relative for relative in paths if relative!='tool-paths.local.json' and Path(relative).parts[0]!='runtime']
        installed_files += [name for name in ('tool-paths.local.json','runtime-path.cmd') if (target/name).is_file()]
        installed_manifest={'version':check['version'],'package':str(ROOT),'files':{relative:hashlib.sha256((target/relative).read_bytes()).hexdigest() for relative in installed_files}}
        (target/'MANIFEST.json').write_text(json.dumps(installed_manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'ok':True,'installed':str(target),'backup':str(archive) if archive else None,'doctor':check},ensure_ascii=False))
    else:print(json.dumps({'ok':True,'doctor':check},ensure_ascii=False))
    return 0


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    try:sys.exit(main())
    except (ValueError,OSError,subprocess.TimeoutExpired) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False));sys.exit(1)
