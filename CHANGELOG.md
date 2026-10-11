# Local revision 0.5.0-local

- Added explicit persistent request/selection/acquisition/report workflows with
  verified receipts, portable catalog links and truthful completion states.
- Added fair round-robin keyword collection, date ordering and sort-bound resume.
- Retain source-bound download parts after timeout/cancel; expose structured live
  progress and increase finite transfer budgets to 1800 seconds.
- Caption failure can fall back to local ASR; preserve raw text/provenance, require
  explicit model downloads and never invoke a cloud service implicitly.
- Added setup/check/install/launch entries and a portable Windows runtime profile.
- Host agent still chooses relevant sources and authors evidence-backed claims;
  report assembly does not independently certify speech or scientific accuracy.

# Local revision 0.4.0-local

- Added AAC M4A encoding and packet-hash-verified AAC/ALAC audio stream copy.
- Added directory image batches, collision preflight, source/output hash resume and partial failure state.
- Added runtime hardware selection for NVENC, QSV, VideoToolbox and VAAPI, plus H265; CPU fallback retains evidence.
- Added evidence-checked Markdown assembly for host-authored transcript claims.
- Added opt-in compatible multipart ASR API with timed segments and credential-safe errors.
- Real Windows checks: NVENC H264/H265, Intel QSV H264, official libheif HEIC decoding, YouTube captions/audio and cached local ASR.
- Cross-platform/clean-client/cloud-service/general accuracy claims remain unverified.

# Local revision 0.2.0-local

- Added executable Python CLI and validated local media outputs.
- Fixed numeric subtitle loss with cue/timestamp parsing.
- Enforced decimal budgets, infeasible-target errors and bounded retries.
- Added explicit accurate/fast trimming and NVENC-to-CPU failure fallback.
- Added image metadata checks and verified pixel-preserving WebP mode.
- Isolated staging files; refused input/previous-output overwrite.
- Added JSON receipts/checksums and regression tests.
- Removed unconditional speed, ratio, resolution and quality promises.

Local changes against upstream commit
6355bcd4996ffc6272842a9a9599e14a8be33017; no upstream release is implied.
# 0.3.0-local

- Add checkpointed YouTube keyword enumeration, ID deduplication, resumable
  batches, channel allowlists and Chinese offline HTML/CSV catalogs.
- Distinguish available-search exhaustion from limits/failures and all-platform
  coverage. Preserve per-item errors and validate hashes before skipping.
- Preserve raw captions and type/language/coverage metadata; deduplicate touching
  rolling cues without removing actual consecutive single-line repetition.
- Capture full bounded structured stdout instead of truncating at 64 KiB.
- Add audio-only download and isolated local faster-whisper worker with explicit
  model-cache/download controls, provenance and optional locked dependencies.

