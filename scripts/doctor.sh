#!/usr/bin/env bash
# Report local-media, online-download, transcription, and image readiness.
# Exit 1 when a required tool is missing: ffmpeg, ffprobe, or yt-dlp.
# ImageMagick, a JS runtime, and python3 are capabilities, not hard failures.
# Bash 3.2 or newer. No third-party dependencies.
set -u

YT_DLP_VERSION="2026.08.19"

ok() { printf '[ok] %s\n' "$*"; }
miss() { printf '[missing] %s\n' "$*"; }
warn() { printf '[warn] %s\n' "$*"; }
info() { printf '[info] %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

OS_NAME="$(uname -s)"
OS_KIND="unknown"
case "$OS_NAME" in
  Darwin) OS_KIND="macos" ;;
  Linux)
    OS_KIND="linux"
    if [ -r /proc/version ] && grep -qi microsoft /proc/version; then
      OS_KIND="wsl"
    fi
    ;;
  MINGW*|MSYS*|CYGWIN*) OS_KIND="gitbash" ;;
esac

PM="none"
if [ "$OS_KIND" = "macos" ] || have brew; then
  PM="brew"
elif have apt-get; then
  PM="apt"
elif have dnf; then
  PM="dnf"
elif have pacman; then
  PM="pacman"
fi

install_ffmpeg() {
  case "$PM" in
    brew) printf '%s\n' "brew install ffmpeg" ;;
    apt) printf '%s\n' "sudo apt update && sudo apt install -y ffmpeg" ;;
    dnf) printf '%s\n' "sudo dnf install -y ffmpeg" ;;
    pacman) printf '%s\n' "sudo pacman -S --needed ffmpeg" ;;
    *) printf '%s\n' "Install ffmpeg from your system package manager so ffmpeg and ffprobe are both on PATH" ;;
  esac
}

install_imagemagick() {
  case "$PM" in
    brew) printf '%s\n' "brew install imagemagick" ;;
    apt) printf '%s\n' "sudo apt update && sudo apt install -y imagemagick" ;;
    dnf) printf '%s\n' "sudo dnf install -y ImageMagick" ;;
    pacman) printf '%s\n' "sudo pacman -S --needed imagemagick" ;;
    *) printf '%s\n' "Install ImageMagick from your system package manager (magick on v7, or convert on v6)" ;;
  esac
}

install_ytdlp() {
  case "$PM" in
    brew)
      printf '%s\n' "brew install yt-dlp"
      printf '%s\n' "Pinned binary instead of the Homebrew bottle:"
      ;;
  esac
  printf '%s\n' "sudo curl -L \"https://github.com/yt-dlp/yt-dlp/releases/download/${YT_DLP_VERSION}/yt-dlp\" -o /usr/local/bin/yt-dlp && sudo chmod a+rx /usr/local/bin/yt-dlp"
  printf '%s\n' "Or, with pipx so the executable is on PATH after ensurepath:"
  printf '%s\n' "python3 -m pip install --user pipx && python3 -m pipx ensurepath && pipx install \"yt-dlp==${YT_DLP_VERSION}\""
  printf '%s\n' "Upgrade later: sudo yt-dlp --update-to stable    or    pipx upgrade yt-dlp"
}

install_js() {
  case "$PM" in
    brew) printf '%s\n' "brew install deno" ;;
    pacman) printf '%s\n' "sudo pacman -S --needed deno" ;;
    *)
      printf '%s\n' "curl -fsSL https://deno.land/install.sh | sh"
      printf '%s\n' "export PATH=\"\$HOME/.deno/bin:\$PATH\""
      ;;
  esac
  case "$PM" in
    brew) printf '%s\n' "Acceptable alternative: brew install node" ;;
    apt) printf '%s\n' "Acceptable alternative: sudo apt update && sudo apt install -y nodejs" ;;
    dnf) printf '%s\n' "Acceptable alternative: sudo dnf install -y nodejs" ;;
    pacman) printf '%s\n' "Acceptable alternative: sudo pacman -S --needed nodejs" ;;
    *) printf '%s\n' "Acceptable alternative: install Node.js so node is on PATH" ;;
  esac
}

