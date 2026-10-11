"""Tool discovery, bounded subprocesses and verified artifact publication."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time


class ToolkitError(Exception):
    def __init__(self, message, code='validation_failed'):
        super().__init__(message)
        self.code = code


def target_bitrate(limit_bytes, duration, audio_bps=96_000):
    if not math.isfinite(duration) or duration <= 0 or limit_bytes <= 0:
        raise ToolkitError('Budget and duration must be finite and positive', 'invalid_argument')
    video = int(limit_bytes * 8 * 0.90 / duration) - audio_bps
    if video < 64_000:
        raise ToolkitError('Target cannot fit minimum video/audio bitrates; reduce duration or audio rate', 'budget_unreachable')
    return video


def classify_network_error(message):
    text = message.lower()
    if '429' in text or 'too many requests' in text:
        return 'rate_limit'
    if any(s in text for s in ['403', '401', 'sign in', 'login required', 'private video']):
        return 'access_denied'
    if any(s in text for s in ['ssl', 'tls', 'timeout', 'timed out', 'connection', 'unable to download']):
        return 'network'
    if 'format' in text:
        return 'formats'
    return 'download_failed'


def positive(value, label):
    if not math.isfinite(value) or value <= 0:
        raise ToolkitError(f'{label} must be finite and positive', 'invalid_argument')
    return value


def input_file(value):
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ToolkitError(f'Input file not found: {path}', 'input_missing')
    return path


class Runner:
    def __init__(self, timeout=300, tool_config=None, progress_dir=None):
        self.timeout = positive(timeout, 'timeout')
        self.events = []
        self.progress_dir=Path(progress_dir).expanduser().resolve() if progress_dir else None
        if self.progress_dir: self.progress_dir.mkdir(parents=True,exist_ok=True)
        config = Path(tool_config) if tool_config else Path(__file__).resolve().parents[2]/'tool-paths.local.json'
        self.tool_paths = {}
        self.config_directory=config.resolve().parent
        if config.exists():
            try:
                self.tool_paths = json.loads(config.read_text(encoding='utf-8-sig'))
                if not isinstance(self.tool_paths,dict) or any(not isinstance(v,str) for v in self.tool_paths.values()):
                    raise ValueError('Tool profile must map names to executable paths')
            except (ValueError,OSError) as exc:
                raise ToolkitError(f'Invalid tool profile: {exc}', 'configuration_invalid') from None

    def tool(self, name):
        override = os.environ.get('MEDIA_' + name.upper().replace('-', '_'))
        configured=self.tool_paths.get(name)
        if configured and not Path(configured).is_absolute() and (self.config_directory/configured).is_file():
            configured=str((self.config_directory/configured).resolve())
        path = shutil.which(override or configured or (sys.executable if name == 'asr-python' else name))
        if not path:
            raise ToolkitError(f'Missing executable {name}; set MEDIA_{name.upper().replace("-", "_")}', 'dependency_missing')
        return path

    def progress(self, name, status, **values):
        if self.progress_dir:
            event=dict(tool=name,status=status,utc=time.time(),**values)
            with (self.progress_dir/'events.jsonl').open('a',encoding='utf-8') as stream:
                stream.write(json.dumps(event,ensure_ascii=False)+'\n');stream.flush()
            # Snapshot is atomically replaced for UI/agent polling.
            from .collection import write_json
            write_json(self.progress_dir/'current.json',event)

    def run(self, name, args, cwd=None):
        command = [self.tool(name), *map(str, args)]
        start = time.monotonic()
        self.progress(name,'running')
        # Spool logs to disk to bound memory for long media/network operations.
        with tempfile.TemporaryDirectory(prefix='media-logs-') as logs, \
                open(Path(logs)/'stdout','w+b') as stdout, \
                open(Path(logs)/'stderr','w+b') as stderr, \
                open(Path(logs)/'stdout','rb') as reader:
            try:
                process = subprocess.Popen(command, cwd=cwd, stdout=stdout, stderr=stderr,
                                           creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
                                           start_new_session=os.name != 'nt')
                try:
                    cursor=0; pending=b''; heartbeat=start
                    while process.poll() is None:
                        if time.monotonic()-start >= self.timeout:
                            raise subprocess.TimeoutExpired(command,self.timeout)
                        if self.progress_dir:
                            size=os.fstat(stdout.fileno()).st_size
                            if size>cursor:
                                reader.seek(cursor); pending+=reader.read(size-cursor); cursor=size
                                lines=pending.split(b'\n'); pending=lines.pop()
                                for line in lines:
                                    if line.startswith(b'MTK_PROGRESS:'):
                                        try:
                                            data=json.loads(line[len(b'MTK_PROGRESS:'):])
                                            fields={key:data[key] for key in ('status','downloaded_bytes','total_bytes','total_bytes_estimate','speed','eta','fragment_index','fragment_count') if key in data}
                                            self.progress(name,'running',progress=fields)
                                        except (ValueError,TypeError): pass
                            if time.monotonic()-heartbeat >= 5:
                                self.progress(name,'running',elapsed=round(time.monotonic()-start,1));heartbeat=time.monotonic()
                        time.sleep(min(0.1,self.timeout))
                except subprocess.TimeoutExpired:
                    # yt-dlp can spawn ffmpeg; stop the whole operation, not
                    # only the parent while a child keeps writing staged files.
                    if os.name == 'nt':
                        try:
                            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL,timeout=10,check=False)
                        except (OSError,subprocess.TimeoutExpired):
                            process.kill()
                    else:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    process.wait(timeout=10)
                    raise
            except (subprocess.TimeoutExpired,KeyboardInterrupt) as exc:
                if isinstance(exc,KeyboardInterrupt) and 'process' in locals() and process.poll() is None:
                    if os.name=='nt':
                        try:subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,check=False)
                        except (OSError,subprocess.TimeoutExpired):process.kill()
                    else: os.killpg(process.pid,signal.SIGKILL)
                    process.wait(timeout=10)
                if isinstance(exc,KeyboardInterrupt):
                    self.progress(name,'cancelled'); raise ToolkitError('Operation cancelled; resumable downloads retained','cancelled') from None
                self.progress(name,'timeout',elapsed=round(time.monotonic()-start,3))
                self.events.append(dict(tool=name, status='timeout', seconds=round(time.monotonic()-start, 3)))
                raise ToolkitError(f'{name} exceeded {self.timeout:g}s', 'timeout') from None
            except OSError as exc:
                # Progress/log IO errors must not leave a writer behind.
                if 'process' in locals() and process.poll() is None:
                    if os.name=='nt':
                        try:subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,check=False)
                        except (OSError,subprocess.TimeoutExpired):process.kill()
                    else:os.killpg(process.pid,signal.SIGKILL)
                    process.wait(timeout=10)
                raise ToolkitError(f'Cannot execute {name}: {exc}', 'dependency_failed') from None
            def tail(stream):
                size = stream.tell(); stream.seek(max(0, size - 65536))
                return stream.read().decode('utf-8', errors='replace')
            error = tail(stderr)
            if stdout.tell() > 16 * 1024 * 1024:
                raise ToolkitError('Structured tool output exceeds 16 MiB; reduce the batch size', 'output_too_large')
            stdout.seek(0)
            output = stdout.read().decode('utf-8', errors='replace')
        self.events.append(dict(tool=name, returncode=process.returncode, seconds=round(time.monotonic()-start, 3)))
        self.progress(name,'success' if process.returncode==0 else 'failed',returncode=process.returncode,elapsed=round(time.monotonic()-start,3))
        if process.returncode:
            code = classify_network_error(error) if name == 'yt-dlp' else 'process_failed'
            raise ToolkitError(f'{name} failed: {error[-3000:]}', code)
        return output

    def ffmpeg(self, args):
        return self.run('ffmpeg', ['-nostdin', '-y', '-v', 'error', *args])

    def probe(self, path):
        try:
            info = json.loads(self.run('ffprobe', ['-v', 'error', '-show_format', '-show_streams', '-of', 'json', path]))
        except (ValueError, TypeError):
            raise ToolkitError('ffprobe did not return valid JSON', 'probe_failed') from None
        if not info.get('streams'):
            raise ToolkitError('Media contains no streams', 'probe_failed')
        return info

    def validate_media(self, path, *, video=False, audio=False, max_bytes=None):
        if not path.is_file() or not path.stat().st_size:
            raise ToolkitError('No nonempty output produced')
        info = self.probe(path)
        kinds = {s.get('codec_type') for s in info['streams']}
        if video and 'video' not in kinds or audio and 'audio' not in kinds:
            raise ToolkitError('Required video/audio stream is missing')
        self.ffmpeg(['-i', path, '-map', '0:v?', '-map', '0:a?', '-f', 'null', os.devnull])
        if max_bytes is not None and path.stat().st_size > max_bytes:
            raise ToolkitError(f'Output is {path.stat().st_size}B, exceeds {max_bytes}B', 'budget_exceeded')
        return info


class Artifact:
    """Stage in the output filesystem; publish only after validation.

    Existing files are always refused. Hard-link publication makes this policy
    race-safe instead of checking then overwriting. Requires a filesystem that
    supports hard links (NTFS, APFS and typical Linux filesystems).
    """
    def __init__(self, output, source=None):
        self.output = Path(output).expanduser().resolve()
        self.receipt = Path(str(self.output) + '.result.json')
        if source and self.output == Path(source).resolve():
            raise ToolkitError('Output must differ from input', 'source_protection')
        if self.output.exists() or self.receipt.exists():
            raise ToolkitError(f'Output or receipt already exists: {self.output}', 'output_exists')

    def __enter__(self):
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='.media-toolkit-', dir=self.output.parent)
        self.directory = Path(self.temp.name)
        self.path = self.directory / self.output.name
        return self

    def publish(self, details):
        digest = hashlib.file_digest if hasattr(hashlib, 'file_digest') else None
        with self.path.open('rb') as file:
            if digest:
                checksum = digest(file, 'sha256').hexdigest()
            else:
                h = hashlib.sha256()
                for block in iter(lambda: file.read(1024*1024), b''):
                    h.update(block)
                checksum = h.hexdigest()
        result = dict(ok=True, output=str(self.output), bytes=self.path.stat().st_size, sha256=checksum, **details)
        receipt_tmp = self.directory / 'receipt.json'
        receipt_tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        linked = False
        try:
            os.link(self.path, self.output)
            linked = True
            os.link(receipt_tmp, self.receipt)
        except OSError as exc:
            if linked:
                self.output.unlink()
            raise ToolkitError(f'Cannot publish without overwriting: {exc}', 'publish_failed') from None
        return result

    def __exit__(self, *args):
        self.temp.cleanup()
