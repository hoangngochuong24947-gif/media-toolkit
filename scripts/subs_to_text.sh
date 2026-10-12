#!/usr/bin/env bash
# Turn SRT, VTT, or transcript JSON into timestamped plain text for the agent.
# Does not summarize. Usage: subs_to_text.sh FILE [FILE...] -o DIR [--chunk-chars N]
set -euo pipefail

ROOT="$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)"
exec python3 "${ROOT}/scripts/optional_tools.py" text "$@"
