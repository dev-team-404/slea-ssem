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
