#!/usr/bin/env bash
set -euo pipefail

# slea-ssem development tool
# Auto-filled by generator (editable)
PY_RUN="uv run"
PY_TEST="uv run pytest -q"
UVICORN_ENTRY="src.backend.main:app"
USE_ALEMBIC=true
IS_DJANGO=false
MANAGE_PY="manage.py"
DEFAULT_DATASET="./data"

cmd="${1:-help}"

case "$cmd" in
  up)
    echo "🔧 Starting dev server..."
    if $IS_DJANGO; then
      export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-"config.settings.dev"}
      $PY_RUN python "$MANAGE_PY" migrate
      $PY_RUN python "$MANAGE_PY" runserver 0.0.0.0:8000
    else
      if $USE_ALEMBIC; then
        $PY_RUN alembic upgrade head
      fi
      if [ -n "$UVICORN_ENTRY" ]; then
        APP_ENV=${APP_ENV:-dev} DATASET=${DATASET:-"$DEFAULT_DATASET"} \
        $PY_RUN uvicorn "$UVICORN_ENTRY" --reload --host 0.0.0.0 --port 8000
      else
        echo "❌ No dev server configured. Edit tools/dev.sh to add your start command."
        exit 1
      fi
    fi
    ;;

  test)
    echo "🧪 Running tests..."
    $PY_TEST
    ;;

  fmt|format)
    echo "🖤 Format + lint (tox -e ruff)..."
    if command -v tox >/dev/null 2>&1; then
      tox -e ruff
    else
      echo "❌ tox not found. Install: uv pip install tox"
      exit 1
    fi
    ;;

  shell)
    echo "🐚 Entering project shell..."
    if command -v uv >/dev/null 2>&1; then
      exec uv run bash
    else
      echo "❌ uv not found. Activate virtualenv manually."
      exit 1
    fi
    ;;

  *)
    cat <<'HELP'
Usage: ./tools/dev.sh <command>

Commands:
  up           Start dev server (uvicorn on :8000 + DB init)
  test         Run test suite (pytest)
  format       Format + lint code (tox -e ruff)
  shell        Enter project shell

Tips:
  - Override dataset: DATASET=/path ./tools/dev.sh up
  - Set APP_ENV=dev|staging|prod as needed

See CLAUDE.md for more.
HELP
    ;;
esac
