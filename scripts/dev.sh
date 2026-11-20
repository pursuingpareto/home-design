#!/usr/bin/env bash
# Run the app locally with one command: the API and the web app together. Ctrl+C stops both.
#
#   scripts/dev.sh            # PostgreSQL database "homedesign" (created and migrated if needed)
#   scripts/dev.sh --memory   # in-memory store: nothing is saved when you stop
#   scripts/dev.sh --open     # also open the browser (combine with --memory if you like)
#   scripts/dev.sh --reset    # drop and recreate the local database first (needed after a model
#                             # schema change: older projects are not migrated before release, D055)
#
# Then open http://localhost:5173 and sign in with: dev-token
#
# Optional environment overrides:
#   HOMEDESIGN_DATABASE_URL  (default postgresql:///homedesign)
#   HOMEDESIGN_DEV_TOKENS    (default dev-token=00000000-0000-4000-8000-000000000001)
#   HOMEDESIGN_API_PORT      (default 8000)     HOMEDESIGN_UI_PORT (default 5173)
#
# The preview-signing key is generated once and kept in .dev/preview-key (git-ignored), so open
# previews survive restarts. Development only: never use these tokens or this key in production.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

STORE=postgres
OPEN=false
RESET=false
for arg in "$@"; do
  case "$arg" in
    --memory) STORE=memory ;;
    --open) OPEN=true ;;
    --reset) RESET=true ;;
    -h | --help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $arg (try --help)" >&2; exit 2 ;;
  esac
done

API_PORT="${HOMEDESIGN_API_PORT:-8000}"
UI_PORT="${HOMEDESIGN_UI_PORT:-5173}"
DATABASE_URL="${HOMEDESIGN_DATABASE_URL:-postgresql:///homedesign}"
TOKENS="${HOMEDESIGN_DEV_TOKENS:-dev-token=00000000-0000-4000-8000-000000000001}"
FIRST_TOKEN="${TOKENS%%=*}"

say() { printf '\033[1m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# --- prerequisites --------------------------------------------------------------------------------
command -v uv > /dev/null || fail "uv is not installed: https://docs.astral.sh/uv/"
command -v npm > /dev/null || fail "Node.js (npm) is not installed: Node 22 or later is needed."
for port in "$API_PORT" "$UI_PORT"; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN > /dev/null 2>&1; then
    fail "Port $port is already in use. Stop whatever is using it (maybe an earlier run), or set HOMEDESIGN_API_PORT / HOMEDESIGN_UI_PORT."
  fi
done

say "Backend dependencies"
(cd "$ROOT/backend" && uv sync --locked --quiet)
if [ ! -d "$ROOT/frontend/node_modules" ] || [ "$ROOT/frontend/package-lock.json" -nt "$ROOT/frontend/node_modules/.package-lock.json" ]; then
  say "Frontend dependencies (npm ci)"
  (cd "$ROOT/frontend" && npm ci --no-audit --no-fund --silent)
fi

# --- preview key (stable across restarts) -----------------------------------------------------------
KEY_FILE="$ROOT/.dev/preview-key"
if [ ! -s "$KEY_FILE" ]; then
  mkdir -p "$ROOT/.dev"
  (umask 077 && openssl rand -hex 32 > "$KEY_FILE")
  say "Generated a local preview key in .dev/preview-key"
fi
export HOMEDESIGN_PREVIEW_KEY="$(cat "$KEY_FILE")"
export HOMEDESIGN_DEV_TOKENS="$TOKENS"

# --- store ------------------------------------------------------------------------------------------
if [ "$STORE" = memory ]; then
  export HOMEDESIGN_STORE=memory
  say "Store: in memory (projects are lost when you stop)"
else
  command -v psql > /dev/null || fail "PostgreSQL client tools not found. Install PostgreSQL, or run: scripts/dev.sh --memory"
  DB_NAME="$(cd "$ROOT/backend" && uv run python -c 'import sys; from psycopg.conninfo import conninfo_to_dict; print(conninfo_to_dict(sys.argv[1]).get("dbname") or "")' "$DATABASE_URL")"
  if [ "$RESET" = true ]; then
    [ -n "$DB_NAME" ] || fail "Cannot tell which database to reset from $DATABASE_URL."
    say "Resetting database $DB_NAME (all local projects are deleted)"
    dropdb --if-exists "$DB_NAME" || fail "Could not drop database $DB_NAME. Is it in use, or is PostgreSQL stopped?"
  fi
  if ! psql "$DATABASE_URL" -Atqc 'select 1' > /dev/null 2>&1; then
    [ -n "$DB_NAME" ] || fail "Cannot reach $DATABASE_URL. Is PostgreSQL running? (Or run: scripts/dev.sh --memory)"
    say "Creating database $DB_NAME"
    createdb "$DB_NAME" 2> /dev/null || fail "Could not create database $DB_NAME. Is PostgreSQL running? (Or run: scripts/dev.sh --memory)"
  fi
  say "Migrating $DATABASE_URL"
  (cd "$ROOT/backend" && uv run python -m homedesign.project.migrate "$DATABASE_URL" > /dev/null) \
    || fail "Migration refused or failed (see above). After a model schema change, run: scripts/dev.sh --reset"
  export HOMEDESIGN_STORE=postgres HOMEDESIGN_DATABASE_URL="$DATABASE_URL"
  say "Store: PostgreSQL ($DATABASE_URL); projects are kept between runs"
fi

# --- run both; Ctrl+C stops both --------------------------------------------------------------------
PIDS=()
cleanup() {
  trap - INT TERM EXIT
  echo
  say "Stopping"
  # Each server runs in its own process group (set -m below), so this also stops uvicorn's reloader
  # worker and the node process behind npx.
  for pid in ${PIDS[@]+"${PIDS[@]}"}; do kill -TERM -- "-$pid" 2> /dev/null || kill -TERM "$pid" 2> /dev/null || true; done
  wait 2> /dev/null || true
}
trap cleanup INT TERM EXIT
set -m # job control: each background server gets its own process group

(cd "$ROOT/backend" && exec uv run uvicorn homedesign.api.app:create_app --factory --host 127.0.0.1 --port "$API_PORT" --reload --reload-dir src) &
PIDS+=($!)
(cd "$ROOT/frontend" && HOMEDESIGN_API_URL="http://127.0.0.1:$API_PORT" HOMEDESIGN_UI_PORT="$UI_PORT" exec npx vite --host 127.0.0.1 --clearScreen false) &
PIDS+=($!)

URL="http://localhost:$UI_PORT"
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$API_PORT/openapi.json" > /dev/null 2>&1 && curl -fsS "http://127.0.0.1:$UI_PORT" > /dev/null 2>&1; then
    echo
    say "Ready: open $URL and sign in with: $FIRST_TOKEN"
    say "API docs: http://127.0.0.1:$API_PORT/docs   ·   Press Ctrl+C to stop both."
    echo
    if [ "$OPEN" = true ]; then open "$URL" 2> /dev/null || xdg-open "$URL" 2> /dev/null || true; fi
    break
  fi
  sleep 0.5
done

# Exit (and stop the other) as soon as either server exits. (Polling: macOS bash 3.2 has no `wait -n`.)
while kill -0 "${PIDS[0]}" 2> /dev/null && kill -0 "${PIDS[1]}" 2> /dev/null; do sleep 1; done
say "A server stopped; shutting down the other."
