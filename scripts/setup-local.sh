#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/lib/venv.sh"

cd "$ROOT"
ensure_venv "$ROOT"

echo ""
echo "==> Setup complete"
echo ""
echo "Activate the venv in your shell:"
echo "  source functions/venv/bin/activate"
echo ""
echo "Start emulators:  firebase emulators:start"
echo "Run unit tests:   ./scripts/test.sh unit"
echo "Run all tests:    ./scripts/test.sh all"
