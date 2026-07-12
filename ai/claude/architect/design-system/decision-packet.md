# Decision Packet Generation (Phase 8d)

This is the reference for **Phase 8d** of the `architect-design-system` skill. Run it only after the delivery plan gate (Gate 6) has been approved by the TA.

For each confirmed slice, create a GitHub issue (or use the next available issue number) and create `docs/decisions/issue-<N>-slice-<M>.yaml` (or `docs/decisions/issue-<N>.yaml` for single-slice domains). Create the `docs/decisions/` directory first if it does not exist.

Use **exactly** the schema below — do not add, remove, or rename fields. For a greenfield system, apply the defaults shown unless the slice warrants otherwise:

```yaml
# docs/decisions/issue-<N>.yaml  (or issue-<N>-slice-<M>.yaml for multi-slice)
issue: <N>                        # GitHub issue number for this slice
slice: null                       # slice number M, or null if one slice per domain
title: "<domain> — initial implementation"
change_type: feature
risk_level: low                   # raise to medium/high if cross-domain or high-traffic

domains:
  - <domain-name>                 # exactly one domain per packet

source_docs:
  prd: "<path>#<requirement-ref>"
  hld:
    - "<path>"                    # relevant HLD from Phase 5
  lld:
    - "<path>"                    # domain LLD from Phase 6
  adr:
    - "<path>"                    # ADRs governing this slice (empty list if none)

tests:
  plan: "<key scenarios from facade APIs in the LLD>"
  new_tests: []                   # developer fills in during /hitl:dev-tdd
  registry_updated: false

incidents:
  checked: true
  relevant: null                  # null for new systems — no incident history

rollout:
  risk: low
  strategy: "Direct deploy — new system, no existing traffic"
  go_no_go: "<observable criterion from demo check in 8a>"

roi:
  required: false                 # set true if slice takes > 1 day
  estimate: null

impact_brief:
  pm_mental_model: "<demo check from 8a in one sentence>"
  risk_assessment: "<main risk for this slice>"

approvals:
  architecture: pending           # architect sets to approved after review
```

The `pm_mental_model` line is the demo check from 8a in one sentence — it is the handoff signal to the PM that this slice is complete.

After all decision packets are written, update `.hitl/design-system.yaml`: set `status: complete`.