install_python3() {
  case "$PM" in
    brew) printf '%s\n' "brew install python" ;;
    apt) printf '%s\n' "sudo apt update && sudo apt install -y python3 python3-pip python3-venv pipx" ;;
    dnf) printf '%s\n' "sudo dnf install -y python3 python3-pip pipx" ;;
    pacman) printf '%s\n' "sudo pacman -S --needed python python-pip python-pipx" ;;
    *) printf '%s\n' "Install python3 from your system package manager" ;;
  esac
  printf '%s\n' "Use python3, never bare python."
  printf '%s\n' "Optional transcription venv: python3 -m venv .venv && . .venv/bin/activate && python3 -m pip install -r requirements-asr.txt"
}

print_bundle() {
  info "one-line install for this machine (system packages, yt-dlp on PATH, no extra services):"
  case "$PM" in
    brew)
      printf '%s\n' "brew install ffmpeg imagemagick yt-dlp deno python"
      ;;
    apt)
      printf '%s\n' "sudo apt update && sudo apt install -y ffmpeg imagemagick python3 python3-pip python3-venv pipx curl ca-certificates nodejs && sudo curl -L \"https://github.com/yt-dlp/yt-dlp/releases/download/${YT_DLP_VERSION}/yt-dlp\" -o /usr/local/bin/yt-dlp && sudo chmod a+rx /usr/local/bin/yt-dlp"
      ;;
    dnf)
      printf '%s\n' "sudo dnf install -y ffmpeg ImageMagick python3 python3-pip pipx curl nodejs && sudo curl -L \"https://github.com/yt-dlp/yt-dlp/releases/download/${YT_DLP_VERSION}/yt-dlp\" -o /usr/local/bin/yt-dlp && sudo chmod a+rx /usr/local/bin/yt-dlp"
      ;;
    pacman)
      printf '%s\n' "sudo pacman -S --needed ffmpeg imagemagick yt-dlp deno python python-pip python-pipx"
      ;;
    *)
      printf '%s\n' "See references/troubleshooting.md for Git Bash / WSL install lines."
      ;;
  esac
}

printf '%s\n' "media-toolkit doctor"
printf '%s\n' "os: ${OS_KIND} (${OS_NAME})"
printf '%s\n' "package-manager: ${PM}"
printf '%s\n' "yt-dlp-known-good: ${YT_DLP_VERSION}"
if [ "$OS_KIND" = "wsl" ]; then
  info "Windows detected via WSL. Install packages inside this distro. Scripts run under bash here."
elif [ "$OS_KIND" = "gitbash" ]; then
  info "Git Bash detected. Prefer WSL for the apt one-liner, or install Windows builds and keep them on PATH:"
  printf '%s\n' "winget install --id Gyan.FFmpeg -e --id yt-dlp.yt-dlp -e --id ImageMagick.ImageMagick -e --id DenoLand.Deno -e --id Python.Python.3.12 -e"
fi
if [ "$PM" = "dnf" ]; then
  info "If dnf cannot find ffmpeg, enable RPM Fusion for your Fedora/RHEL version, then rerun the install line."
fi
if [ "$PM" = "brew" ] && ! have brew; then
  warn "This looks like macOS but brew is not on PATH. Install Homebrew, then rerun doctor."
fi

missing_required=0
local_media="ready"
online="ready"
transcription="ready"
images="ready"
ffmpeg_hint=0

if have ffmpeg; then
  ok "ffmpeg: $(command -v ffmpeg)"
else
  miss "ffmpeg (required for local-media)"
  install_ffmpeg
  ffmpeg_hint=1
  missing_required=1
  local_media="not-ready"
fi

if have ffprobe; then
  ok "ffprobe: $(command -v ffprobe)"
