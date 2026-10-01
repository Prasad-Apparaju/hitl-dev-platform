# Linked changes

When the design of a change lives in one repository and its code in another, or when a change in
one service needs an endpoint from another service first, HITL keeps one change per repository and
links them. Each change has its own record, branch and PR, as today. The link is a short list in the
change record, and HITL reads a partner's state from the host: its issue, its pull requests, and its
record where you can read it. It never reads a partner's code.

This is the first slice of the multi-repo workspace (FR-30). It is opt-in: a project that declares
no partner behaves exactly as before.

## Declaring a partner

Intake asks once, after the plan is agreed: does this change have a partner in another repository?
Answer with the repository, the partner's change id and its role, and intake writes:

```yaml
# .hitl/current-change.yaml
linked_changes:
  - { repo: org/docs,  change_id: GH-40,    role: docs }       # holds this change's approved design
  - { repo: org/email, change_id: EMAIL-14, role: provider }   # must be deployed before this change
```

| Role | Meaning, from this change's side | What waits on it |
|---|---|---|
| `docs` | the design was approved there | the first build step and the CI traceability gate |
| `provider` | it must ship first | the deploy step, per environment |
| `consumer` | it ships after this change | nothing here; the consumer declares this change as its provider |
| `code` | it implements this docs change | the fold of the PRD delta at conclude |

## What you see when something waits

The TDD step, the deploy step and the conclude step run one check and print one line per partner
plus a verdict, for example:

```
docs     GH-40      org/docs                     status=planning approved=no merged=no deployed=[]
waiting on: org/docs GH-40 is not approved (record status planning, no approval comment, no merged PR)
```

A partner counts as approved when its record says `implementation-approved`, or its issue carries
the Ready for Development or Gate Approved comment HITL posts (from someone with write access to
that repository; anyone else's is ignored), or its PR merged. A provider counts as shipped when its
PR merged and its record lists a deployment to the environment you are deploying to, or its issue
carries the Deployed comment for it. The record is read from the provider's branch, or from the
merge commit once the branch is gone. When the host cannot be read, the check stops and says which read failed. It never
passes on silence.

## Building against a design in another repository

Give the LLD by pinned reference wherever a skill asks for an LLD path, and in the manifest's `lld:`:

```
org/docs@3f2c9a1:docs/02-design/technical/lld/scm.md
```

The skill fetches that exact file into `.hitl/linked/` (ignored in git) and cites the reference. A
branch name is not a pin; the design that was approved is a commit.

## Repository settings

```yaml
# .hitl/config.yaml
repo: org/svc                 # this repository as owner/name
change_id_prefix: SCM         # default GH; your change ids become SCM-12, SCM-13
issues:
  epics: org/docs             # where epics are filed
  slices: org/svc             # where slices, bugs and follow-ups are filed
```

The prefix shows in the breadcrumb, Team Pulse, the retro and every issue comment HITL posts. With
a prefix configured, give skills the full id (`SVC-3`); a bare number is refused because it could be
any repository's. Add `prefixes: { DOCS: org/docs }` so a partner's id resolves to its repository.
Skills that file issues read the `issues` block, and intake links a new slice issue under its epic as
a sub-issue where the host supports it.

## Limits

- Two repositories that both need code changes are two linked changes; there is no single record
  spanning them yet. That is slice 1 of FR-30.
- The approval signals are the comments HITL posts. A repository that turned those hooks off must
  keep its change record readable on its branch.
- Access is the host's. A contributor who cannot read a repository sees what the host shows them
  about its issues and pull requests, and nothing else.

Conventions: `shared/linked-changes.md` in the plugin. Design:
`docs/design/multi-repo-workspace/` in the source repository.
