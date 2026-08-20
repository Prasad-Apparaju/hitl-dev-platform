# Collecting First Pass dispositions

Called from `start-change` Step 4b. The menu is presented **once**, in brief mode — not a
step-by-step interview.

## The choices file

```bash
# Only NON-keep steps go in. An absent step means keep. `actor` is the accountable human,
# not the agent.
cat > .hitl/first-pass-choices.json <<'JSON'
{
  "actor": "name@team",
  "choices": {
    "roi":   { "disposition": "decline", "reason": "internal tool; ROI self-evident" },
    "docs":  { "disposition": "starter", "reason": "thin first pass" }
  }
}
JSON
```

## Rules that still apply when collecting the choices

1. **Floor** — a `floor` skip requires the accountable role's risk-accepted `ack_by` + reason, and
   (for a step mapping to a hard gate) a linked `waiver_ref`. A skip is **not** a waiver. Put both
   in the entry.
2. **Starter** — write the honest-minimal artifact from `starters.py` (e.g. acceptance criteria =
   "a working version of the system"), mark it `needs-enhancement`, record its path; seed a
   fast-follow to *enhance* it.
3. **Defer** — seed a linked fast-follow ticket and put its ref in `followup_ref`.

If the validator is missing, say so **before** collecting any choices — the ledger is unenforced without it:

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
CHK="ci/first-pass/check_skips.py"
[[ -f "$CHK" ]] || CHK="$ROOT/shared/ci/first-pass/check_skips.py"
[[ -f "$CHK" ]] || echo "⚠ First Pass validator not found — run /hitl:dev-update to install it. Do NOT record skips until it is present: the ledger is unenforced without it."
```

Certification happens in **Step 6b**, once the change file exists and there is something real to certify.

Run the change under **brief mode** ([`shared/first-pass/brief.md`](../../shared/first-pass/brief.md) —
say less, ask less, never re-ask what intake already settled) and the **reduced-friction permission policy**
([`shared/first-pass/permissions.md`](../../shared/first-pass/permissions.md)); use the neutral /
respectful language in [`shared/first-pass/language.md`](../../shared/first-pass/language.md).

> **Resurfacing does not happen here.** `resurface.surface()` matches unresolved skips against the new
> change's domains and `allowed_paths`, and neither is known until the workflow's own impact step fills
> them. Called at change start it always matches nothing. It belongs at the impact step, where scope
> exists. See the worked example at
> [`docs/examples/first-pass/`](https://github.com/Prasad-Apparaju/hitl-dev-platform/tree/main/docs/examples/first-pass).
