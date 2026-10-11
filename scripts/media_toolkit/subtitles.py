"""Parse subtitle cues; never filter dialogue by its first character."""
import html
import re
from .runtime import ToolkitError

TIMESTAMP = r'(?:\d+:)?\d{2}:\d{2}[.,]\d{3}'
CUE = re.compile(rf'^({TIMESTAMP})\s+-->\s+({TIMESTAMP})(?:\s+.*)?$')


def seconds(value):
    parts = value.replace(',', '.').split(':')
    numbers = list(map(float, parts))
    if len(numbers) == 3:
        hours, minutes, sec = numbers
    else:
        hours, minutes, sec = 0, *numbers
    if minutes >= 60 or sec >= 60:
        raise ToolkitError('Invalid subtitle timestamp', 'subtitle_invalid')
    return hours * 3600 + minutes * 60 + sec


def parse_subtitles(text):
    cues = []
    # A cue identifier or SRT index is outside the timestamp/body block.
    for block in re.split(r'\n\s*\n', text.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n').strip()):
        lines = block.splitlines()
        if not lines or re.match(r'^(NOTE(?:\s|$)|STYLE$|REGION$)', lines[0]):
            continue
        matches = [(i, CUE.match(line.strip())) for i, line in enumerate(lines)]
        found = next(((i, m) for i, m in matches if m), None)
        if not found:
            if any('-->' in line for line in lines):
                raise ToolkitError('Malformed subtitle cue', 'subtitle_invalid')
            continue
        index, match = found
        start, end = seconds(match[1]), seconds(match[2])
        if end <= start:
            raise ToolkitError('Subtitle end must follow start', 'subtitle_invalid')
        body = '\n'.join(lines[index+1:])
        body = html.unescape(re.sub(r'<[^>]*>', '', body))
        body = '\n'.join(line.strip() for line in body.splitlines() if line.strip())
        if body:
            cues.append(dict(start=start, end=end, text=body))
    if not cues:
        raise ToolkitError('No valid subtitle cues found', 'subtitle_empty')
    return cues


def clean_text(cues):
    output = []; previous = None
    for cue in cues:
        lines = cue['text'].splitlines()
        # Rolling captions often include a 10 ms single-line carry frame at
        # exactly the previous end. Do not erase actual consecutive "Yes, Yes".
        touching_roll = previous and abs(cue['start'] - previous['end']) <= 0.001 and (
            len(previous['text'].splitlines()) > 1 or len(lines) > 1 or
            previous['end'] - previous['start'] <= 0.05 or cue['end'] - cue['start'] <= 0.05)
        if previous and (cue['start'] < previous['end'] or touching_roll):
            old = previous['text'].splitlines()
            for overlap in range(min(len(old), len(lines)), 0, -1):
                if old[-overlap:] == lines[:overlap]:
                    lines = lines[overlap:]
                    break
        output.extend(lines)
        previous = cue
    return '\n'.join(output) + '\n'
