"""Offline tests for optional stdlib helpers. No network."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from optional_tools import (  # noqa: E402
    ToolkitError,
    clean_text,
    parse_subtitles,
    publish_file,
    run_bounded,
    write_receipt,
)


class SubtitleTests(unittest.TestCase):
    def test_numeric_body_and_markup(self):
        cues = parse_subtitles(
            "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n128GB <c>unified</c> memory &amp; compute\n"
        )
        self.assertEqual(cues[0]["text"], "128GB unified memory & compute")
        self.assertEqual(cues[0]["start"], 0)
        self.assertEqual(cues[0]["end"], 2)

    def test_srt_numbers_are_only_removed_outside_cue(self):
        cues = parse_subtitles(
            "1\n00:00:01,000 --> 00:00:02,500\n2026 results\n42\n\n2\n00:00:03,000 --> 00:00:04,000\nNext\n"
        )
        self.assertEqual(cues[0]["text"], "2026 results\n42")
        self.assertEqual(cues[1]["text"], "Next")

    def test_overlapping_rolling_lines_are_deduplicated(self):
        cues = parse_subtitles(
            "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nFirst line\nshared line\n\n"
            "00:00:01.000 --> 00:00:03.000\nshared line\nnew line\n"
        )
        self.assertEqual(clean_text(cues), "First line\nshared line\nnew line\n")

    def test_nonoverlapping_repetition_is_preserved(self):
        cues = parse_subtitles(
            "00:00:00.000 --> 00:00:01.000\nYes\n\n00:00:02.000 --> 00:00:03.000\nYes\n"
        )
        self.assertEqual(clean_text(cues), "Yes\nYes\n")

    def test_vtt_note_and_style_are_not_dialogue(self):
        cues = parse_subtitles(
            "WEBVTT\n\nNOTE metadata\nnot dialogue\n\nSTYLE\n::cue { color: red; }\n\n"
            "cue-id\n00:01.000 --> 00:02.000 align:start\n<v Speaker>Hello</v><00:01.500>\n"
        )
        self.assertEqual(cues, [{"start": 1.0, "end": 2.0, "text": "Hello"}])

    def test_invalid_input_fails(self):
        for text in ["plain text", "00:00:03.000 --> 00:00:01.000\nwrong"]:
            with self.subTest(text=text):
                with self.assertRaises(ToolkitError):
                    parse_subtitles(text)


class ReceiptTests(unittest.TestCase):
    def test_publish_writes_sha256_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staged = root / "staged.bin"
            staged.write_bytes(b"abc")
            output = root / "out.bin"
            payload = publish_file(staged, output, {"command": "test"})
            self.assertEqual(payload["sha256"], "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
            self.assertTrue((root / "out.bin.result.json").is_file())
            with self.assertRaises(ToolkitError):
                publish_file(staged, output, {"command": "test"})

    def test_receipt_refuses_second_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clip.bin"
            path.write_bytes(b"xyz")
            first = write_receipt(path, {"command": "receipt"})
            self.assertEqual(first["bytes"], 3)
            with self.assertRaises(ToolkitError):
                write_receipt(path)


class TextTests(unittest.TestCase):
    def test_timestamped_text_keeps_numbers_and_chunks(self):
        from optional_tools import write_timestamped_text

        cue = "1\n00:00:01,000 --> 00:00:02,000\n2026 results\n\n"
        body = ""
        for index in range(6):
            start = index * 2
            body += f"{index + 1}\n00:00:{start:02d},000 --> 00:00:{start + 1:02d},500\nline {index} 128GB\n\n"
        body = cue + body
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "talk.srt"
            source.write_text(body, encoding="utf-8")
            wrote = write_timestamped_text(source, root / "text", 200)
            joined = "\n".join(path.read_text(encoding="utf-8") for path in wrote)
            self.assertIn("2026 results", joined)
            self.assertIn("[00:00:01.000 --> 00:00:02.000]", joined)
            self.assertTrue((root / "text" / "talk" / "INDEX.txt").is_file())
            self.assertGreater(len(list((root / "text" / "talk").glob("part-*.txt"))), 1)


class SourceTests(unittest.TestCase):
    def test_urls_keep_fields_and_filter_platform(self):
        from optional_tools import load_source_items

        payload = {
            "items": [
                {
                    "url": "https://x.com/example/status/1",
                    "platform": "twitter",
                    "title": "a post",
                    "author": "someone",
                    "published": "2026-01-02",
                    "why_selected": "mentions the topic",
                },
                {
                    "url": "https://www.bilibili.com/video/BVxxxxxxxxxx",
                    "platform": "bilibili",
                    "title": "a video",
                    "author": "uploader",
                    "published": "",
                    "why_selected": "BV link from bili search",
                },
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            items = load_source_items(path)
            self.assertEqual(items[0]["why_selected"], "mentions the topic")
            script = Path(__file__).resolve().parents[1] / "scripts" / "optional_tools.py"
            proc = subprocess.run(
                [sys.executable, str(script), "sources", str(path), "--platform", "twitter"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.stdout.strip(), "https://x.com/example/status/1")


class TimeoutTests(unittest.TestCase):
    def test_sleep_is_killed(self):
        with self.assertRaises(ToolkitError) as caught:
            run_bounded(["/bin/sleep", "5"], 0.2)
        self.assertEqual(caught.exception.code, "timeout")


if __name__ == "__main__":
    unittest.main()
