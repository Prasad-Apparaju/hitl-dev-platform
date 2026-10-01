# Multi-Repo Workspace — Requirements (the WHAT)

> Status: **draft, v1.1 (2026-09-30)** — EPIC #105, PRD **FR-30**. v1.1 adds slice 0, linked changes,
> from the field case in the issue's 2026-10-01 comment: an opt-in step that ships before the full
> workspace and without the major version. Repo-scoped code access with one shared,
> readable documentation tree. HITL keeps governing the whole product while the code is split across
> repositories that different people can and cannot see.
> The design (HOW) will live under `docs/design/multi-repo-workspace/`.
> Related: the system manifest (domains), the change record (`.hitl/current-change.yaml`), the traceability
> gate (`ci/preflight/check_change.py`), First Pass permissions (FR-29), and the onboarding paths (FR-17..19).

## Problem

HITL assumes one git root that holds the documentation, the code, the tests, and its own `.hitl/` state.
Every hook resolves paths from that root, the traceability gate builds one changed-file list from one
`git diff` and requires docs and code to appear in it together, and the workflow expects one PR to carry the
design docs, the code, the tests, the decision packet, the impact brief and the rollout plan.

Hosting platforms (GitHub, GitLab, Bitbucket) grant **read** access per repository. There is no path-level
read permission. So an organisation that wants some people to see everything and other people to see code
**per repository** cannot do it inside one repo, whatever the folder layout. Today the choice is: everyone who
can see any code sees all of it, or the team splits the code and loses HITL.

The concrete driver is external contributors. A growing share of implementation work is done by freelancers,
often abroad, who should be able to work in the repository they are engaged for, read all of the
documentation so they understand what they are building, and see nothing else. Employees keep full access.

## The model (six principles)

1. **The code repository is the unit of code access.** HITL does not emulate path-level permissions. If two
   pieces of code need different audiences, they live in different repositories, and the hosting platform's
   own permissions do the enforcing. HITL grants no access itself.
2. **Two tiers of people.** A **full-access member** sees every repository in the workspace. A **repo-scoped
   contributor** sees the documentation and only the code repositories they have been granted. Both tiers use
   the same HITL surface; a contributor is never asked to do a step that needs access they do not have.
3. **Documentation is one shared tree, readable by all.** Requirements, designs, the system manifest and the
   registries live in one documentation repository that every workspace member can read. Who may *write* it
   is the organisation's choice; HITL requires only that the PM and Architect lanes work with write access to
   that repository alone.
4. **One change, one record, wherever the work lands.** A change keeps a single identity even when its design
   lands in the documentation repository and its code in one or more code repositories. The chain
   issue → requirement → design → code → tests → deployment stays unbroken and verifiable across repositories.
5. **HITL never leaks code into the shared tree.** Documentation being readable by all is a decision about
   documents people write. HITL-generated artifacts that embed code (session logs, retro records, review
   records, impact briefs with code excerpts, knowledge-graph output) are not documents in that sense and must
   never be written to the shared tree.
6. **A single repository is the degenerate workspace.** Nothing changes for a team that keeps docs and code
   together. A workspace is opt-in, and the single-repo layout stays the default and the reference behaviour.

## An accepted trade-off, recorded

Making *all* documentation readable by repo-scoped contributors exposes the architecture: the HLDs, the LLDs,
the system manifest (every domain, its files, its dependencies) and the ADRs. For an external contractor that
is usually more sensitive than the slice of code they write. This was raised during requirements on
2026-09-03 and **accepted by the product owner** as a trade-off: contributors need the whole picture to build
their part well, and the organisation prefers that over partitioned documentation. Principle 5 and WR-9 exist
so that the trade-off covers exactly what was accepted (authored documentation) and not more.

## Goals

- Let an organisation give some people every repository and other people specific repositories, with one
  documentation tree readable by everyone, and keep HITL governing the whole product.
- Let a repo-scoped contributor run the full developer lane for a change confined to their repository, with
  no access beyond that repository plus read on the documentation.
- Keep the traceability chain unbroken and machine-verifiable when a change spans repositories.
- Keep every hook, gate and validator honest about scope: "the project" becomes "the workspace", never
  "whatever happens to be on disk".
- Leave single-repository projects exactly as they are.

## Non-goals

- **Not** an access-management product. HITL does not create teams, grant or revoke permissions, or manage
  SSO/RBAC (PRD §9). It reads the declared topology and, at most, checks that the platform agrees with it.
- **Not** path-level access control inside one repository. That does not exist on the hosting platforms and
  HITL will not pretend otherwise.
- **Not** partitioned documentation. All authored documentation is readable by every workspace member (see
  the accepted trade-off). A future requirement may add tiers; this one does not.
