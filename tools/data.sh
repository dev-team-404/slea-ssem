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
    src="${2:-$DEFAULT_S3}"
    dest="${3:-$DEFAULT_DATASET}"
    echo "⬇️  Syncing $src → $dest (parquet only)..."
    if command -v aws >/dev/null 2>&1; then
      aws s3 sync "$src" "$dest" --exclude "*" --include "*.parquet" --only-show-errors
      echo "✅ Sync complete"
    else
      echo "❌ aws CLI not found. Install awscli or edit tools/data.sh"
      exit 1
    fi
    ;;

  validate)
    path="${2:-$DEFAULT_DATASET}"
    if [ -f "scripts/validate_dataset.py" ]; then
      $PY_RUN python scripts/validate_dataset.py "$path"
    else
      echo "❌ scripts/validate_dataset.py not found"
      echo "Create this script or customize tools/data.sh"
      exit 1
    fi
    ;;

  *)
    cat <<'HELP'
Usage: ./tools/data.sh <command> [args]

Commands:
  pull-local [s3://...] [./data]  Sync parquet data from S3
  validate [./data]               Validate dataset

Tips:
  - Edit DEFAULT_S3 and DEFAULT_DATASET in this file
  - Create scripts/validate_dataset.py for your validation logic

See CLAUDE.md for more.
HELP
    ;;
esac
