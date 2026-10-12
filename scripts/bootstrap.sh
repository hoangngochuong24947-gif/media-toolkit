#!/usr/bin/env bash
# Install missing media tools. Dry-run unless --yes / --confirm / MEDIA_CONFIRM=1.
# Does not prompt for a sudo password. Without passwordless sudo, system packages
# are skipped and the script says so.
set -u

SKILL_DIR="$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)"
YT_DLP_VERSION="2026.08.19"
APPLY=0
DRY_FLAG=0
YES_FLAG=0
WITH_ASR=0
WITH_REACH=0
REACH_FAIL=0
AGENT_REACH_URL="https://github.com/Panniantong/Agent-Reach/archive/main.zip"

usage() {
  cat <<'EOF'
usage: bootstrap.sh [--dry-run] [--yes|--confirm] [--with-asr] [--with-reach]

Default is dry-run: print the plan and do not install.
--yes installs. Ask the user before sudo or system packages, then pass --yes.
--with-asr also creates .venv and installs requirements-asr.txt (only with --yes).
--with-reach installs the Agent-Reach CLI from its GitHub zip (pipx, or a user venv).
It does not use sudo, does not write logins or cookies, and does not run
`agent-reach install --system`.
MEDIA_CONFIRM=1 is the same as --yes.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --yes|--confirm) YES_FLAG=1 ;;
    --dry-run) DRY_FLAG=1 ;;
    --with-asr) WITH_ASR=1 ;;
    --with-reach) WITH_REACH=1 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [ "$YES_FLAG" -eq 1 ] && [ "$DRY_FLAG" -eq 1 ]; then
  printf 'pass only one of --yes and --dry-run\n' >&2
  exit 2
fi
if [ "$DRY_FLAG" -eq 1 ]; then
  APPLY=0
elif [ "$YES_FLAG" -eq 1 ] || [ "${MEDIA_CONFIRM:-}" = "1" ]; then
  APPLY=1
fi

have() { command -v "$1" >/dev/null 2>&1; }

OS_NAME="$(uname -s)"
PM="none"
case "$OS_NAME" in
  Darwin) PM="brew" ;;
esac
if [ "$PM" = "none" ]; then
  if have brew; then PM="brew"
  elif have apt-get; then PM="apt"
  elif have dnf; then PM="dnf"
  elif have pacman; then PM="pacman"
  fi
fi

can_sudo() {
  if [ "$(id -u)" -eq 0 ]; then
    return 0
  fi
  have sudo && sudo -n true >/dev/null 2>&1
}

run_cmd() {
  if [ "$APPLY" -eq 1 ]; then
    "$@"
  else
    printf 'would-run:'
    printf ' %q' "$@"
    printf '\n'
  fi
}

run_root() {
  if [ "$(id -u)" -eq 0 ]; then
    run_cmd "$@"
    return $?
  fi
  if can_sudo; then
    if [ "$APPLY" -eq 1 ]; then
      sudo -n "$@"
    else
      printf 'would-run: sudo -n'
      printf ' %q' "$@"
      printf '\n'
      printf 'sudo: yes (passwordless sudo is available; ask the user before --yes)\n'
    fi
    return $?
  fi
  printf 'no-sudo: not running:'
  printf ' %q' "$@"
  printf '\n'
  printf 'Ask the user before they run sudo. This script does not prompt.\n'
  return 1
}

ensure_user_path() {
  line='export PATH="$HOME/.local/bin:$HOME/.deno/bin:$PATH"'
  marker='# media-toolkit PATH'
  for rc in "$HOME/.bashrc" "$HOME/.profile"; do
    if [ -f "$rc" ] && grep -qF "$marker" "$rc"; then
      printf 'path: already recorded in %s\n' "$rc"
      continue
    fi
    if [ "$APPLY" -eq 1 ]; then
      printf '\n%s\n%s\n' "$marker" "$line" >> "$rc"
      printf 'path: appended to %s\n' "$rc"
    else
      printf 'would-append to %s: %s\n' "$rc" "$line"
    fi
  done
  export PATH="${HOME}/.local/bin:${HOME}/.deno/bin:${PATH}"
}

