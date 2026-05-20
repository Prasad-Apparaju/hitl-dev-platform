#!/usr/bin/env bash
# Tests the HITL current_step read/write cycle:
#   1. welcome.sh breadcrumb renders correctly at various step numbers
#   2. sync-step-to-issue.sh hook correctly filters file paths and parses step info
#   3. Edge cases: malformed YAML, missing fields, migration-setup placeholder

set -uo pipefail

PASS=0
FAIL=0
HITL_FILE=".hitl/current-change.yaml"
WELCOME="ai/claude/hooks/welcome.sh"
SYNC_HOOK="ai/claude/hooks/sync-step-to-issue.sh"

pass() { echo "  PASS: $1"; (( PASS++ )) || true; }
fail() { echo "  FAIL: $1"; (( FAIL++ )) || true; }

write_context() {
    mkdir -p .hitl
    cat > "$HITL_FILE" << YAML
change_id: ${1:-GH-99}
tier: ${2:-2}
status: build
manifest:
  domain: payments
current_step:
  number: ${3:-10}
  name: "${4:-AI generates tests (RED)}"
  phase: "${5:-Build}"
YAML
}

# Run welcome.sh capturing output via file redirect (avoids PPID subshell issue)
run_welcome() {
    rm -f /tmp/hitl-welcomed-"$$"
    bash "$WELCOME" > /tmp/hitl_test_out.txt 2>&1
    cat /tmp/hitl_test_out.txt
}

# Simulate the hook input JSON that Claude Code sends for a Write/Edit tool call
hook_input() {
    local file_path="${1:-}"
    printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"},"tool_response":{}}' "$file_path"
}

echo ""
echo "=== HITL current_step read/write tests ==="
echo ""

# ── Breadcrumb tests ──────────────────────────────────────────────────────────

echo "-- Breadcrumb: step in the middle of 32-step workflow --"
write_context "GH-42" 2 14 "Generate code (GREEN)" "Build"
OUT=$(run_welcome)
echo "$OUT" | grep -q "Step 14 / 32: Generate code (GREEN)" \
    && pass "header shows correct step number and name" \
    || fail "header step 14 not found in: $OUT"
echo "$OUT" | grep -q "HITL — Build" \
    && pass "header shows correct phase" \
    || fail "phase 'Build' not found in: $OUT"
echo "$OUT" | grep -q "▶14\." \
    && pass "trail marks step 14 as current" \
    || fail "trail marker ▶14 not found in: $OUT"
echo "$OUT" | grep -q "✓13\." \
    && pass "trail shows prior step as completed" \
    || fail "prior step marker not found"
echo "$OUT" | grep -q "·15\." \
    && pass "trail shows next step as pending" \
    || fail "pending step marker not found"

echo ""
echo "-- Breadcrumb: step 1 (left edge of trail) --"
write_context "GH-42" 2 1 "Create GitHub issue" "Design"
OUT=$(run_welcome)
echo "$OUT" | grep -q "Step 1 / 32" \
    && pass "step 1 header correct" \
    || fail "step 1 header wrong: $OUT"
echo "$OUT" | grep -q "▶1\." \
    && pass "trail marks step 1 as current" \
    || fail "▶1 not found in: $OUT"
# At step 1 there are no prior completed steps — no ✓ markers
echo "$OUT" | grep -qv "✓" \
    && pass "no completed markers at step 1" \
    || fail "unexpected ✓ markers at step 1"

echo ""
echo "-- Breadcrumb: step 32 (right edge of trail) --"
write_context "GH-42" 2 32 "90-day ROI review" "Post-Ship"
OUT=$(run_welcome)
echo "$OUT" | grep -q "Step 32 / 32" \
    && pass "step 32 header correct" \
    || fail "step 32 header wrong: $OUT"
echo "$OUT" | grep -q "▶32\." \
    && pass "trail marks step 32 as current" \
    || fail "▶32 not found in: $OUT"

echo ""
echo "-- Breadcrumb: migration setup phase --"
write_context "migration-setup" 3 3 "Initialize system manifest" "Migration Setup"
OUT=$(run_welcome)
echo "$OUT" | grep -q "HITL — Migration Setup" \
    && pass "migration phase label in header" \
    || fail "Migration Setup label not found: $OUT"
echo "$OUT" | grep -q "change: migration-setup" \
    && pass "migration-setup change_id shown" \
    || fail "migration-setup not shown: $OUT"

echo ""
echo "-- Breadcrumb: migration review phase --"
write_context "GH-55" 3 4 "Write migration brief" "Migration Review"
OUT=$(run_welcome)
echo "$OUT" | grep -q "HITL — Migration Review" \
    && pass "migration review phase label in header" \
    || fail "Migration Review label not found: $OUT"

