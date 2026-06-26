#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/gmail-addon"

if ! command -v clasp &>/dev/null; then
  echo "Error: clasp is not installed. Run: npm install -g @google/clasp"
  exit 1
fi

echo "==> Pushing Gmail add-on"
clasp push

echo "==> Add-on code pushed"
echo ""
echo "Next (one-time, operator only):"
echo "  1. Apps Script editor → Deploy → Test deployments (if not done)"
echo "  2. Run function logOAuthClientId → copy aud from Executions log"
echo "  3. firebase functions:secrets:set APPS_SCRIPT_OAUTH_CLIENT_ID"
echo "  4. ./scripts/deploy.sh"
echo ""
echo "See docs/installing/INSTALL.md § Link add-on to backend"
