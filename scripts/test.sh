#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/lib/venv.sh"

MODE="${1:-unit}"

cd "$ROOT"
ensure_venv "$ROOT"

cd functions

case "$MODE" in
  unit)
    pytest tests/unit -v --cov=src --cov-report=term-missing
    ;;
  integration)
    cd "$ROOT"
    firebase emulators:exec --only firestore \
      "cd functions && $ROOT/functions/venv/bin/python -m pytest tests/integration -v"
    ;;
  all)
    pytest tests/unit -v --cov=src --cov-report=term-missing
    cd "$ROOT"
    firebase emulators:exec --only firestore \
      "cd functions && $ROOT/functions/venv/bin/python -m pytest tests/integration -v"
    ;;
  lint)
    ruff check src
    ;;
  *)
    echo "Usage: $0 [unit|integration|all|lint]"
    exit 1
    ;;
esac
