import importlib.util
import math
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
AVAILABLE = importlib.util.find_spec('media_toolkit') is not None
if AVAILABLE:
    from media_toolkit.subtitles import parse_subtitles, clean_text
    from media_toolkit.runtime import ToolkitError, target_bitrate, classify_network_error


class AvailabilityTests(unittest.TestCase):
    def test_executable_toolkit_exists(self):
        self.assertTrue(AVAILABLE, 'The repository must ship an executable media toolkit')


@unittest.skipUnless(AVAILABLE, 'CLI not implemented yet')
class SubtitleTests(unittest.TestCase):
    def test_numeric_body_and_markup(self):
        cues = parse_subtitles('WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n128GB <c>unified</c> memory &amp; compute\n')
        self.assertEqual(cues[0]['text'], '128GB unified memory & compute')
        self.assertEqual(cues[0]['start'], 0)
        self.assertEqual(cues[0]['end'], 2)

    def test_srt_numbers_are_only_removed_outside_cue(self):
        cues = parse_subtitles('1\n00:00:01,000 --> 00:00:02,500\n2026 results\n42\n\n2\n00:00:03,000 --> 00:00:04,000\nNext\n')
        self.assertEqual(cues[0]['text'], '2026 results\n42')

    def test_overlapping_rolling_lines_are_deduplicated(self):
        cues = parse_subtitles('WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nFirst line\nshared line\n\n00:00:01.000 --> 00:00:03.000\nshared line\nnew line\n')
        self.assertEqual(clean_text(cues), 'First line\nshared line\nnew line\n')

    def test_nonoverlapping_repetition_is_preserved(self):
        cues = parse_subtitles('00:00:00.000 --> 00:00:01.000\nYes\n\n00:00:02.000 --> 00:00:03.000\nYes\n')
        self.assertEqual(clean_text(cues), 'Yes\nYes\n')

    def test_vtt_note_and_style_are_not_dialogue(self):
        cues = parse_subtitles('WEBVTT\n\nNOTE metadata\nnot dialogue\n\nSTYLE\n::cue { color: red; }\n\ncue-id\n00:01.000 --> 00:02.000 align:start\n<v Speaker>Hello</v><00:01.500>\n')
        self.assertEqual(cues, [dict(start=1.0, end=2.0, text='Hello')])

    def test_invalid_input_fails(self):
        for text in ['plain text', '00:00:03.000 --> 00:00:01.000\nwrong']:
            with self.subTest(text=text), self.assertRaises(ToolkitError):
                parse_subtitles(text)


@unittest.skipUnless(AVAILABLE, 'CLI not implemented yet')
class BudgetTests(unittest.TestCase):
    def test_decimal_mb_budget(self):
        self.assertEqual(target_bitrate(500_000, 10, 96_000), 264_000)

    def test_impossible_budget_is_rejected(self):
        with self.assertRaises(ToolkitError):
            target_bitrate(50_000, 10, 96_000)

    def test_nonfinite_and_zero_inputs_are_rejected(self):
        for duration in [0, -1, math.inf, math.nan]:
            with self.subTest(duration=duration), self.assertRaises(ToolkitError):
                target_bitrate(500_000, duration, 96_000)

    def test_network_failures_are_classified(self):
        for message, expected in [('HTTP Error 429', 'rate_limit'), ('HTTP Error 403', 'access_denied'), ('SSL EOF', 'network'), ('No video formats found', 'formats'), ('unknown error', 'download_failed')]:
            self.assertEqual(classify_network_error(message), expected)


if __name__ == '__main__':
    unittest.main()
