#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/lib/venv.sh"

cd "$ROOT"
ensure_venv "$ROOT"

"$ROOT/functions/venv/bin/python" "$ROOT/scripts/seed-emulator.py"