echo ""
echo "-- Breadcrumb: no context file → static menu --"
rm -f "$HITL_FILE"
rm -f /tmp/hitl-welcomed-"$$"
OUT=$(run_welcome)
echo "$OUT" | grep -q "HITL AI-Driven Development" \
    && pass "static menu shown when no context file" \
    || fail "static menu not shown: $OUT"

echo ""
echo "-- Breadcrumb: context file exists but no current_step → static menu --"
mkdir -p .hitl
printf 'change_id: GH-1\ntier: 2\nstatus: planning\n' > "$HITL_FILE"
rm -f /tmp/hitl-welcomed-"$$"
OUT=$(run_welcome)
echo "$OUT" | grep -q "HITL AI-Driven Development" \
    && pass "static menu shown when current_step missing" \
    || fail "static menu not shown: $OUT"

# ── Sync hook tests ───────────────────────────────────────────────────────────

# Use a PID-unique change ID so each run gets its own /tmp cache file.
SYNC_TEST_ID="GH-$$"
SYNC_TEST_NUM="$$"
trap 'rm -f "/tmp/hitl-last-step-${SYNC_TEST_ID}"' EXIT INT TERM

echo ""
echo "-- Sync hook: ignores writes to non-context files --"
write_context "$SYNC_TEST_ID" 2 10 "AI generates tests (RED)" "Build"
RESULT=$(hook_input "src/services/payment.py" | bash "$SYNC_HOOK"; echo "exit:$?")
echo "$RESULT" | grep -q "exit:0" \
    && pass "hook exits 0 for non-context file" \
    || fail "hook failed for non-context file: $RESULT"

echo ""
echo "-- Sync hook: recognizes .hitl/current-change.yaml --"
write_context "$SYNC_TEST_ID" 2 18 "Code review Round 1" "Verify"
# Mock gh: writes call args to a log file (hook redirects gh stdout to /dev/null,
# so we need a side-channel to verify gh was called with the right args)
GH_LOG="/tmp/hitl_test_gh_log_$$"
MOCK_DIR=$(mktemp -d)
rm -f "$GH_LOG"
printf '#!/usr/bin/env bash\necho "gh %s" >> %s\n' '"$*"' "$GH_LOG" > "$MOCK_DIR/gh"
chmod +x "$MOCK_DIR/gh"
RESULT=$(hook_input ".hitl/current-change.yaml" | PATH="$MOCK_DIR:$PATH" bash "$SYNC_HOOK" 2>&1; echo "exit:$?")
echo "$RESULT" | grep -q "exit:0" \
    && pass "hook exits 0 for context file write" \
    || fail "hook returned non-zero: $RESULT"
[[ -f "$GH_LOG" ]] \
    && pass "gh issue comment called for GH-N change_id" \
    || fail "gh not called — expected comment to be posted"
grep -q "issue comment ${SYNC_TEST_NUM}" "$GH_LOG" 2>/dev/null \
    && pass "gh called with correct issue number" \
    || fail "wrong issue number in gh call: $(cat "$GH_LOG" 2>/dev/null)"
grep -q "Code review Round 1" "$GH_LOG" 2>/dev/null \
    && pass "step name included in comment body" \
    || fail "step name not in comment: $(cat "$GH_LOG" 2>/dev/null)"
rm -rf "$MOCK_DIR" "$GH_LOG"

echo ""
echo "-- Sync hook: skips migration-setup placeholder change_id --"
write_context "migration-setup" 3 2 "Customize CLAUDE.md" "Migration Setup"
RESULT=$(hook_input ".hitl/current-change.yaml" | bash "$SYNC_HOOK" 2>&1; echo "exit:$?")
echo "$RESULT" | grep -q "exit:0" \
    && pass "hook exits 0 for migration-setup placeholder" \
    || fail "hook failed for migration-setup: $RESULT"
# gh should NOT have been called (no real issue)
echo "$RESULT" | grep -qv "gh called" \
    && pass "gh not called for migration-setup placeholder" \
    || fail "gh was called unexpectedly: $RESULT"

echo ""
echo "-- Sync hook: skips when current_step block is missing --"
mkdir -p .hitl
printf 'change_id: GH-99\ntier: 2\nstatus: planning\n' > "$HITL_FILE"
RESULT=$(hook_input ".hitl/current-change.yaml" | bash "$SYNC_HOOK" 2>&1; echo "exit:$?")
echo "$RESULT" | grep -q "exit:0" \
    && pass "hook exits 0 when current_step missing" \
    || fail "hook failed with missing current_step: $RESULT"

# ── Cleanup ───────────────────────────────────────────────────────────────────

rm -f "$HITL_FILE" /tmp/hitl_test_out.txt /tmp/hitl-welcomed-"$$"
rmdir .hitl 2>/dev/null || true

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
