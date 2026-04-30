#!/usr/bin/env bash
# Run all HITL convention checks. Pass --only semgrep|manifest|mermaid to run a subset.

set -euo pipefail

ONLY="${1:-all}"
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

run_check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" 2>/dev/null; then
    echo "  PASS: $name"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  FAIL: $name"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

echo ""
echo "=== HITL Convention Checks ==="
echo ""

if [[ "$ONLY" == "all" || "$ONLY" == "semgrep" ]]; then
  echo "--- Semgrep (code conventions) ---"
  if ! command -v semgrep &>/dev/null; then
    echo "  SKIP: semgrep not installed. Install with: pip install semgrep  OR  brew install semgrep"
    WARN_COUNT=$((WARN_COUNT + 1))
  elif [[ ! -d ".semgrep" ]]; then
    echo "  SKIP: no .semgrep/ directory in project root"
    WARN_COUNT=$((WARN_COUNT + 1))
  else
    run_check "semgrep scan" "semgrep scan --config .semgrep/ --error"
  fi
  echo ""
fi

if [[ "$ONLY" == "all" || "$ONLY" == "manifest" ]]; then
  echo "--- Manifest drift ---"
  if [[ ! -f "tools/manifest-drift/check_manifest_drift.py" ]]; then
    echo "  SKIP: tools/manifest-drift/check_manifest_drift.py not found"
    WARN_COUNT=$((WARN_COUNT + 1))
  else
    SOURCE_DIRS=""
    [[ -d "app" ]] && SOURCE_DIRS="$SOURCE_DIRS app/"
    [[ -d "src" ]] && SOURCE_DIRS="$SOURCE_DIRS src/"
    if [[ -z "$SOURCE_DIRS" ]]; then
      echo "  SKIP: no app/ or src/ directory found"
      WARN_COUNT=$((WARN_COUNT + 1))
    else
      run_check "manifest drift" "python tools/manifest-drift/check_manifest_drift.py --source-dirs $SOURCE_DIRS"
    fi
  fi
  echo ""
fi

if [[ "$ONLY" == "all" || "$ONLY" == "mermaid" ]]; then
  echo "--- Mermaid br tags ---"
  if [[ ! -f "scripts/fix_mermaid_br_tags.py" ]]; then
    echo "  SKIP: scripts/fix_mermaid_br_tags.py not found"
    WARN_COUNT=$((WARN_COUNT + 1))
  else
    run_check "mermaid br tags" "find docs/ -name '*.md' -exec python scripts/fix_mermaid_br_tags.py --check {} +"
  fi
  echo ""
fi

echo "=== Results: $PASS_COUNT passed, $FAIL_COUNT failed, $WARN_COUNT skipped/warned ==="
echo ""

if [[ $FAIL_COUNT -gt 0 ]]; then
  echo "Convention violations found. Fix before creating the PR."
  exit 1
fi

exit 0
