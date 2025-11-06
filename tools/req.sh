#!/usr/bin/env bash
# tools/req.sh
# REQ-based development automation (Phase 1-4 workflow)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Validate input
if [ $# -lt 1 ]; then
  cat <<'HELP'
Usage: ./tools/req.sh <REQ-ID> [phase]

Examples:
  ./tools/req.sh REQ-B-A2-Edit-1          # Auto-run Phase 1-4
  ./tools/req.sh REQ-B-A2-Edit-1 spec     # Phase 1: Specification
  ./tools/req.sh REQ-B-A2-Edit-1 tests    # Phase 2: Test Design
  ./tools/req.sh REQ-B-A2-Edit-1 impl     # Phase 3: Implementation
  ./tools/req.sh REQ-B-A2-Edit-1 summary  # Phase 4: Summary

Note: Full workflow pauses after Phase 1 & 2 for your review.
HELP
  exit 1
fi

REQ_ID="$1"
PHASE="${2:-all}"

# Extract REQ details from feature_requirement_mvp1.md
extract_req() {
  local req_id="$1"
  if grep -q "^$req_id" docs/feature_requirement_mvp1.md; then
    echo "✅ Found $req_id in feature_requirement_mvp1.md"
  else
    echo "❌ REQ ID not found in feature_requirement_mvp1.md"
    exit 1
  fi
}

run_phase_1() {
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Phase 1️⃣: SPECIFICATION"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "[Claude will]"
  echo "- Extract REQ block: $REQ_ID"
  echo "- Summarize intent, constraints, performance goals"
  echo "- Define: Location, Signature, Behavior, Dependencies, Non-functional"
  echo "- Present spec for your review"
  echo ""
  echo "🛑 PAUSE: You must approve spec before Phase 2 proceeds"
  echo ""
}

run_phase_2() {
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Phase 2️⃣: TEST DESIGN (TDD)"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "[Claude will]"
  echo "- Design 4-5 test cases (happy path, validation, edge cases)"
  echo "- Include REQ ID in docstrings: # REQ: $REQ_ID"
  echo "- Show test file location: tests/<domain>/test_<feature>.py"
  echo "- Present test plan for your review"
  echo ""
  echo "🛑 PAUSE: You must approve tests before Phase 3 proceeds"
  echo ""
}

run_phase_3() {
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Phase 3️⃣: IMPLEMENTATION"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "[Claude will]"
  echo "- Implement minimal code satisfying spec + tests"
  echo "- Run: tox -e style && pytest tests/<domain>/test_<feature>.py"
  echo "- Report validation results"
  echo ""
}

run_phase_4() {
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Phase 4️⃣: SUMMARY & COMMIT"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "[Claude will]"
  echo "- List modified files + rationale"
  echo "- Show test results (all pass?)"
  echo "- Create traceability table: REQ → Spec → Tests → Code"
  echo "- Create git commit: ./tools/commit.sh"
  echo ""
}

# Main
extract_req "$REQ_ID"
echo ""

case "$PHASE" in
  spec|1)
    run_phase_1
    ;;
  tests|2)
    run_phase_1
    echo ""
    run_phase_2
    ;;
  impl|3)
    run_phase_1
    echo ""
    run_phase_2
    echo ""
    run_phase_3
    ;;
  summary|4)
    run_phase_4
    ;;
  all|*)
    run_phase_1
    echo ""
    read -r -p "✅ Spec approved? (y/N): " APPROVE1 || APPROVE1="N"
    if [ "$APPROVE1" != "y" ] && [ "$APPROVE1" != "Y" ]; then
      echo "❌ Spec rejected. Exiting."
      exit 1
    fi
    echo ""
    run_phase_2
    echo ""
    read -r -p "✅ Tests approved? (y/N): " APPROVE2 || APPROVE2="N"
    if [ "$APPROVE2" != "y" ] && [ "$APPROVE2" != "Y" ]; then
      echo "❌ Tests rejected. Exiting."
      exit 1
    fi
    echo ""
    run_phase_3
    echo ""
    run_phase_4
    echo ""
    read -r -p "📝 Create commit? (y/N): " DO_COMMIT || DO_COMMIT="N"
    if [ "$DO_COMMIT" = "y" ] || [ "$DO_COMMIT" = "Y" ]; then
      ./tools/commit.sh
    fi
    ;;
esac

echo ""
echo "For details, see: CLAUDE.md → REQ-Based Development Workflow"
echo ""