- **Not** a monorepo tool. HITL does not manage submodules, subtrees, or vendoring; the design chooses how a
  workspace is materialised locally, and that choice is an implementation detail behind the workspace
  declaration.
- **Not** a mirror of docs into each code repository. There is one source of truth for documentation, and
  "readable by all" means read access to it, not copies.
- **Not** a change to what HITL governs. It still governs the build and ships no runtime, dashboard or service.

## Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| **WR-1** | **A project can declare a workspace.** A workspace is one documentation repository plus one or more code repositories, declared in a machine-readable file that HITL reads. A single repository holding both is a valid workspace with one member and needs no declaration. | Must |
| **WR-2** | **Every code path resolves to a repository.** The system manifest maps each domain to a code repository; every path a change, a gate or a skill reasons about resolves to exactly one repository in the workspace. An unmapped code path is a validation error, not a silent pass. | Must |
| **WR-3** | **Two access tiers are first-class.** The workspace declares, per repository, whether it is *shared* (readable by every member) or *scoped* (granted per person). The documentation repository is always shared. HITL uses the declaration to decide which steps and artifacts a person can be asked for. | Must |
| **WR-4** | **A repo-scoped contributor can run the developer lane end to end.** With write access to their code repository and read access to the documentation repository only, a contributor can start a change, run TDD, implement against the approved LLD, run the adherence and impact steps, and open the PR. No step in that lane requires reading or writing a repository they were not granted. | Must |
| **WR-5** | **The PM and Architect lanes need only the documentation repository.** Requirements, design, decision packets and approvals are authored and recorded with write access to the documentation repository alone. Reading code stays optional for these lanes, as it is today. | Must |
| **WR-6** | **One change identity across repositories.** A change spanning the documentation repository and one or more code repositories has one change id, one tier, one step plan and one skip ledger. Its record links every branch and PR the change produced, and its status is derived from all of them. | Must |
| **WR-7** | **The traceability chain spans repositories.** Issue → requirement → design (documentation repository) → code and tests (code repository) → deployment record is verifiable when the links cross repositories. The verify-traceability step and the CI traceability gate both work on a workspace, and neither requires docs and code in the same diff when they legitimately live in different repositories. | Must |
| **WR-8** | **Gates and hooks are workspace-aware, not root-aware.** The LLD-exists gate, the domain-boundary check, the context hook, the manifest-drift check and the First Pass permission model define scope as *the workspace repositories this person has* rather than *the current directory*. A path in another workspace repository is in scope when the change declares it; a path outside the workspace stays out of scope as today. | Must |
| **WR-9** | **HITL-generated artifacts never carry code into the shared tree.** Session logs, retro records, review records, impact-brief excerpts, knowledge-graph output and any other artifact that can contain code or file contents from a scoped repository are written to that repository or to a location with the same access as that repository, never to the shared documentation repository. Authored documentation is unaffected. | Must |
| **WR-10** | **A contributor can meet every implementer obligation without extra access.** The obligations that today write to the documentation tree during implementation (the test registry, an LLD touched by an API change, the token-cost registry) can be met by a contributor who has only their code repository. Whether that is partitioned registries with aggregation, a routed contribution, or something else is a design decision; the requirement is that no lane step is unreachable for a scoped contributor. | Must |
| **WR-11** | **Single-repository projects are unchanged.** Every existing hook, gate, skill and CI template behaves identically on a project with no workspace declaration. The workspace is additive and opt-in. | Must |
| **WR-12** | **A full-access member can review across repositories.** The Architect Code Review, the spec-conformance review and the impact brief can be run by a full-access member over a change whose code lives in a repository the author could see but a different reviewer might not; the review sees the design and the code together. | Should |
| **WR-13** | **The declared topology can be checked against the platform.** HITL can compare the workspace declaration with the hosting platform's actual repository permissions (via its API, when a token is available) and report mismatches: a scoped repository readable by everyone, or a documentation repository a member cannot read. Advisory, not a gate; HITL changes nothing on the platform. | Should |
| **WR-14** | **Onboarding paths understand workspaces.** Greenfield, brownfield and migration onboarding can create or adopt a workspace declaration, and there is guidance for splitting an existing monorepo into a workspace (which code moves where, how history is preserved, how the manifest is re-mapped) without losing the existing HITL record. | Should |

## Slice 0: linked changes (ships first, opt-in, no schema break)

The field case: a team splits agent services out of a monorepo into one repository per service. The
monorepo keeps the documentation and the epics; each service repository has its own code, CI, deploy,
issues and change-id prefix (`SCM-12`, `EMAIL-14`), because issue numbers collide across repositories.
Two shapes of change follow: docs in one repository and code in another; and code in two repositories
that must ship in order. Today the link between the halves is free text that nothing checks.

