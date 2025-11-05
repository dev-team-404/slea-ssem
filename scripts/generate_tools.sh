#!/usr/bin/env bash
#
# scripts/generate_tools.sh
# Auto-generates tools/*.sh based on project configuration
# Run after cloning: ./scripts/generate_tools.sh
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="$ROOT_DIR/tools"
SCRIPTS_DIR="$ROOT_DIR/scripts"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}✓${NC} $*"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $*"; }
log_error() { echo -e "${RED}✗${NC} $*"; }

# Detect project config
echo "🔍 Detecting project configuration..."

# Read from pyproject.toml
if [ ! -f "$ROOT_DIR/pyproject.toml" ]; then
    log_error "pyproject.toml not found"
    exit 1
fi

PROJECT_NAME=$(grep '^name = ' "$ROOT_DIR/pyproject.toml" | head -1 | sed 's/.*name = "\([^"]*\)".*/\1/')
PYTHON_VERSION=$(grep '^requires-python' "$ROOT_DIR/pyproject.toml" | sed 's/.*>= *"\([0-9.]*\)".*/\1/')

# Detect package manager
if [ -f "$ROOT_DIR/uv.lock" ]; then
    PKG_MANAGER="uv"
elif [ -f "$ROOT_DIR/poetry.lock" ]; then
    PKG_MANAGER="poetry"
elif [ -f "$ROOT_DIR/requirements.txt" ]; then
    PKG_MANAGER="pip"
else
    PKG_MANAGER="uv"
fi

# Detect framework
IS_FASTAPI=false
IS_DJANGO=false
UVICORN_ENTRY=""
MANAGE_PY="manage.py"

if grep -q "fastapi" "$ROOT_DIR/pyproject.toml" 2>/dev/null; then
    IS_FASTAPI=true
    # Try to find the entry point
    if [ -f "$ROOT_DIR/src/backend/main.py" ]; then
        UVICORN_ENTRY="src.backend.main:app"
    elif [ -f "$ROOT_DIR/src/main.py" ]; then
        UVICORN_ENTRY="src.main:app"
    fi
elif grep -q "django" "$ROOT_DIR/pyproject.toml" 2>/dev/null; then
    IS_DJANGO=true
fi

# Detect database & migration tools
USE_ALEMBIC=false
USE_DJANGO_MIGRATIONS=false

if grep -q "alembic" "$ROOT_DIR/pyproject.toml" 2>/dev/null; then
    USE_ALEMBIC=true
elif [ "$IS_DJANGO" = true ]; then
    USE_DJANGO_MIGRATIONS=true
fi

# Check for data sources
HAS_DATA_SOURCES=false
if [ -d "$ROOT_DIR/data" ] || grep -q "data/" "$ROOT_DIR/README.md" 2>/dev/null; then
    HAS_DATA_SOURCES=true
fi

log_info "Project: $PROJECT_NAME (Python $PYTHON_VERSION)"
log_info "Package Manager: $PKG_MANAGER"
[ "$IS_FASTAPI" = true ] && log_info "Framework: FastAPI (Entry: $UVICORN_ENTRY)"
[ "$IS_DJANGO" = true ] && log_info "Framework: Django"
[ "$USE_ALEMBIC" = true ] && log_info "Migrations: Alembic"
[ "$USE_DJANGO_MIGRATIONS" = true ] && log_info "Migrations: Django"

# Generate tools directory if not exists
mkdir -p "$TOOLS_DIR"
mkdir -p "$SCRIPTS_DIR"

# Generate tools/dev.sh
echo ""
echo "📝 Generating tools/dev.sh..."

PY_RUN="$PKG_MANAGER run"
if [ "$PKG_MANAGER" = "pip" ]; then
    PY_RUN="python -m"
fi

cat > "$TOOLS_DIR/dev.sh" <<'EOF'
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
EOF

chmod +x "$TOOLS_DIR/dev.sh"
log_info "Created tools/dev.sh"

# Generate tools/data.sh
echo ""
echo "📝 Generating tools/data.sh..."

cat > "$TOOLS_DIR/data.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# slea-ssem data sync tool
# Currently no external data sources (configure as needed)
PY_RUN="uv run"
DEFAULT_DATASET="./data"
# DEFAULT_S3="s3://your-bucket/path"  # Configure when data sources added

cmd="${1:-help}"

case "$cmd" in
  pull-local)
    src="${2:-}"
    dest="${3:-$DEFAULT_DATASET}"
    if [ -z "$src" ]; then
      echo "❌ Usage: ./tools/data.sh pull-local <source> [dest]"
      exit 1
    fi
    echo "⬇️  Syncing $src → $dest..."
    if command -v aws >/dev/null 2>&1; then
      aws s3 sync "$src" "$dest" --exclude "*" --include "*.parquet" --only-show-errors
      echo "✅ Sync complete"
    else
      echo "❌ aws CLI not found. Install awscli or customize tools/data.sh"
      exit 1
    fi
    ;;

  validate)
    path="${2:-$DEFAULT_DATASET}"
    if [ -f "scripts/validate_dataset.py" ]; then
      $PY_RUN python scripts/validate_dataset.py "$path"
    else
      echo "ℹ️  scripts/validate_dataset.py not found"
      echo "Create this script or customize tools/data.sh"
      exit 0
    fi
    ;;

  *)
    cat <<'HELP'
