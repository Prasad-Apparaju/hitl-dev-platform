#!/usr/bin/env bash
# Run all HITL convention checks.
#
# Options:
#   --only semgrep|manifest|mermaid   Run a subset of checks
#   --strict                          Exit non-zero if any check was skipped/unavailable

set -euo pipefail

ONLY="all"
STRICT=false

for arg in "$@"; do
  case "$arg" in
    --only) ;;
    semgrep|manifest|mermaid) ONLY="$arg" ;;
    --strict) STRICT=true ;;
  esac
done

# Allow --only <value> positional form
if [[ "${1:-}" == "--only" && -n "${2:-}" ]]; then
  ONLY="$2"
fi

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

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

skip_check() {
  local name="$1"
  local reason="$2"
  echo "  SKIP: $name — $reason"
  SKIP_COUNT=$((SKIP_COUNT + 1))
}

echo ""
echo "=== HITL Convention Checks ==="
echo ""

if [[ "$ONLY" == "all" || "$ONLY" == "semgrep" ]]; then
  echo "--- Semgrep (code conventions) ---"
  if ! command -v semgrep &>/dev/null; then
    skip_check "semgrep" "not installed (pip install semgrep  OR  brew install semgrep)"
  elif [[ ! -d ".semgrep" ]]; then
    skip_check "semgrep" "no .semgrep/ directory — copy from hitl-dev-platform/.semgrep/"
  else
    run_check "semgrep scan" "semgrep scan --config .semgrep/ --error"
  fi
  echo ""
fi

if [[ "$ONLY" == "all" || "$ONLY" == "manifest" ]]; then
  echo "--- Manifest drift ---"
  if [[ ! -f "ci/manifest-drift/check_manifest_drift.py" ]]; then
    skip_check "manifest drift" "ci/manifest-drift/check_manifest_drift.py not found — copy from hitl-dev-platform/ci/manifest-drift/"
  else
    SOURCE_DIRS=""
    [[ -d "app" ]] && SOURCE_DIRS="$SOURCE_DIRS app/"
    [[ -d "src" ]] && SOURCE_DIRS="$SOURCE_DIRS src/"
    if [[ -z "$SOURCE_DIRS" ]]; then
      skip_check "manifest drift" "no app/ or src/ directory found"
    else
      run_check "manifest drift" "python ci/manifest-drift/check_manifest_drift.py --source-dirs $SOURCE_DIRS"
    fi
  fi
  echo ""
fi

if [[ "$ONLY" == "all" || "$ONLY" == "mermaid" ]]; then
  echo "--- Mermaid br tags ---"
  if [[ ! -f "scripts/fix_mermaid_br_tags.py" ]]; then
    skip_check "mermaid br tags" "scripts/fix_mermaid_br_tags.py not found — copy from hitl-dev-platform/scripts/"
  elif [[ ! -d "docs" ]]; then
    skip_check "mermaid br tags" "no docs/ directory found"
  else
    run_check "mermaid br tags" "find docs/ -name '*.md' -exec python scripts/fix_mermaid_br_tags.py --check {} +"
  fi
  echo ""
fi

echo "=== Results: $PASS_COUNT passed, $FAIL_COUNT failed, $SKIP_COUNT skipped ==="
echo ""

if [[ $FAIL_COUNT -gt 0 ]]; then
  echo "Convention violations found. Fix before creating the PR."
  exit 1
fi

if [[ $SKIP_COUNT -gt 0 && $PASS_COUNT -eq 0 ]]; then
  echo "All checks were skipped — no conventions verified."
  echo "Install missing tools or add source/docs directories before using this as a PR gate."
  exit 1
fi

exit 0