| ID | Requirement | Priority |
|----|-------------|----------|
| **LC-1** | **A change can declare linked changes in other repositories.** `linked_changes` in the change record lists `{repo, change_id, role}` with `role` one of `docs`, `provider`, `consumer`, `code`. It is optional; a project that never declares one behaves exactly as before. | Must |
| **LC-2** | **A code change cannot pass design while its `docs` partner is unapproved.** The partner's state is read from the host (its change record on its branch where readable, else its issue's HITL comments), never from its code. The TDD step and the traceability gate both refuse until the docs partner is approved. | Must |
| **LC-3** | **A `consumer` change cannot deploy before its `provider` partner is merged and deployed** to the same environment, read the same way. | Must |
| **LC-4** | **The implementer accepts an approved LLD from another repository by pinned reference**, `owner/repo@<commit>:<path>`, in place of a local path, in the TDD, apply-change and LLD-adherence steps and in the manifest's `lld:` field. | Must |
| **LC-5** | **The change-id prefix is configurable per repository** in `.hitl/config.yaml` and shows in the breadcrumb, Team Pulse and the retro. Default `GH`. | Must |
| **LC-6** | **Skills that file issues know which repository an epic and a slice belong in**, from `.hitl/config.yaml`, and can link a slice issue to its epic across repositories as a sub-issue. | Should |
| **LC-7** | **A `docs` change with `code` partners folds its PRD delta when the last code partner has merged**, so the PRD stays true to what is running; folding earlier is a recorded choice, never silent. | Should |

Slice 0 answers design fork 1 (where the change record lives: in each repository, linked) without
changing the change-record schema's required fields or the one-change-per-branch rule.

## Personas

- **Full-access member (engineer, architect, lead).** Sees every repository. Wants HITL to feel exactly as it
  does today, plus the ability to review and reason about changes that span repositories.
- **Repo-scoped contributor (freelancer, vendor engineer).** Has one or a few code repositories and reads all
  the documentation. Wants to be productive on day one, understand the whole system from the docs, and never
  hit a HITL step that needs access they were not given.
- **PM.** Works in the documentation repository. Wants requirements, designs and approvals to flow as today,
  and wants to see one change record even when three repositories were touched.
- **Engineering manager / owner.** Decides who gets what. Wants the declared topology to be true on the
  platform and wants confidence that no HITL byproduct quietly copies code somewhere everyone can read.

## Relationship to existing mechanisms (reuse, don't reinvent)

- **The system manifest** already maps domains to files and LLDs. It is the natural place for the
  domain → repository mapping (WR-2); the workspace declaration adds the repository list and access tiers.
- **The change record** (`.hitl/current-change.yaml`) already carries the change id, tier, step plan, skip
  ledger and PR URL. WR-6 extends it to several branches and PRs rather than inventing a second record.
- **The traceability gate and verify-traceability step** already define the chain. WR-7 changes where each
  link may live, not what the chain is.
- **First Pass permissions** already define in-scope and out-of-scope by path. WR-8 changes the definition of
  the root, not the model.
- **Waivers and the platform-readiness register** are unaffected; they stay in the documentation repository.
- **The public/private repository split of the framework itself** (this repo vs `hitl-internal`) is the same
  shape as this requirement applied to HITL's own development, and is the first workspace to dogfood on.

## Open questions (for the design phase — HOW, not WHAT)

- Where the change record lives when a change spans repositories: in the code repository where the work
  happens, in the documentation repository, or in both with one authoritative copy.
- How the branch ↔ change reconciliation in the hooks works when a change has one branch per repository.
- How a workspace is materialised on a developer's machine: sibling checkouts, submodules, or a virtual root
  resolved from the declaration. What a contributor who lacks a repository sees in its place.
- Which repository's CI runs the cross-repository traceability check, and how it reads the other repository's
  PR without granting the runner more access than the author had.
- How the registries are partitioned and aggregated (WR-10), and whether the aggregate is generated or
  hand-maintained.
- How the manifest schema qualifies `files:` and `lld:` with a repository, and how the compound-agentic
  validators' `artifact:` references resolve across repositories.
- How the knowledge graph and the impact brief work per repository and whether a full-access member gets a
  merged view.
- Whether the plugin's own state for a repo-scoped contributor needs a reduced profile, and how
  `/hitl:dev-update` keeps every repository in a workspace on the same HITL version.
- Versioning: this changes the change-record schema and the one-change-per-branch invariant, so it is
  expected to ship as a major version. Sequenced behind the 2.9.0 release.
