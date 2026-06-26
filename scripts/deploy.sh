#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/lib/venv.sh"

cd "$ROOT"
ensure_venv "$ROOT"

echo "==> Running unit tests"
"$ROOT/scripts/test.sh" unit

echo ""
echo "==> Deploying to Firebase"
PROJECT_FLAG=""
if [ -n "${FIREBASE_PROJECT_ID:-}" ]; then
  PROJECT_FLAG="--project $FIREBASE_PROJECT_ID"
fi

firebase deploy $PROJECT_FLAG --only firestore:rules,firestore:indexes,functions,hosting

echo ""
echo "==> Deploy complete"