install_pkgs() {
  case "$PM" in
    brew) run_cmd brew install "$@" ;;
    apt) run_root apt-get update && run_root apt-get install -y "$@" ;;
    dnf) run_root dnf install -y "$@" ;;
    pacman) run_root pacman -S --noconfirm --needed "$@" ;;
    *)
      printf 'no package manager detected for: %s\n' "$*"
      return 1
      ;;
  esac
}

if [ "$APPLY" -eq 1 ]; then
  printf 'bootstrap: yes\n'
else
  printf 'bootstrap: dry-run\n'
fi
printf 'package-manager: %s\n' "$PM"
printf 'skill-dir: %s\n' "$SKILL_DIR"

if have ffmpeg && have ffprobe; then
  printf 'keep: ffmpeg %s\n' "$(command -v ffmpeg)"
else
  printf 'missing: ffmpeg (system package, may use sudo)\n'
  install_pkgs ffmpeg || true
fi

if have magick || have convert; then
  if have magick; then
    printf 'keep: magick %s\n' "$(command -v magick)"
  else
    printf 'keep: convert %s\n' "$(command -v convert)"
  fi
else
  printf 'missing: ImageMagick (system package, may use sudo)\n'
  case "$PM" in
    dnf) install_pkgs ImageMagick || true ;;
    *) install_pkgs imagemagick || true ;;
  esac
fi

if have deno; then
  printf 'keep: deno %s\n' "$(command -v deno)"
elif [ "$PM" = "brew" ]; then
  printf 'missing: deno\n'
  install_pkgs deno || true
elif [ "$PM" = "pacman" ]; then
  printf 'missing: deno\n'
  install_pkgs deno || true
else
  printf 'missing: deno (user install into ~/.deno, no sudo)\n'
  if [ "$APPLY" -eq 1 ]; then
    curl -fsSL https://deno.land/install.sh | DENO_INSTALL="${HOME}/.deno" sh
  else
    printf 'would-run: curl -fsSL https://deno.land/install.sh | DENO_INSTALL=$HOME/.deno sh\n'
  fi
fi

if have yt-dlp; then
  printf 'keep: yt-dlp %s\n' "$(command -v yt-dlp)"
elif [ "$PM" = "brew" ]; then
  printf 'missing: yt-dlp\n'
  install_pkgs yt-dlp || true
else
  printf 'missing: yt-dlp %s -> ~/.local/bin (no sudo)\n' "$YT_DLP_VERSION"
  if [ "$APPLY" -eq 1 ]; then
    mkdir -p "${HOME}/.local/bin"
    tmp="$(mktemp "${TMPDIR:-/tmp}/yt-dlp.XXXXXX")"
    if curl -fL "https://github.com/yt-dlp/yt-dlp/releases/download/${YT_DLP_VERSION}/yt-dlp" -o "$tmp"; then
      chmod a+rx "$tmp"
      mv "$tmp" "${HOME}/.local/bin/yt-dlp"
    else
      rm -f "$tmp"
      printf 'yt-dlp download failed\n' >&2
    fi
  else
    printf 'would-run: curl -fL https://github.com/yt-dlp/yt-dlp/releases/download/%s/yt-dlp -o ~/.local/bin/yt-dlp\n' "$YT_DLP_VERSION"
  fi
fi

ensure_user_path

