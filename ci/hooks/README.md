# ci/hooks/

Regression tests for the enforcement hooks in `ai/claude/hooks/`.

| Path | What it does |
|------|-------------|
| `test_check_hitl_context.py` | Pins the intake-gate path handling (plugin issue #20): absolute Claude Code paths honor the `.hitl/`/`.claude/` bootstrap exemption, out-of-project paths are ignored, guarded project files stay blocked. Invokes the real hook script the way the harness does (JSON on stdin, cwd = project root). |
| `test_check_platform_ready.py` | Pins the platform-bootstrap deploy gate (issue #21, decision D2): production-only, Tier 2+ only, waiver semantics (tier_limit, lapsed revisit), and the statusline platform chip (shown only while not delivery-ready). |

Run with `pytest ci/hooks/ -q`.
