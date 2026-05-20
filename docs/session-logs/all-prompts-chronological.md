# All Prompts — Chronological

## 2026-05-01 Session 01

*(Prompts from prior session — see 2026-05-01-session-01.md)*

---

## 2026-05-03 Session 01 (context window 1)

1. Apply 7 pre-identified brownfield consistency fixes
2. "when the PM started the requirement discussion, I didn't see the system creating an issue in github. Whenever they start working on a change or a new feature, there should be an issue in the system?"
3. "after PM creates an issue for a greenfield project or an enhancement to an existing project, will the workflow create tickets for the work the architect, developers etc. do? What kind of issues are created and updated all the way till the feature goes to deployment?"
4. "let's go with A" (chose Option A: gate comments on existing issue rather than sub-issues)
5. "my philosophy is, issues should be used for someone to pick up work, do their part in the workflow, keep them updated with progress. When they finish their work, all the documentation goes into HLD/LLD/ARD/TDD artifacts. Tickets are not long-term sources of truth. Just places for updates of work in transit. They NEVER be used as alternatives to the main documents since they can corrupt the context with outdated info. Is that how the process works?"
6. "yes pl ." (confirmed applying issue-as-pointer model everywhere)
7. "I have some feedback on these changes here /Users/Prasad_1/Projects/hitl-dev-platform/Claude-feedback/review-feedback-2026-05-03-workflow-latest-working-tree.md"
8. "are all the changes in git ?"
9. "yes"
10. "some more feedback here /Users/Prasad_1/Projects/hitl-dev-platform/Claude-feedback/review-feedback-2026-05-03-workflow-followup-693c474.md"
11. "where can I see a screenshot of the breadcrumbs of the workflow ?"
12. "yes" (confirmed creating breadcrumb screenshots for all roles)

---

## 2026-05-03 Session 02 (context window 2 — continuation)

1. *(Session resumed from context summary)* — completed pending breadcrumb screenshot work: created 5 SVGs, added Progress Banners to 4 skills, added Progress Breadcrumbs sections to 5 role docs, committed and pushed.

---

## 2026-05-19 Session 01

1. Update 4 playbook documentation files to reflect workflow change: new step 19a (architect code review with GitHub PR and 7-item checklist), step 25 renamed to "Verify PR completeness", post-ship expanded to 3 steps (30 pentest, 31 30-day ROI, 32 90-day ROI), step 28 adds `/hitl:ops:detect-drift`, overall step count 31 → 33.

---

## 2026-05-19 Session 02

1. (Continued from context-compacted session) Implement all 5 v4 addendum review findings: fix mangled paths in architect/design-feature/SKILL.md, remove invalid colon-bearing name: fields from all 40 SKILL.md files, restructure build.sh to place dev skills under skills/dev/ for correct /hitl:dev: namespacing, update plugin README with correct command names, update CLAUDE.md.template with correct command names.

---

## 2026-05-19 Session 03

1. "more feedback here `/tmp/hitl-repo-review-feedback-v6.md`" — addressed all 4 findings: (HIGH) flatten plugin skill layout from depth 3 to depth 2 (`skills/dev-tdd/` → `/hitl:dev-tdd`), (Medium) fix find parentheses bug in normalization, (Medium) fix non-hermetic test with GH-$$ and trap, (Low) global rename /hitl:role:name → /hitl:role-name across 80+ files plus SVG and step-count fixes.

## 2026-05-19 Session 04

1. (Continued from compacted context — v7 review feedback) — addressed all 4 v7 findings: (Medium) fix plugin.json description to hyphen-style commands + add manifest sync to build.sh; (Medium) add ${CLAUDE_PLUGIN_ROOT}/ prefix to bundled file refs via two-pass normalization in build.sh; (Low) delete skills/README.md + prevent rebuild; (Low) fix 31-step → 32-step in codex, fix stale source paths in generate-docs SKILL.md.

## 2026-05-19 Session 07

1. "more feedback `/tmp/hitl-repo-review-feedback-v10.md`" — clean pass, no blocking issues. Added CLAUDE_BIN env var override and resolved-path printing to build.sh to handle PATH shadowing by broken claude wrapper.

## 2026-05-19 Session 06

1. "more feedback `/tmp/hitl-repo-review-feedback-v9.md`" — (Medium) replaced PyYAML-dependent frontmatter guard in build.sh with `claude plugin validate "$PLUGIN_DIR"` call; no new dependencies, prints skip message if claude not on PATH. v9 also confirmed live smoke test passed: skill loaded correctly with first heading returned.

## 2026-05-19 Session 05

1. "here is feedback from real runtime validation with Claude Code 2.1.142 `/tmp/hitl-repo-review-feedback-v8.md`" — (High) quoted 3 SKILL.md descriptions with embedded ': ' to fix YAML frontmatter parse failures caught by claude plugin validate; (Medium) replaced relative Markdown links in pm-design-feature with bare path prose refs + added mangled-path and YAML frontmatter guards to build.sh; (Low) added version 1.0.0 to plugin.json + expanded manifest sync to include version. Validation result: `✔ Validation passed`.