if [ "$WITH_REACH" -eq 1 ]; then
  printf 'reach-policy: no sudo, no cookie configure, no TWITTER_* export, no agent-reach install --system\n'
  printf 'reach-source: %s\n' "$AGENT_REACH_URL"
  printf 'reach-note: do not pip-install the PyPI name agent-reach; upstream says that name is a different project\n'
  if have agent-reach; then
    printf 'keep: agent-reach %s\n' "$(command -v agent-reach)"
  else
    py_ok="$(python3 -c 'import sys; print("yes" if sys.version_info >= (3, 10) else "no")' 2>/dev/null || printf 'no')"
    if [ "$py_ok" != "yes" ]; then
      printf 'missing: Python 3.10+ (Agent-Reach requirement). Not installing.\n'
    elif [ "$APPLY" -ne 1 ]; then
      printf 'would-run: pipx install %s\n' "$AGENT_REACH_URL"
      printf 'fallback: python3 -m venv ~/.agent-reach-venv && ~/.agent-reach-venv/bin/python3 -m pip install %s\n' "$AGENT_REACH_URL"
    elif have pipx; then
      pipx install "$AGENT_REACH_URL" || REACH_FAIL=1
    elif python3 -m pipx --version >/dev/null 2>&1; then
      python3 -m pipx install "$AGENT_REACH_URL" || REACH_FAIL=1
    else
      printf 'pipx missing; using ~/.agent-reach-venv (documented fallback, no sudo)\n'
      venv_py="${HOME}/.agent-reach-venv/bin/python3"
      if [ ! -x "$venv_py" ]; then
        python3 -m venv "${HOME}/.agent-reach-venv"
      fi
      if ! "$venv_py" -m pip --version >/dev/null 2>&1; then
        # Ubuntu can create a venv without ensurepip when python3-venv is absent.
        # get-pip.py stays inside that venv. No sudo.
        get_pip="$(mktemp "${TMPDIR:-/tmp}/get-pip.XXXXXX.py")"
        if curl -fsSL https://bootstrap.pypa.io/get-pip.py -o "$get_pip"; then
          "$venv_py" "$get_pip"
        fi
        rm -f "$get_pip"
      fi
      if "$venv_py" -m pip --version >/dev/null 2>&1; then
        "$venv_py" -m pip install --disable-pip-version-check "$AGENT_REACH_URL"
        mkdir -p "${HOME}/.local/bin"
        ln -sfn "${venv_py%/*}/agent-reach" "${HOME}/.local/bin/agent-reach"
      else
        printf 'agent-reach install failed: venv has no pip. python3-venv or pipx would fix it.\n' >&2
        REACH_FAIL=1
      fi
    fi
    if [ "$APPLY" -eq 1 ] && ! have agent-reach && [ ! -x "${HOME}/.local/bin/agent-reach" ]; then
      printf 'agent-reach install failed\n' >&2
      REACH_FAIL=1
    fi
  fi
else
  if have agent-reach; then
    printf 'keep: agent-reach %s\n' "$(command -v agent-reach)"
  else
    printf 'optional: agent-reach not requested (bash scripts/bootstrap.sh --with-reach)\n'
  fi
fi

if [ "$WITH_ASR" -eq 1 ]; then
  printf 'asr: python3 -m venv %s/.venv && python3 -m pip install -r requirements-asr.txt\n' "$SKILL_DIR"
  printf 'asr-note: large wheels and, later, a model download. Ask before --yes --with-asr.\n'
  if [ "$APPLY" -eq 1 ]; then
    if ! have python3; then
      printf 'missing: python3 (needed for the venv)\n'
      case "$PM" in
        apt) install_pkgs python3 python3-pip python3-venv || true ;;
        dnf) install_pkgs python3 python3-pip || true ;;
        pacman) install_pkgs python python-pip || true ;;
        brew) install_pkgs python || true ;;
      esac
    fi
    python3 -m venv "${SKILL_DIR}/.venv"
    "${SKILL_DIR}/.venv/bin/python3" -m pip install --disable-pip-version-check -r "${SKILL_DIR}/requirements-asr.txt"
  fi
fi

export PATH="${HOME}/.local/bin:${HOME}/.deno/bin:${PATH}"
if [ "$APPLY" -eq 1 ]; then
  bash "${SKILL_DIR}/scripts/doctor.sh"
  doctor_status=$?
  if [ "$REACH_FAIL" -ne 0 ]; then
    printf 'bootstrap: agent-reach install failed\n' >&2
    exit 1
  fi
  exit "$doctor_status"
else
  bash "${SKILL_DIR}/scripts/doctor.sh" || true
  printf 'bootstrap: dry-run, nothing installed\n'
  exit 0
fi
