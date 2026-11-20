#!/usr/bin/env bash
# Run every check CI runs, in the same order (TEST-001 §8). Stops at the first failure.
#
# Usage (from anywhere in the repository):  scripts/check.sh
# Needs: uv, Node 22+, and a local PostgreSQL for the backend tests (see backend/README.md).

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CURRENT="setup"
trap 'echo; echo "✗ check.sh failed during: ${CURRENT}" >&2' ERR

step() {
  CURRENT="$1"
  echo
  echo "==> ${CURRENT}"
}

step "backend: install (uv sync --locked)"
cd "$ROOT/backend"
uv sync --locked

step "backend: tests (pytest, PostgreSQL and in-memory stores)"
uv run pytest

step "backend: committed schemas are current"
uv run python -m homedesign.model.schema_export --check

step "backend: Reference House 001 fixture and template are current"
uv run python -m homedesign.timber.fixture --check

step "backend: frontend fixtures are current"
uv run python -m homedesign.api.ui_fixtures --check

step "vectors: the ECMAScript oracle reproduces the committed vectors"
cd "$ROOT"
node tests/vectors/jcs/generate.mjs > /dev/null
git diff --exit-code -- tests/vectors/

step "frontend: install (npm ci)"
cd "$ROOT/frontend"
npm ci --no-audit --no-fund

step "frontend: generated API types are current"
npm run -s check:api

step "frontend: type-check"
npm run -s typecheck

step "frontend: unit and component tests (Vitest)"
npm test --silent

step "frontend: production build"
npm run -s build

step "end to end (Playwright, Chromium)"
npx playwright test

echo
echo "✓ All checks passed."
