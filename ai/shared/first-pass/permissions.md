# First Pass — permission policy (FR-29 / CR-15 / ADR-7)

Under First Pass, routine reversible in-scope work proceeds without a per-action prompt; the genuinely
critical still prompts. This is the floor logic applied to tool permissions — **not** `bypassPermissions`.
The classifier is `ci/first-pass/permissions.py` (`decide()`); this file is the human-readable contract.

## Auto-allow (no prompt) — only when First Pass is active AND in scope

- **Reads** anywhere in the project working tree.
- **Edits / writes** to files **within the change's scope** — the declared manifest domain / `allowed_paths`.
- Running the project's own tests / build.

## Always prompt (critical) — even under First Pass

- **Irreversible / destructive:** deletes, destructive DB operations, `git push --force`.
- **Outward-facing:** deploys, promotions, migrations, external sends, secret / credential access.
- **Out of scope:** any write or delete outside the project root or the change's declared domain
  (detected via the existing `check-domain-boundary.sh` hook).
- **Anything unrecognized** — the classifier fails safe to a prompt.

## Mapping to Claude Code

First Pass corresponds to a scoped **`acceptEdits`**-style permission mode plus an allow-list bounded to the
change scope, with the critical actions above kept on the **ask** list. First Pass **must never** select
`bypassPermissions` — that would drop the critical prompts and violate CR-15 ("never bypass all safety").
The exact mode/allow-list wiring is applied by the driver skill when a change is marked `first_pass: true`.
