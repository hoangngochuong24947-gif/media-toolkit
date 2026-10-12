# Changelog

## Unreleased

- README: a "what yt-dlp can and cannot do" checklist — the supported search, format, download, subtitle, playlist, cookie, and recovery paths, and the boundaries (DRM, live edge, region locks, bot checks on datacenter IPs, no LLM work).
- `tests/test_gates.sh`: the Agent-Reach dry-run assertion accepts any of the three valid reach plans (keep an installed CLI, plan the pipx install, report a missing Python 3.10+). The suite no longer fails on a machine that already has `agent-reach`, or on a host whose only `python3` is Apple's 3.9.
- Optional Agent-Reach companion (MIT, not vendored): `doctor.sh` reports `discovery (agent-reach)` and per-channel `active_backend`; `bootstrap.sh --with-reach` installs the GitHub zip with pipx or a user venv and does not configure logins.
- X/Twitter: yt-dlp for status videos, Agent-Reach `twitter` for search and post text, with a one-time confirmation before cookies or `TWITTER_AUTH_TOKEN` / `TWITTER_CT0`. Handoff file is `sources.json`.
- Hermes / agentskills.io `SKILL.md` frontmatter, `scripts/bootstrap.sh` (dry-run unless `--yes`), and install notes for Hermes, Claude Code, Codex, and Cursor.
- Distill path is agent-written. `scripts/subs_to_text.sh` emits timestamped text; `references/report-template.md` is the blank report. No script calls an LLM.
- Confirmation gates: ASR and downloads print a plan and exit 0 until `--yes` or `MEDIA_CONFIRM=1`. Bootstrap does not prompt for sudo.
- Documented a short skill that routes to `references/`, with `scripts/doctor.sh` as the setup check.
- Added bash recipes for GIF palette generation (`-update 1`), target-size two-pass (awk, not `bc`), trim, MP3 extract, ImageMagick 6/7 convert, and hardware-encode fallback.
- Cookie policy: local `--cookies-from-browser` is the normal personal path; `cookies.txt` stays outside the repo.
- Search results use `%(webpage_url)s`.
- Optional `scripts/optional_tools.py` (stdlib, `python3`) adapts three ideas from cowboy596's MIT media-toolkit contribution: a bounded subprocess with timeout, no-overwrite publication plus a sha256 receipt, and subtitle parsing that keeps numeric dialogue and timestamps. Full-decode validation is the `validate` subcommand. Hardware fallback for this tree lives in `scripts/encode.sh`.

The project/collection state machine, Windows `.cmd` launchers, manifest hash gate, and hosted transcription client from that contribution are not part of this tree.
