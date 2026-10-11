# Persistent customer workflow

The host agent determines relevance, reads actual transcripts, and authors the
report. The CLI handles persistent execution and verifies evidence. It is not an
independent language model. Local media commands remain available separately.

## Request and discovery

Tell the user the scope once: platform, explicit query variants, ordering, date
boundary if any, candidate budget, and intended reading/download selections.
Choose routine defaults from the request; do not repeatedly ask for permission
for authorized reversible work. Clarify only material ambiguity. No claim of
all-site completeness. Date order does not filter dates: independently fetch
metadata and verify dates before selecting items for a recent-period requirement.

Create request.json outside the source repository:

```json
{
  "request": "Find DGX Spark videos, write a technical report, download the official video",
  "queries": ["NVIDIA DGX Spark official", "DGX Spark benchmarks"],
  "search": {"page_size": 10, "max_videos": 50, "max_pages": 10, "sort": "relevance"},
  "report_required": true,
  "subtitles_languages": "en,zh-Hans,zh-CN",
  "js_runtime": "node",
  "asr": {"enabled": true, "model": "small", "language": "en", "cache_dir": "models", "allow_model_download": false}
}
```

An official link obtained independently may be recorded in seed_videos with id,
title and the official backlink source. This does not establish verified official
identity by itself: the host must verify the backlink/channel before selecting.
Do not select the first search result solely on its display name.

Prefix commands with `python <skill>/scripts/media.py` or portable `media.cmd`:

```text
project init REQUEST.json -o JOB_DIR
project run JOB_DIR
project status JOB_DIR
project select JOB_DIR --video-id REVIEW_ID --video-id OFFICIAL_ID --download-id OFFICIAL_ID --reason "Official backlink verified; reviewer provides benchmark conditions"
project run JOB_DIR
```

The first run discovers candidates and returns awaiting_selection (incomplete,
nonzero exit); init/select return ok:true only for successful request changes.
Selections are additive and never silently discarded. Search scope is distinct
from content reading and downloads. Continue larger discovery budgets with
collect on JOB_DIR/discovery, preserving the same query strings and sort setting;
do not assume exhausting the returned search means complete platform coverage.

## Acquisition and recovery

Each selected video obtains subtitles when requested. If that fails and local ASR
is enabled, audio is acquired, raw ASR preserved, then a derived transcript links
the video URL with unchanged cues and a hash of the original. Missing model/cache
or ASR errors remain failed. API ASR is never selected implicitly.

Every requested video download is attempted even if another stage/source fails.
Use `project run JOB_DIR --retry-failed` to explicitly retry failed/cancelled
stages. Successful outputs are skipped only after receipt/hash verification;
tampering is preserved, not overwritten. Interrupted runs keep pending/running
checkpoints; source-bound download parts permit resuming when the server supports
it. Network/CDN changes may still prevent byte-level resume.

Read JOB_DIR/progress/current.json and events.jsonl while running. Distinguish
metadata/network, transfer and decode tool stages. A missing byte update is not a
failed download. Timeouts are finite and configurable; explicit cancellation is
cancelled, not access_denied. Do not kill unrelated system processes.

## Author and publish

Read every selected transcript used for the report. Preserve ASR/name/number
uncertainties; report only supported claims with test settings and timestamps.
Claims use the schema from capability-parity.md. All cited transcripts must be
verified selected artifacts; a claim from every selected transcript is required.

```text
project report JOB_DIR --claims CLAIMS.json
project status JOB_DIR
```

awaiting_report means acquisition done but the user request is not complete.
success/complete:true requires all requested selected artifacts and the report.
The HTML index uses relative artifact links and can move with the job directory.
ASR cache/profile absolute paths are user configuration; update them if relocated.

## Windows delivery

Portable candidate: unpack on D:, run check.cmd, then use media.cmd. The shipped
runtime/profile stays with the package, without system Python/PATH modification.
Models are separate; explicit first-download requires network. For optional agent
installation: `install-skill.cmd "AGENT_SKILL_DIR" "BACKUP_DIR"`. It validates
package files, backs up an existing skill, and installs lightweight files pointing
to the package runtime. Keep that runtime directory in place; after moving it,
repeat install with backup to refresh pointers. Source-only ZIP requires separately
configured tools/Python. Physical clean-client acceptance is a separate validation.
