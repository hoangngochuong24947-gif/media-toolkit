#!/usr/bin/env python3
"""Optional stdlib helpers. Agents can ignore this and call ffmpeg or yt-dlp.

Subtitle parsing, bounded process runs, no-overwrite publication, and sha256
receipts are adapted from cowboy596's media-toolkit contribution (MIT).
The project/collection workflow is intentionally not included.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path


class ToolkitError(Exception):
    def __init__(self, message: str, code: str = "validation_failed") -> None:
        super().__init__(message)
        self.code = code


TIMESTAMP = r"(?:\d+:)?\d{2}:\d{2}[.,]\d{3}"
CUE = re.compile(rf"^({TIMESTAMP})\s+-->\s+({TIMESTAMP})(?:\s+.*)?$")


def seconds(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    numbers = [float(part) for part in parts]
    if len(numbers) == 3:
        hours, minutes, sec = numbers
    elif len(numbers) == 2:
        hours = 0.0
        minutes, sec = numbers
    else:
        raise ToolkitError("Invalid subtitle timestamp", "subtitle_invalid")
    if minutes >= 60 or sec >= 60:
        raise ToolkitError("Invalid subtitle timestamp", "subtitle_invalid")
    return hours * 3600 + minutes * 60 + sec


def parse_subtitles(text: str) -> list[dict]:
    """Parse SRT/VTT cues. Dialogue that starts with a digit is kept."""
    cues = []
    normalized = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").strip()
    for block in re.split(r"\n\s*\n", normalized):
        lines = block.splitlines()
        if not lines or re.match(r"^(NOTE(?:\s|$)|STYLE$|REGION$)", lines[0]):
            continue
        found = None
        for index, line in enumerate(lines):
            match = CUE.match(line.strip())
            if match:
                found = (index, match)
                break
        if found is None:
            if any("-->" in line for line in lines):
                raise ToolkitError("Malformed subtitle cue", "subtitle_invalid")
            continue
        index, match = found
        start, end = seconds(match.group(1)), seconds(match.group(2))
        if end <= start:
            raise ToolkitError("Subtitle end must follow start", "subtitle_invalid")
        body = "\n".join(lines[index + 1 :])
        body = html.unescape(re.sub(r"<[^>]*>", "", body))
        body = "\n".join(line.strip() for line in body.splitlines() if line.strip())
        if body:
            cues.append({"start": start, "end": end, "text": body})
    if not cues:
        raise ToolkitError("No valid subtitle cues found", "subtitle_empty")
    return cues


def clean_text(cues: list[dict]) -> str:
    """Drop overlapping rolling-caption repeats. Keep real repeated lines."""
    output: list[str] = []
    previous = None
    for cue in cues:
        lines = cue["text"].splitlines()
        touching_roll = False
        if previous is not None and abs(cue["start"] - previous["end"]) <= 0.001:
            previous_lines = previous["text"].splitlines()
            short_previous = previous["end"] - previous["start"] <= 0.05
            short_current = cue["end"] - cue["start"] <= 0.05
            touching_roll = (
                len(previous_lines) > 1 or len(lines) > 1 or short_previous or short_current
            )
        overlaps_previous = previous is not None and (
            cue["start"] < previous["end"] or touching_roll
        )
        if overlaps_previous and previous is not None:
            old = previous["text"].splitlines()
            for overlap in range(min(len(old), len(lines)), 0, -1):
                if old[-overlap:] == lines[:overlap]:
                    lines = lines[overlap:]
                    break
        output.extend(lines)
        previous = cue
    return "\n".join(output) + "\n"


def run_bounded(args: list[str], timeout: float, cwd: str | None = None) -> str:
    """Run a command without a shell. Kill the process group on timeout."""
    if timeout <= 0:
        raise ToolkitError("timeout must be positive", "invalid_argument")
    try:
        process = subprocess.Popen(
            args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        raise ToolkitError(f"Cannot execute {args[0]}: {exc}", "dependency_missing") from exc
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        raise ToolkitError(f"{args[0]} exceeded {timeout:g}s", "timeout") from None
    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace")[-3000:]
        raise ToolkitError(f"{args[0]} failed: {detail}", "process_failed")
    return stdout.decode("utf-8", errors="replace")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _link_new(source: Path, dest: Path) -> None:
    try:
        os.link(source, dest)
    except OSError as exc:
        raise ToolkitError(f"Cannot publish without overwriting: {exc}", "publish_failed") from exc


def publish_file(staged: Path, output: Path, details: dict) -> dict:
    """Hard-link staged onto output and write a sha256 receipt. Never overwrites."""
    output = Path(output).expanduser().resolve()
    staged = Path(staged).resolve()
    receipt = Path(str(output) + ".result.json")
    if output == staged:
        raise ToolkitError("Output must differ from the staged file", "source_protection")
    if output.exists() or receipt.exists():
        raise ToolkitError(f"Output or receipt already exists: {output}", "output_exists")
    if not staged.is_file() or staged.stat().st_size == 0:
        raise ToolkitError("No nonempty output produced", "validation_failed")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": True,
        "output": str(output),
        "bytes": staged.stat().st_size,
        "sha256": sha256_file(staged),
        **details,
    }
    receipt_dir = Path(tempfile.mkdtemp(prefix=".media-toolkit-", dir=str(output.parent)))
    try:
        receipt_tmp = receipt_dir / "receipt.json"
        receipt_tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _link_new(staged, output)
        try:
            _link_new(receipt_tmp, receipt)
        except ToolkitError:
            output.unlink()
            raise
    finally:
        receipt_tmp = receipt_dir / "receipt.json"
        if receipt_tmp.exists():
            receipt_tmp.unlink()
        receipt_dir.rmdir()
    return payload


def write_receipt(path: Path, details: dict | None = None) -> dict:
    """Write path.result.json for an existing file. Refuses if the receipt exists."""
    path = Path(path).expanduser().resolve()
    if not path.is_file() or path.stat().st_size == 0:
        raise ToolkitError(f"Input file not found: {path}", "input_missing")
    receipt = Path(str(path) + ".result.json")
    if receipt.exists():
        raise ToolkitError(f"Receipt already exists: {receipt}", "output_exists")
    payload = {
        "ok": True,
        "output": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        **(details or {}),
    }
    receipt_dir = Path(tempfile.mkdtemp(prefix=".media-toolkit-", dir=str(path.parent)))
    try:
        receipt_tmp = receipt_dir / "receipt.json"
        receipt_tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _link_new(receipt_tmp, receipt)
    finally:
        leftover = receipt_dir / "receipt.json"
        if leftover.exists():
            leftover.unlink()
        receipt_dir.rmdir()
    return payload


def validate_media(path: Path, timeout: float = 120) -> dict:
    """Probe the file, then fully decode every stream to the null muxer."""
    path = Path(path).expanduser().resolve()
    if not path.is_file() or path.stat().st_size == 0:
        raise ToolkitError(f"Input file not found: {path}", "input_missing")
    raw = run_bounded(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ],
        timeout,
    )
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ToolkitError("ffprobe did not return valid JSON", "probe_failed") from exc
    if not info.get("streams"):
        raise ToolkitError("Media contains no streams", "probe_failed")
    run_bounded(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-f", "null", "-"],
        timeout,
    )
    return info


def format_ts(value: float) -> str:
    milliseconds = int(round(max(0.0, value) * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def cue_block(cue: dict) -> str:
    return f"[{format_ts(float(cue['start']))} --> {format_ts(float(cue['end']))}]\n{cue['text']}\n"


def load_cues(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
        rows = data.get("cues") or data.get("segments") or []
        cues = []
        for row in rows:
            text = str(row.get("text", "")).strip()
            if not text:
                continue
            cues.append({"start": float(row["start"]), "end": float(row["end"]), "text": text})
        if not cues:
            raise ToolkitError(f"No cues in {path}", "subtitle_empty")
        return cues
    return parse_subtitles(raw)


def chunk_cues(cues: list[dict], chunk_chars: int) -> list[list[dict]]:
    if chunk_chars < 200:
        raise ToolkitError("chunk size must be at least 200 characters", "invalid_argument")
    groups: list[list[dict]] = []
    current: list[dict] = []
    size = 0
    for cue in cues:
        block = cue_block(cue)
        if current and size + len(block) > chunk_chars:
            groups.append(current)
            current = []
            size = 0
        current.append(cue)
        size += len(block)
    if current:
        groups.append(current)
    return groups


def write_timestamped_text(path: Path, out_dir: Path, chunk_chars: int) -> list[Path]:
    cues = load_cues(path)
    groups = chunk_cues(cues, chunk_chars)
    stem = path.stem
    written: list[Path] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    if len(groups) == 1:
        body = _part_text(path, groups[0], 1, 1)
        dest = out_dir / f"{stem}.txt"
        dest.write_text(body, encoding="utf-8")
        written.append(dest)
        return written
    part_dir = out_dir / stem
    part_dir.mkdir(parents=True, exist_ok=True)
    index_lines = [
        f"# source: {path.name}",
        f"# parts: {len(groups)}",
        "# Read the parts in order. Do not summarize them here.",
        "# The host agent writes the report from references/report-template.md.",
        "",
    ]
    for number, group in enumerate(groups, start=1):
        dest = part_dir / f"part-{number:03d}.txt"
        dest.write_text(_part_text(path, group, number, len(groups)), encoding="utf-8")
        start = format_ts(float(group[0]["start"]))
        end = format_ts(float(group[-1]["end"]))
        index_lines.append(f"part-{number:03d}.txt {start} --> {end}")
        written.append(dest)
    index = part_dir / "INDEX.txt"
    index.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    written.append(index)
    return written


def _part_text(path: Path, cues: list[dict], number: int, total: int) -> str:
    header = [
        f"# source: {path}",
        f"# part: {number}/{total}",
        f"# time: {format_ts(float(cues[0]['start']))} --> {format_ts(float(cues[-1]['end']))}",
        "# The host agent reads this and writes the report. This file is not a summary.",
        "",
    ]
    body = "\n".join(cue_block(cue).rstrip() for cue in cues)
    return "\n".join(header) + body + "\n"


def _cmd_text(args: argparse.Namespace) -> int:
    out_dir = Path(args.output)
    wrote: list[Path] = []
    for item in args.inputs:
        wrote.extend(write_timestamped_text(Path(item), out_dir, args.chunk_chars))
    for path in wrote:
        print(path)
    return 0


def _cmd_subtitles(args: argparse.Namespace) -> int:
    source = Path(args.input)
    cues = parse_subtitles(source.read_text(encoding="utf-8-sig"))
    document = {"text": clean_text(cues), "cues": cues, "source": str(source)}
    encoded = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        out = Path(args.output)
        if out.exists():
            raise ToolkitError(f"Output or receipt already exists: {out}", "output_exists")
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".media-toolkit-", dir=str(out.parent.resolve())) as tmp:
            staged = Path(tmp) / out.name
            staged.write_text(encoded, encoding="utf-8")
            publish_file(staged, out, {"command": "subtitles", "cues": len(cues)})
        print(encoded, end="")
    else:
        print(encoded, end="")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    info = validate_media(Path(args.input), timeout=args.timeout)
    codecs = [stream.get("codec_name") for stream in info["streams"]]
    print(json.dumps({"ok": True, "codecs": codecs}, ensure_ascii=False))
    return 0


def load_source_items(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        items = data.get("items", [])
    elif isinstance(data, list):
        items = data
    else:
        raise ToolkitError("sources file must be a list or an object with items", "invalid_argument")
    if not isinstance(items, list):
        raise ToolkitError("sources items must be a list", "invalid_argument")
    cleaned: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            raise ToolkitError("each source must be an object", "invalid_argument")
        url = str(item.get("url") or "").strip()
        if not url:
            raise ToolkitError("source item missing url", "invalid_argument")
        cleaned.append(item)
    return cleaned


def _cmd_sources(args: argparse.Namespace) -> int:
    items = load_source_items(Path(args.file))
    for item in items:
        if args.platform and str(item.get("platform") or "") != args.platform:
            continue
        print(str(item["url"]).strip())
    return 0


def _cmd_receipt(args: argparse.Namespace) -> int:
    payload = write_receipt(Path(args.input), {"command": "receipt"})
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Optional stdlib media helpers")
    sub = parser.add_subparsers(dest="command", required=True)
    subs = sub.add_parser("subtitles", help="Parse SRT/VTT without dropping numeric dialogue")
    subs.add_argument("input")
    subs.add_argument("-o", "--output")
    subs.set_defaults(func=_cmd_subtitles)
    validate = sub.add_parser("validate", help="Fully decode a media file with ffmpeg")
    validate.add_argument("input")
    validate.add_argument("--timeout", type=float, default=120)
    validate.set_defaults(func=_cmd_validate)
    receipt = sub.add_parser("receipt", help="Write a sha256 receipt without overwriting")
    receipt.add_argument("input")
    receipt.set_defaults(func=_cmd_receipt)
    text = sub.add_parser("text", help="Write timestamped plain text. Does not summarize.")
    text.add_argument("inputs", nargs="+")
    text.add_argument("-o", "--output", required=True)
    text.add_argument("--chunk-chars", type=int, default=12000)
    text.set_defaults(func=_cmd_text)
    sources = sub.add_parser("sources", help="Print URLs from sources.json. Does not download.")
    sources.add_argument("file")
    sources.add_argument("--platform", help="Keep items whose platform field matches")
    sources.set_defaults(func=_cmd_sources)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ToolkitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
