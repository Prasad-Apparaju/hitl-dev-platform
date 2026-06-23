---
description: "Audit dependencies for known CVEs and breaking changes BEFORE a dependency or framework upgrade proceeds, and produce a go/no-go. Run on every change using the Upgrade profile, during the Design phase after Impact Analysis and before implementation — the recorded CVE report and verdict are the `cve_audit` required evidence the merge gate checks."
argument-hint: "[change ID, e.g. 'GH-42'] [--package name@version]"
disable-model-invocation: true
---

**Before doing anything else:** Check whether `.hitl/` exists in the current directory. If it does not, stop immediately and output this — do not proceed with any steps:

```
This project hasn't been set up for HITL.
To get started, run one of these commands in your project directory:

  /hitl:dev-start-from-prd      new project from a PRD
  /hitl:dev-start-brownfield    adopt HITL on an existing codebase
  /hitl:dev-start-migration     migrate a system
```

---


# Dependency + CVE Audit

Audit the dependencies an upgrade touches for known CVEs and breaking changes, then produce a **GO / NO-GO** verdict that gates whether the upgrade proceeds.

**Input:** $ARGUMENTS
- `<change-ID>` — the upgrade being audited
- `--package <name@version>` — optional: scope the audit to a single package being bumped, instead of the whole tree

**Refusal rule:** If `.hitl/current-change.yaml` is not on the **Upgrade** profile, stop: "This change is not an Upgrade — the Dependency + CVE audit is an Upgrade-profile gate. If a dependency or framework bump is in scope, re-run `/hitl:dev-apply-change` and select the Upgrade profile."

The audit covers two distinct questions, both required:
1. **Security** — does any current or target dependency carry a known CVE?
2. **Breaking changes** — does the version bump cross a major boundary or introduce documented breaking changes / deprecations the code relies on?

---

## Required tools

Use the audit tool that matches the project's ecosystem (detect from the lockfile present). Only the matching tool is needed; if it is absent, report which to install rather than skipping the security check.

| Ecosystem | Lockfile | CVE audit tool | Command |
|---|---|---|---|
| Node / npm | `package-lock.json` | `npm audit` | `npm audit --json` |
| Node / pnpm · yarn | `pnpm-lock.yaml` · `yarn.lock` | `pnpm audit` · `yarn npm audit` | `pnpm audit --json` |
| Python | `poetry.lock` · `requirements.txt` | `pip-audit` | `pip-audit -f json` |
| Go | `go.sum` | `govulncheck` | `govulncheck -json ./...` |
| Rust | `Cargo.lock` | `cargo audit` | `cargo audit --json` |
| Java / Maven | `pom.xml` | OWASP Dependency-Check | `dependency-check --format JSON` |
| Any / container / multi-lang | — | `osv-scanner`, `trivy`, `grype` | `osv-scanner --lockfile=<file> --format json` · `trivy fs --scanners vuln .` |

**Cross-ecosystem fallback:** `osv-scanner` and `trivy` read most lockfiles and query the OSV database — use one of them when the native tool is unavailable or the repo is multi-language.

If no audit tool is installed, report exactly which one to install (with the install command if known) and stop. Do not declare GO without a security scan — an unaudited upgrade is a NO-GO by default.

---

## Progress Banners

Format: `---` line, `**Dependency + CVE Audit — Step N / 4: [Name]**`, trail, `---`.

| Step | Name | Banner trail |
|---|---|---|
| 1 | Inventory the upgrade | `▶ Inventory · ○ CVE scan · ○ Breaking changes · ○ Verdict` |
| 2 | CVE scan | `✅ Inventory · ▶ CVE scan · ○ Breaking changes · ○ Verdict` |
| 3 | Breaking-change review | `✅ Inventory · ✅ CVE scan · ▶ Breaking changes · ○ Verdict` |
| 4 | Go / No-Go verdict + record | `✅ Inventory · ✅ CVE scan · ✅ Breaking changes · ▶ Verdict` |

---

## Step 1 — Inventory the upgrade

Read `.hitl/current-change.yaml` and the impact-analysis output to determine what is being bumped:

```
Upgrade inventory — <ChangeID>
──────────────────────────────
Direct bumps:     <pkg from→to, one per line>
Crosses major?:   <yes/no per bump — semver major boundary>
Transitive churn: <count of indirect deps that change, if known from a dry-run resolve>
Ecosystem / tool: <detected lockfile → audit tool>
```

If the target versions are not yet pinned, resolve them first (e.g. `npm install --package-lock-only`, `poetry lock --no-update` against the proposed constraint) so the audit runs against the **resolved** tree, not just the declared constraint.

---

## Step 2 — CVE scan

Run the matching audit tool against both the current tree and, where feasible, the resolved target tree — an upgrade can fix CVEs or introduce new ones.

