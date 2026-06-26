#!/usr/bin/env bash
# Shared helpers for the project Python virtual environment.
# Source this file from other scripts: source "$(dirname "$0")/lib/venv.sh"
#
# Firebase Functions runtime (see firebase.json) requires functions/venv to be
# created with the matching Python version and firebase-functions installed there.

VENV_DIR="${VENV_DIR:-functions/venv}"

# Resolve Python executable matching firebase.json runtime (default: python313).
resolve_python_bin() {
  local root="${1:?Project root required}"

  if [ -n "${PYTHON_BIN:-}" ]; then
    echo "$PYTHON_BIN"
    return
  fi

  local runtime
  runtime=$(grep -oE '"runtime": "python[0-9]+"' "$root/firebase.json" 2>/dev/null \
    | head -1 \
    | grep -oE 'python[0-9]+' \
    || echo "python313")

  # python313 -> 3.13
  local version_digits="${runtime#python}"
  local major minor
  major="${version_digits:0:1}"
  minor="${version_digits:1}"

  local candidate="python${major}.${minor}"
  if command -v "$candidate" &>/dev/null; then
    echo "$candidate"
    return
  fi

  echo "Error: $candidate is required (Firebase runtime: $runtime) but was not found." >&2
  echo "" >&2
  echo "Install Python ${major}.${minor}, then recreate the venv:" >&2
  echo "  macOS (Homebrew):  brew install python@${major}.${minor}" >&2
  echo "  pyenv:             pyenv install ${major}.${minor} && pyenv local ${major}.${minor}" >&2
  echo "" >&2
  echo "Or set PYTHON_BIN to your Python ${major}.${minor} executable." >&2
  exit 1
}

venv_needs_recreate() {
  local venv_path="$1"
  local python_bin="$2"

  if [ ! -d "$venv_path" ]; then
    return 0
  fi

  if [ ! -x "$venv_path/bin/python" ]; then
    return 0
  fi

  local expected actual
  expected=$("$python_bin" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  actual=$("$venv_path/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "none")

  [ "$expected" != "$actual" ]
}

ensure_venv() {
  local root="${1:?Project root required}"
  local venv_path="$root/$VENV_DIR"
  local python_bin
  python_bin=$(resolve_python_bin "$root")

  if venv_needs_recreate "$venv_path" "$python_bin"; then
    if [ -d "$venv_path" ]; then
      echo "==> Recreating $VENV_DIR ($python_bin required for Firebase deploy)"
      rm -rf "$venv_path"
    else
      echo "==> Creating virtual environment at $VENV_DIR with $python_bin"
    fi
    "$python_bin" -m venv "$venv_path"
  fi

  # shellcheck disable=SC1091
  source "$venv_path/bin/activate"

  echo "==> Installing Python dependencies into $VENV_DIR ($python_bin)"
  python -m pip install -q --upgrade pip
  python -m pip install -q -r "$root/functions/requirements.txt"
  if [ -f "$root/functions/requirements-dev.txt" ]; then
    python -m pip install -q -r "$root/functions/requirements-dev.txt"
  fi

  if ! python -c "import firebase_functions" 2>/dev/null; then
    echo "Error: firebase-functions is not installed in $VENV_DIR." >&2
    echo "Run: $python_bin -m pip install -r functions/requirements.txt" >&2
    exit 1
  fi
}

venv_python() {
  local root="${1:?Project root required}"
  echo "$root/$VENV_DIR/bin/python"
}
