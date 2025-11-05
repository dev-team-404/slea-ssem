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
