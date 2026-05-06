# Technical Advisor Playbook

**Role:** The Technical Advisor (TA) is the human expert who bridges business requirements and architecture. The TA owns the migration brief and review documents, gates the handoff to the Architect, and ensures the design starts from a validated problem statement — not from external vendor documents taken at face value.

**Behavioral mode:** Draft-propose-approve. Claude drafts; the TA reviews, challenges, and approves before any artifact is finalised or handed off. Claude does not proceed to the next phase without explicit TA approval.

---

## When this role applies

- You are leading or advising a migration project
- You are evaluating external documentation (vendor runbooks, consultant deliverables) before design begins
- You are deciding whether the Architect should proceed to HLD/LLD work
- You are reviewing design gate artifacts before a handoff to the Architect or Developer

---

## Phase 1 — Read and challenge the migration context

Before any design begins, verify the migration context is grounded:

```
Read docs/00-migration/migration-context.yaml.
Tell me: what is actually being migrated, what is the stated trigger,
and what assumptions are baked into the framing that I should challenge
before we go further.
```

Challenge the trigger explicitly. Ask:
- Is this the real reason, or the stated reason?
- Does the target architecture actually solve the problem?
- Are there simpler alternatives we have not considered?

Do not proceed to Phase 2 until the context is confirmed as accurate.

---

## Phase 2 — Evaluate external documentation

```
Read all files in docs/00-migration/external-reference/.
For each document: what does it claim, what is the evidence base for
that claim, and where does it assume a context (scale, team, platform)
that differs from ours?
```

Use the evaluation criteria from `/migrate:review-external-docs` Phase 2. The TA's job here is to apply judgment to the reliability ratings — Claude proposes ratings, the TA overrides where domain knowledge differs.

Approve or reject each document's use as design input before Phase 3.

---

## Phase 3 — Own the migration review

The migration review (`docs/00-migration/migration-review.md`) is a TA artifact. Claude drafts it; the TA must approve every section before it is marked `status: approved`.

Sections the TA must personally verify:
- **Reliable inputs** — would you stake the project on these?
- **Gaps requiring architect decision** — are these the real gaps, or are there more?
- **Divergence recommendations** — do these protect the team or create unnecessary risk?
- **Risk flags** — are the top risks actually the top risks?

The migration review is not approved until the TA can answer yes to: *"If the Architect reads only this document, will they design the right system?"*

---

## Phase 4 — Own the migration brief

The migration brief (`docs/00-migration/migration-brief.md`) is the PRD-equivalent for the migration. It replaces `docs/01-product/prd.md` in all downstream skills. The TA owns its accuracy.

Before approving, verify:

| Check | Question |
|---|---|
| Functional requirements | Are these testable? Would a developer know when they are done? |
| NFRs | Are throughput, latency, and volume numbers from measurement — not assumption? |
| Out of scope | Is everything excluded intentional? Will anything excluded come back as a surprise? |
| Open questions | Is every open question assigned to someone? Are any blocking HLD work? |
| Slice criterion | Does every planned slice produce something observable — demo-able or measurably verifiable? |

---

## Phase 5 — Handoff to Architect

**Handoff is valid only when all of the following exist and are approved:**

| Artifact | Location | Required state |
|---|---|---|
| Migration context | `docs/00-migration/migration-context.yaml` | Complete — no placeholders |
| External reference docs | `docs/00-migration/external-reference/` | Staged and inventoried |
| Migration review | `docs/00-migration/migration-review.md` | `status: approved` by TA |
| Migration brief | `docs/00-migration/migration-brief.md` | `status: approved` by TA |
| Open questions | Listed in migration brief | All assigned — none blocking |
| GitHub issue | Tracking issue created | Change ID recorded in `.hitl/current-change.yaml` |

**Do not hand off with open questions unassigned.** Unanswered NFRs at handoff become architecture mistakes at build time.

To initiate handoff:

```
/architect:design-system docs/00-migration/migration-brief.md
```

or for slice-by-slice:

```
/architect:design-feature
```

Tell the Architect: *"The migration brief replaces the PRD. Start from `docs/00-migration/migration-brief.md`."*

---

## Design gate responsibilities (ongoing)

After handoff the TA remains a gate reviewer — not a decision-maker for architecture, but a guardian of the original problem statement. At each design gate, ask:

- **HLD gate:** Does this architecture actually solve the migration trigger described in the brief?
- **LLD gate:** Are the domain boundaries consistent with what the external docs described as the integration points?
- **Code review gate:** Does the implementation match what I told the Architect to build?

If any gate answer is no, the TA raises it as a finding — the Architect decides how to resolve it.

---

## How to tell Claude you are the TA

At session start, say: *"I am the Technical Advisor for this session."*

Claude will switch to draft-propose-approve mode:
- Claude drafts documents and waits for your explicit approval before treating them as final
- Claude flags design decisions that require TA judgment rather than resolving them autonomously
- Claude does not advance to the next phase without your go-ahead
