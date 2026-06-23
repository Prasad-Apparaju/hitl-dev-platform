# Decision Packet Schema (Phase 10 reference)

Reference for Phase 10 of the Design Feature skill. Defines the decision packet file naming, the exact YAML schema, and how each field maps back to the work done in prior phases.

## Contents

- [File naming](#file-naming)
- [Schema](#schema)
- [Field mapping from prior phases](#field-mapping-from-prior-phases)
- [Gate comment and output](#gate-comment-and-output)

## File naming

For each confirmed slice, create `docs/decisions/issue-<N>-slice-<M>.yaml` (or `docs/decisions/issue-<N>.yaml` for a single-slice change). Create the `docs/decisions/` directory first if it does not exist.

## Schema

Use **exactly** the schema below — do not add, remove, or rename fields. Populate every field from the work completed in prior phases:

```yaml
# docs/decisions/issue-<N>.yaml  (or issue-<N>-slice-<M>.yaml for multi-slice)
issue: <N>                        # GitHub issue number (Phase 1)
slice: null                       # slice number M, or null for single-slice (Phase 7)
title: "<slice description>"      # from Phase 7
change_type: feature              # feature | bugfix | refactor | infrastructure
risk_level: medium                # low | medium | high | critical — derived from tier

domains:
  - <domain-name>                 # exactly one domain per packet (Phase 7)

source_docs:
  prd: "<path>#<requirement-ref>" # PRD path from Phase 1
  hld:
    - "<path>"                    # HLD path from Phase 3
  lld:
    - "<path>"                    # LLD path for this domain from Phase 5
  adr:
    - "<path>"                    # ADR paths from Phase 4 (empty list if none)

tests:
  plan: "<summary>"               # test plan summary from Phase 8
  new_tests:
    - "<tests/file.py::test_name>"  # full list from Phase 8
  registry_updated: false         # developer sets true during /hitl:dev-tdd

incidents:
  checked: true
  relevant: null                  # incident ID from Phase 8, or null

rollout:
  risk: medium                    # same as risk_level
  strategy: "canary 5% → 25% → 100%, 1h soak each"  # placeholder; ops refines
  go_no_go: "<measurable criteria from LLD or incident history>"

roi:
  required: false                 # true if effort > 1 day (Phase 1)
  estimate: null                  # roi_estimate from .hitl/current-change.yaml, or null

impact_brief:
  pm_mental_model: "<one sentence: what changes for the PM>"
  risk_assessment: "<one sentence: main risk>"

approvals:
  architecture: pending           # architect sets to approved after review
```

## Field mapping from prior phases

| Field | Source |
|---|---|
| `issue` | GitHub issue number from Phase 1 |
| `slice` | Slice number M; `null` if single-slice |
| `title` | Slice description from Phase 7 |
| `risk_level` | tier 0–1 → low, 2 → medium, 3–4 → high/critical |
| `domains` | Exactly one domain — the domain for this slice from Phase 7 |
| `source_docs.lld` | LLD path for this domain from Phase 5 |
| `source_docs.adr` | ADR paths from Phase 4 that apply to this slice |
| `tests.plan` | Test plan summary for this slice from Phase 8 |
| `tests.new_tests` | Test list from Phase 8 |
| `incidents.relevant` | Incident ID found in Phase 8, or `null` |
| `rollout.go_no_go` | Criteria from LLD or incident history (Phase 8) |
| `roi.required` | `true` if effort > 1 day (Phase 1) |
| `roi.estimate` | `roi_estimate` from `.hitl/current-change.yaml`, or `null` |

## Gate comment and output

After all packets are assembled and `.hitl/current-change.yaml` is set to `status: awaiting-packet-approval`, post a GitHub issue comment:

```bash
gh issue comment <issue-number> \
  --body "## ⏸ Gate: Decision Packet Review

Decision packet(s) assembled and awaiting TA + PM approval.

**Slices:** <slice plan from Phase 7>
**Decision packet(s):** \`docs/decisions/issue-<N>...\`
**Estimated effort:** <N days>
**Rollout risk:** <level>

Run \`/hitl:ta-approve\` to review and advance this gate. The TA checklist covers:
domain scope, LLD path, test plan completeness, rollout risk, and PM sign-off."
```

Then output:

```
Gate 4 reached — status set to 'awaiting-packet-approval'.

The TA (and PM) must run /hitl:ta-approve to approve the decision packet(s).
Once approved, status will advance to 'implementation-approved' and developers
can begin /hitl:dev-tdd.

This session ends here.
```
