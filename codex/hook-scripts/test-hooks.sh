#!/usr/bin/env bash
# Smoke tests for check-hitl-context.sh and check-domain-boundary.sh.
# Verifies both Claude-style (Edit/Write) and Codex-style (apply_patch) inputs.
#
# Usage: bash codex/hook-scripts/test-hooks.sh
# Run from the platform repo root.

# No set -e or pipefail: tests intentionally run commands that exit non-zero.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PASS=0
FAIL=0

# Resolve script locations: installed target has them in $SCRIPT_DIR;
# platform repo has them in hooks/ (copied to target during install).
resolve_script() {
  local name="$1"
  if [[ -f "$SCRIPT_DIR/$name" ]]; then
    echo "$SCRIPT_DIR/$name"
  elif [[ -f "$PLATFORM_ROOT/hooks/$name" ]]; then
    echo "$PLATFORM_ROOT/hooks/$name"
  else
    echo ""
  fi
}

assert_exit() {
  local desc="$1"
  local expected="$2"
  local actual="$3"
  if [[ "$actual" == "$expected" ]]; then
    echo "  PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $desc (expected exit $expected, got $actual)"
    FAIL=$((FAIL + 1))
  fi
}

assert_stderr_contains() {
  local desc="$1"
  local pattern="$2"
  local output="$3"
  if echo "$output" | grep -q "$pattern"; then
    echo "  PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $desc (expected stderr to contain '$pattern')"
    echo "        got: $output"
    FAIL=$((FAIL + 1))
  fi
}

TMPDIR_TEST=$(mktemp -d)
trap "rm -rf $TMPDIR_TEST" EXIT
pushd "$TMPDIR_TEST" > /dev/null
git init -q

CONTEXT_SCRIPT=$(resolve_script "check-hitl-context.sh")
BOUNDARY_SCRIPT=$(resolve_script "check-domain-boundary.sh")

if [[ -z "$CONTEXT_SCRIPT" || -z "$BOUNDARY_SCRIPT" ]]; then
  echo "ERROR: hook scripts not found in $SCRIPT_DIR or $PLATFORM_ROOT/hooks/" >&2
  exit 1
fi

echo ""
echo "=== check-hitl-context.sh ==="
echo ""

# --- No context file ---

# T1: apply_patch adding a source file — no context → block (exit 2)
INPUT='{"hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Add File: src/app.py\n+print(1)\n*** End Patch\n"}}'
echo "$INPUT" | bash "$CONTEXT_SCRIPT" 2>/dev/null; R=$?
assert_exit "apply_patch adds src/app.py, no context → exit 2" 2 $R

# T2: apply_patch editing a docs file — no context → allow (exit 0)
INPUT='{"hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Update File: docs/design.md\n-old\n+new\n*** End Patch\n"}}'
echo "$INPUT" | bash "$CONTEXT_SCRIPT" 2>/dev/null; R=$?
assert_exit "apply_patch edits docs/design.md, no context → exit 0" 0 $R

# T3: apply_patch renaming a source file — no context → block (exit 2)
INPUT='{"hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Rename File: src/old.py => src/new.py\n*** End Patch\n"}}'
echo "$INPUT" | bash "$CONTEXT_SCRIPT" 2>/dev/null; R=$?
assert_exit "apply_patch renames src/old.py => src/new.py, no context → exit 2" 2 $R

# T4: apply_patch touching only config files — no context → allow (exit 0)
INPUT='{"hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Update File: pyproject.toml\n-x=1\n+x=2\n*** End Patch\n"}}'
echo "$INPUT" | bash "$CONTEXT_SCRIPT" 2>/dev/null; R=$?
assert_exit "apply_patch edits pyproject.toml, no context → exit 0" 0 $R

# T5: Claude-style Edit source file — no context → block (exit 2)
INPUT='{"tool_name":"Edit","tool_input":{"file_path":"src/app.py","old_string":"a","new_string":"b"}}'
echo "$INPUT" | bash "$CONTEXT_SCRIPT" 2>/dev/null; R=$?
assert_exit "Claude Edit src/app.py, no context → exit 2" 2 $R

# T6: Claude-style Edit README.md — no context → allow (exit 0)
INPUT='{"tool_name":"Edit","tool_input":{"file_path":"README.md","old_string":"a","new_string":"b"}}'
echo "$INPUT" | bash "$CONTEXT_SCRIPT" 2>/dev/null; R=$?
assert_exit "Claude Edit README.md, no context → exit 0" 0 $R

# --- With context file ---

mkdir -p .hitl
cat > .hitl/current-change.yaml << 'YAML'
change_id: GH-1
tier: 2
status: implementation-approved
manifest:
  path: docs/system-manifest.yaml
  domain: app
allowed_paths:
  - src/app.py
YAML

# T7: apply_patch adding a source file — valid context → allow (exit 0)
INPUT='{"hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Add File: src/app.py\n+print(1)\n*** End Patch\n"}}'
echo "$INPUT" | bash "$CONTEXT_SCRIPT" 2>/dev/null; R=$?
assert_exit "apply_patch adds src/app.py, valid context → exit 0" 0 $R

# T8: apply_patch with multiple files (source + docs) — valid context → allow (exit 0)
INPUT='{"hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Update File: src/app.py\n-a\n+b\n*** Update File: docs/guide.md\n-x\n+y\n*** End Patch\n"}}'
echo "$INPUT" | bash "$CONTEXT_SCRIPT" 2>/dev/null; R=$?
assert_exit "apply_patch mixed source+docs, valid context → exit 0" 0 $R

echo ""
echo "=== check-domain-boundary.sh ==="
echo ""

# T9: apply_patch editing src/app.py (in allowed_paths) → no warning
INPUT='{"hook_event_name":"PostToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Update File: src/app.py\n-a\n+b\n*** End Patch\n"}}'
OUTPUT=$(echo "$INPUT" | bash "$BOUNDARY_SCRIPT" 2>&1); R=$?
assert_exit "apply_patch src/app.py in allowed_paths → exit 0" 0 $R

# T10: apply_patch editing src/other.py (outside allowed_paths) → boundary warning
INPUT='{"hook_event_name":"PostToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Update File: src/other.py\n-a\n+b\n*** End Patch\n"}}'
OUTPUT=$(echo "$INPUT" | bash "$BOUNDARY_SCRIPT" 2>&1)
assert_stderr_contains "apply_patch src/other.py outside allowed_paths → boundary warning" "DOMAIN BOUNDARY WARNING" "$OUTPUT"

# T11: Claude-style Edit src/other.py (outside allowed_paths) → boundary warning
INPUT='{"tool_name":"Edit","tool_input":{"file_path":"src/other.py","old_string":"a","new_string":"b"}}'
OUTPUT=$(echo "$INPUT" | bash "$BOUNDARY_SCRIPT" 2>&1)
assert_stderr_contains "Claude Edit src/other.py outside allowed_paths → boundary warning" "DOMAIN BOUNDARY WARNING" "$OUTPUT"

# T12: apply_patch moves src/old.py → src/new.py; new path is outside allowed_paths → boundary warning
INPUT='{"hook_event_name":"PostToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Update File: src/old.py\n*** Move to: src/new.py\n*** End Patch\n"}}'
OUTPUT=$(echo "$INPUT" | bash "$BOUNDARY_SCRIPT" 2>&1)
assert_stderr_contains "apply_patch Move to destination src/new.py outside allowed_paths → boundary warning" "DOMAIN BOUNDARY WARNING" "$OUTPUT"

popd > /dev/null

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
echo ""
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