Usage: ./tools/data.sh <command> [args]

Commands:
  pull-local <src> [dest]  Sync data from S3 or local path
  validate [path]          Validate dataset

Tips:
  - Configure DEFAULT_DATASET and data sources in this file
  - Create scripts/validate_dataset.py for validation logic

See CLAUDE.md for more.
HELP
    ;;
esac
EOF

chmod +x "$TOOLS_DIR/data.sh"
log_info "Created tools/data.sh"

# Generate tools/release.sh (simple version)
echo ""
echo "📝 Generating tools/release.sh..."

cat > "$TOOLS_DIR/release.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Simple semver release: tag, optional build
# Usage: ./tools/release.sh patch|minor|major

bump="${1:-}"
[ -z "$bump" ] && { echo "Usage: $0 {patch|minor|major}"; exit 1; }

# Check clean tree
if ! git diff --quiet 2>/dev/null; then
  echo "❌ Uncommitted changes. Commit or stash first."
  exit 1
fi

# Get current semver tag (fallback to 0.0.0)
current="$(git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0")"
IFS='.' read -r MAJ MIN PAT <<<"$current"
MAJ=${MAJ:-0}
MIN=${MIN:-0}
PAT=${PAT:-0}

case "$bump" in
  patch) PAT=$((PAT+1));;
  minor) MIN=$((MIN+1)); PAT=0;;
  major) MAJ=$((MAJ+1)); MIN=0; PAT=0;;
  *) echo "❌ Unknown bump: $bump"; exit 1;;
esac

new="$MAJ.$MIN.$PAT"

echo "📝 Tagging $current → $new"
git tag -a "$new" -m "Release $new"
git push --follow-tags

echo "✅ Release $new complete"
echo "Next: Verify build/deployment pipelines"
EOF

chmod +x "$TOOLS_DIR/release.sh"
log_info "Created tools/release.sh"

# Generate tools/commit.sh
echo ""
echo "📝 Generating tools/commit.sh..."

cat > "$TOOLS_DIR/commit.sh" <<'EOF'
#!/usr/bin/env bash
# tools/commit.sh
# Interactive commit with summary & automatic message generation
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Check if there are changes
if git diff --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo "❌ No changes to commit"
  exit 1
fi

echo "📊 Changes to commit:"
echo ""
git status -s
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
git diff --stat
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Ask for commit type
echo "Select commit type:"
PS3="Choose (1-6): "
select type in "feat" "fix" "chore" "refactor" "test" "docs"; do
  case $type in
    feat|fix|chore|refactor|test|docs)
      COMMIT_TYPE=$type
      break
      ;;
    *)
      echo "Invalid choice"
      ;;
  esac
done

# Ask for scope (optional)
read -r -p "Scope (optional, e.g., 'tools', 'backend', 'api'): " SCOPE || SCOPE=""
if [ -n "$SCOPE" ]; then
  SCOPE="($SCOPE): "
else
  SCOPE=": "
fi

# Ask for short description
read -r -p "Short description (required): " DESCRIPTION || true
if [ -z "$DESCRIPTION" ]; then
  echo "❌ Description required"
  exit 1
fi

# Ask for body
echo ""
echo "Detailed message (optional, press Ctrl+D when done, or Enter to skip):"
read -r -p "> " -t 2 BODY || BODY=""

# Preview commit message
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Commit message preview:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "$COMMIT_TYPE$SCOPE$DESCRIPTION"
if [ -n "$BODY" ]; then
  echo ""
  echo "$BODY"
fi
echo ""
echo ""
echo "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
echo ""
echo "Co-Authored-By: Claude <noreply@anthropic.com>"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Confirm
read -r -p "Proceed with commit? (y/N): " CONFIRM || CONFIRM="N"
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
  echo "Cancelled."
  exit 0
fi

# Stage all changes
git add -A

# Create commit
if [ -z "$BODY" ]; then
  git commit -m "$(cat <<COMMIT_EOF
$COMMIT_TYPE$SCOPE$DESCRIPTION

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
COMMIT_EOF
)"
else
  git commit -m "$(cat <<COMMIT_EOF
$COMMIT_TYPE$SCOPE$DESCRIPTION

$BODY

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
COMMIT_EOF
)"
fi

echo ""
echo "✅ Commit created!"
echo ""

# Ask about push
read -r -p "Push to remote? (y/N): " PUSH || PUSH="N"
if [ "$PUSH" = "y" ] || [ "$PUSH" = "Y" ]; then
  git push
  echo "✅ Pushed!"
else
  echo "💡 Tip: Push later with: git push"
fi
EOF

chmod +x "$TOOLS_DIR/commit.sh"
log_info "Created tools/commit.sh"

# All done!
echo ""
log_info "All tool wrappers generated successfully!"
echo ""
echo "📋 Next steps:"
echo "  1. Review generated scripts: ls -la tools/"
echo "  2. Test a command: ./tools/dev.sh help"
echo "  3. Make first commit: ./tools/commit.sh"
echo ""
echo "💡 Edit tools/*.sh to customize for your project"