else
  miss "ffprobe (required for local-media; it ships with the ffmpeg package)"
  if [ "$ffmpeg_hint" -eq 0 ]; then
    install_ffmpeg
  fi
  missing_required=1
  local_media="not-ready"
fi

LOCAL_YT="${HOME}/.local/bin/yt-dlp"
if [ -x "$LOCAL_YT" ] && ! have yt-dlp; then
  warn "yt-dlp is installed at ~/.local/bin/yt-dlp but that directory is not on PATH."
  printf '%s\n' "Fix now: export PATH=\"\$HOME/.local/bin:\$PATH\""
  printf '%s\n' "Persist: add that line to ~/.bashrc or ~/.zshrc, then open a new shell."
fi

if have yt-dlp; then
  ok "yt-dlp: $(command -v yt-dlp)"
  if yt-dlp --version >/dev/null 2>&1; then
    info "yt-dlp version: $(yt-dlp --version 2>/dev/null | head -n 1)"
  fi
  info "Known-good stable pin: ${YT_DLP_VERSION}. Upgrade: sudo yt-dlp --update-to stable   or   pipx upgrade yt-dlp"
else
  miss "yt-dlp (required for online-download; must be on PATH)"
  install_ytdlp
  missing_required=1
  online="not-ready"
fi

IM_BIN=""
IM_KIND=""
if have magick; then
  IM_BIN="$(command -v magick)"
  IM_KIND="magick (v7)"
  ok "imagemagick: ${IM_KIND} at ${IM_BIN}"
elif have convert; then
  IM_BIN="$(command -v convert)"
  IM_KIND="convert (v6)"
  ok "imagemagick: ${IM_KIND} at ${IM_BIN}"
  if have mogrify; then
    info "mogrify: $(command -v mogrify)"
  fi
else
  miss "imagemagick (magick or convert). Images are not ready."
  install_imagemagick
  images="not-ready"
fi

if have deno; then
  ok "js-runtime: deno (preferred) at $(command -v deno)"
elif have node; then
  ok "js-runtime: node (acceptable) at $(command -v node)"
  info "deno is preferred for YouTube n-challenges. Optional install:"
  install_js
else
  miss "js runtime (deno preferred, node acceptable). YouTube downloads may fail signature checks."
  install_js
  if [ "$online" = "ready" ]; then
    online="degraded"
  fi
fi

if have python3; then
  ok "python3: $(command -v python3)"
  info "Transcription only: python3 -m venv .venv && . .venv/bin/activate && python3 -m pip install -r requirements-asr.txt"
else
  miss "python3 (required only for local transcription)"
  install_python3
  transcription="not-ready"
fi

if have python && ! have python3; then
  warn "Found python ($(command -v python)) but not python3. Call python3; do not call bare python."
fi

if have ffmpeg; then
  printf '%s\n' "hw-encoders (a listed name can still fail without a GPU; scripts fall back to libx264/libx265):"
  ffmpeg -hide_banner -encoders 2>/dev/null | awk '/h264_nvenc|hevc_nvenc|h264_vaapi|hevc_vaapi|h264_qsv|hevc_qsv|h264_videotoolbox|hevc_videotoolbox|libx264 |libx265 / { print }' || true
  info "fallback: libx264 / libx265"
fi

printf '%s\n' "capability local-media: ${local_media}"
printf '%s\n' "capability online-download: ${online}"
printf '%s\n' "capability transcription: ${transcription}"
printf '%s\n' "capability images: ${images}"
if [ -n "$IM_KIND" ]; then
  printf '%s\n' "imagemagick-choice: ${IM_KIND}"
else
  printf '%s\n' "imagemagick-choice: none"
fi

if [ "$missing_required" -ne 0 ]; then
  print_bundle
  printf '%s\n' "next: bash scripts/bootstrap.sh    (dry-run; ask the user before sudo, then --yes)"
  printf '%s\n' "result: fail"
  exit 1
fi

printf '%s\n' "result: ok"
exit 0
