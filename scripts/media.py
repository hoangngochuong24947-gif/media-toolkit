#!/usr/bin/env python3
"""Run from any working directory: python /path/to/skill/scripts/media.py."""
import sys
from pathlib import Path
# Isolated Python omits the script directory; anchor imports to this trusted file.
sys.path.insert(0, str(Path(__file__).resolve().parent))
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8')
from media_toolkit.cli import main

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