```bash
# Example (npm); substitute the tool from the table above
npm audit --json > audit-current.json
# Resolve target versions into a lockfile, then re-scan
npm audit --json > audit-target.json
```

Summarize each finding with severity and whether the upgrade fixes or introduces it:

```
CVE scan results
────────────────
  <CVE / advisory id>  <severity>  <package@version>  — <fixed-by-upgrade | introduced-by-upgrade | unchanged>
  ...
Totals: critical <n>  high <n>  moderate <n>  low <n>
```

- A **critical or high** CVE that the upgrade does **not** fix, or that it **introduces**, is a blocking finding.
- Note any advisory with no fixed version available — that constrains the verdict (may force a different target or a documented accepted-risk).

---

## Step 3 — Breaking-change review

A clean CVE scan does not mean the upgrade is safe to apply. For every bump that crosses a major version (or any minor flagged by the impact analysis):

- Read the dependency's **CHANGELOG / release notes / migration guide** for the version range being crossed.
- List documented breaking changes, removed/renamed APIs, and deprecations.
- Cross-check against actual usage in the codebase — grep for the affected symbols/APIs to find call sites that will break.

```
Breaking-change review
──────────────────────
  <pkg> <from>→<to>:
    - <breaking change>  — affects: <file:line call sites, or "no usage found">
    - <deprecation>      — affects: <…>
```

Flag any breaking change with live call sites as work the implementation must address. If the upgrade touches a framework with a codemod/migration tool, note it (the implementation step can run it).

---

## Step 4 — Go / No-Go verdict and record

Combine both halves into a single verdict:

```
Dependency + CVE Audit — <ChangeID>
───────────────────────────────────
CVEs:             critical <n>  high <n>  moderate <n>  low <n>   (unfixed/introduced: <list>)
Breaking changes: <n> documented, <n> with live call sites
Verdict:          GO / GO-WITH-CONDITIONS / NO-GO

Rationale: <one or two sentences>
Conditions (if any): <e.g. "bump to X.Y.Z instead — current target carries unfixed CVE-…"; "address N call sites for removed API foo()">
```

Verdict rules:
- **GO** — no unfixed critical/high CVE introduced or carried; breaking changes are either absent or have no live call sites.
- **GO-WITH-CONDITIONS** — proceedable only after the listed conditions are met (different target version, call-site fixes, accepted-risk sign-off for a low/moderate advisory with no fix). List each condition explicitly.
- **NO-GO** — an unfixed critical/high CVE in the target, or breaking changes the team is not prepared to absorb. The upgrade does not proceed.

**Record the result.**

On the GitHub issue:

```bash
gh issue comment <issue-number> \
  --body "## 🔒 Dependency + CVE Audit — <verdict>

**CVEs:** critical <n> · high <n> · moderate <n> · low <n>
**Breaking changes:** <n> (<n> with live call sites)
**Verdict:** GO / GO-WITH-CONDITIONS / NO-GO

<paste verdict block; list conditions if any>

Audit tool: <tool>. Raw report at \`<path>\`."
```

In `.hitl/current-change.yaml`:

```yaml
cve_audit:
  audited_at: <ISO timestamp>
  tool: <tool>
  cves: { critical: <n>, high: <n>, moderate: <n>, low: <n> }
  unfixed_or_introduced: [ "<advisory ids>" ]
  breaking_changes: <n>
  breaking_with_callsites: <n>
  verdict: go | go-with-conditions | no-go
  conditions: [ "<condition>" ]
  raw: <path to exported json>
```

**On GO**, report that `cve_audit` evidence is recorded and the upgrade may proceed to implementation.

**On NO-GO or unmet conditions**, do not set `verdict: go`. The Upgrade profile requires `cve_audit` as passing evidence at the merge gate — the change cannot complete until the verdict is GO (or conditions are satisfied and re-audited).

---

## When to Run

| Workflow step | Gate |
|---|---|
| Design phase, after Impact Analysis, before implementation (Upgrade profile) | a GO verdict is required before code is written against the new versions |
| Merge gate (Integration Verification) | `cve_audit.verdict` must be `go`; a missing or NO-GO audit blocks merge |

---

## Important Rules

- An upgrade with no CVE scan is a NO-GO by default — never infer "probably fine" without running the tool.
- Audit the **resolved** dependency tree (lockfile), not just the declared version constraint — transitive deps carry CVEs too.
- A clean security scan is only half the audit — a major-version bump with unreviewed breaking changes is not a GO.
- "Fixed in a later version" is not a fix until that version is the target — re-audit after changing the target.
- Accepted-risk for a low/moderate advisory with no available fix requires explicit operator sign-off recorded in `conditions`, not a silent pass.
