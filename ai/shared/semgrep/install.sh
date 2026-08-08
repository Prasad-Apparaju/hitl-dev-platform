#!/usr/bin/env bash
# Install HITL's semgrep convention rules into a product repo (issue #47).
#
# Ships to the plugin as shared/semgrep/install.sh, alongside the rule files themselves, and is
# invoked by all three onboarding skills. It exists as a script rather than a block pasted into
# each SKILL.md because three copies of the same loop is how they drift — and because the skills
# are under a body-length budget.
#
# Copies ONLY files the project does not already have. A product repo's .semgrep/ is co-owned:
# teams add their own rules and tune the shipped ones for their stack, and onboarding must never
# overwrite that. Updating already-installed rules is /hitl:dev-update Step 4.7, which shows a
# diff and asks first.
#
# Run from the product repo root. Idempotent.

set -uo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

installed=0
while IFS= read -r src; do
  rel="${src#"$SRC"/}"
  [[ "$rel" == "install.sh" ]] && continue
  # A rule the project deliberately opted out of stays out — otherwise re-running onboarding
  # resurrects exactly what /hitl:dev-update was taught to leave alone.
  if [[ -f .semgrep/.hitl-optout ]] && grep -v '^[[:space:]]*#' .semgrep/.hitl-optout | grep -qxF "$rel"; then
    continue
  fi
  if [[ ! -f ".semgrep/$rel" ]]; then
    mkdir -p ".semgrep/$(dirname "$rel")"
    cp "$src" ".semgrep/$rel"
    installed=$((installed + 1))
  fi
done < <(find "$SRC" -type f \( -name "*.yaml" -o -name "*.yml" -o -name ".semgrepignore" \))

if [[ $installed -gt 0 ]]; then
  echo "Semgrep convention rules installed: .semgrep/ ($installed file(s))."
else
  echo "Semgrep convention rules already present — nothing copied."
fi
exit 0
