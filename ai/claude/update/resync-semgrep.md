# Semgrep rule re-sync: the Step 4.7 protocol

Read from Step 4.7 of `dev-update`. The block the step runs, and the rules behind it: what is installed, what is reported, what is never touched, and how a deliberate removal stays removed.

## Why this step exists

`.semgrep/` is the rule set `/hitl:dev-check-conventions` scans with. Onboarding copies it once, so without this step a rule fix upstream never reaches an already-onboarded project.

## The per-file protocol

Unlike a plain file copy, a product repo's rule set is co-owned: teams add and tune rules. So the step never blind-copies:

| Case | Action |
|---|---|
| Shipped rule the repo does **not** have | install it |
| Shipped rule, byte-identical | leave alone, say nothing |
| Shipped rule the repo has **modified** | show the diff and **ask** before overwriting |
| Rule the repo added itself | never touched, never reported as drift |
| Rule listed in `.semgrep/.hitl-optout` | never installed — a deliberate removal stays removed |

## The opt-out file

Without `.semgrep/.hitl-optout`, "install anything absent" would resurrect a deliberately deleted rule on every update. One path per line relative to `.semgrep/`, `#` comments allowed, for example `best-practices/tenant-isolation.yaml`. A listed rule is never installed and is reported as opted out.

## Superseded files

A rule that was renamed upstream leaves its old file behind, and the comparison loop cannot tell that apart from a rule the project wrote itself, so it would sit there forever as dead config. The fence reports the known superseded files (currently `best-practices/pydantic-validation.yaml`, renamed upstream and made framework-neutral) and never auto-deletes them: the project may have edited one. Delete it yourself once the replacement is in place.

## The block

Run this as one Bash call; it resolves the plugin root itself.

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
if [[ -z "$ROOT" || ! -d "$ROOT/shared/semgrep" ]]; then
  echo "No shipped rule set found: skipping semgrep re-sync."
else
  new=(); changed=(); skipped=()
  while IFS= read -r src; do
    rel="${src#"$ROOT"/shared/semgrep/}"
    [[ "$rel" == "install.sh" ]] && continue
    # Honour a deliberate removal — otherwise every update resurrects the deleted rule.
    if [[ -f .semgrep/.hitl-optout ]] && grep -qxF "$rel" <(grep -v '^[[:space:]]*#' .semgrep/.hitl-optout); then
      skipped+=("$rel"); continue
    fi
    if [[ ! -f ".semgrep/$rel" ]]; then
      new+=("$rel")
    elif ! cmp -s "$src" ".semgrep/$rel"; then
      changed+=("$rel")
    fi
  done < <(find "$ROOT/shared/semgrep" -type f \( -name "*.yaml" -o -name "*.yml" -o -name ".semgrepignore" \))
  [[ ${#skipped[@]} -gt 0 ]] && echo "  · opted out (.semgrep/.hitl-optout): ${skipped[*]}"

  # Install everything absent — nothing to lose, nothing to confirm.
  for rel in "${new[@]}"; do
    mkdir -p ".semgrep/$(dirname "$rel")"
    cp "$ROOT/shared/semgrep/$rel" ".semgrep/$rel"
    echo "  + installed .semgrep/$rel"
  done

  # Locally modified files are reported with a diff and left untouched for now.
  for rel in "${changed[@]}"; do
    echo "  ~ .semgrep/$rel differs from the shipped version:"
    diff -u ".semgrep/$rel" "$ROOT/shared/semgrep/$rel" | sed 's/^/      /'
  done
  [[ ${#changed[@]} -eq 0 && ${#new[@]} -eq 0 ]] && echo "  ✓ semgrep rules already current"

  # Superseded files: a rule that was RENAMED upstream leaves its old file behind, and the
  # loop above cannot tell that apart from a rule the project wrote itself, so it would sit
  # there forever as dead config. Report, never auto-delete — the project may have edited it.
  for old in best-practices/pydantic-validation.yaml; do
    if [[ -f ".semgrep/$old" ]]; then
      echo "  ! .semgrep/$old is superseded: it was renamed upstream and made framework-neutral."
      echo "    Its rule could never fire: delete it once you are happy with the replacement."
    fi
  done
fi
```

## When a file differs

Show the diff the fence printed and ask per file, with the question in Step 4.7. Only an explicit yes copies that one file. Keeping the repo's version means it misses the upstream rule fix; say so. Then stage `.semgrep/` and verify the rule set still loads, as the step's last fence does.
