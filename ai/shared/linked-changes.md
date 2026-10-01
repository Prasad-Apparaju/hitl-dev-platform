# Linked changes

A change that spans repositories stays one change per repository. Each record names its partners,
and HITL reads a partner's state from the host, never from its code. This is FR-30 slice 0
(EPIC #105); the full workspace, with access tiers and a shared documentation tree, comes later.

## The record

```yaml
# .hitl/current-change.yaml, optional
linked_changes:
  - { repo: org/docs,  change_id: GH-40,    role: docs }       # holds this change's design
  - { repo: org/email, change_id: EMAIL-14, role: provider }   # must ship before this change
```

Roles, from the declaring change's side: `docs` holds this change's design; `provider` must be merged
and deployed before this change deploys; `consumer` ships after this change; `code` implements this
docs change. The issue number is the digits at the end of the partner's change id, or an `issue:`
field when it is not.

## What waits on what

| Point | Check | Waits for |
|---|---|---|
| `dev-tdd`, `dev-apply-change` | `linked.py need docs-approved` | every `docs` partner approved: its record says `implementation-approved`, or its issue carries `## ✅ Ready for Development` or `## ✅ Gate Approved`, or its PR merged (a PR counts when it sits on the `issue/<n>-` branch, kept on the PR after the branch is deleted, or names the change id or `#<n>` as a whole word) |
| the CI traceability gate, where a repository runs `ci/preflight/check_change.py` (the platform's own gate; not installed by onboarding) | `check_change.py` | the decision packet and the LLD or ADR found in the `docs` partner's PR when none is local |
| `ops-deploy` | `linked.py need provider-deployed --env <target>` | every `provider` merged and deployed to the target: `deployments: [{environment: <target>}]` in its record (read from its branch, or from the PR's merge commit once the branch is gone), or `## 🚀 Deployed to <target>` on its issue |
| `dev-conclude` (fold) | `linked.py need code-merged` | every `code` partner merged; folding earlier is asked and recorded as `fold_before_partners` |

A comment marker counts only from an author with write, maintain or admin permission on that
repository; a marker from anyone else is listed as ignored. A deploy step marked done with no
environment recorded is reported plainly and does not pass.

Exit codes: 0 satisfied; 2 not satisfied, with one line naming what is waited on; 3 the host could not
be read. Unreadable is never a pass. The script is `ci/linked/linked.py` in the repository, or
`$ROOT/shared/ci/linked/linked.py` in the plugin.

## A design in another repository

Give the LLD as `owner/repo@<commit sha>:<path>` wherever a skill takes an LLD path, and in the
manifest's `lld:`. `linked.py fetch <ref>` writes the pinned file under `.hitl/linked/` (ignored in
git) and prints the path. Write the reference, never the cached path, into the record and into
anything you cite. A branch name is not a pin and is refused.

## The repository's own settings

```yaml
# .hitl/config.yaml
repo: org/svc                 # this repository as owner/name (default: what gh repo view says)
change_id_prefix: SCM         # default GH; start-change writes <prefix>-<issue>
issues:
  epics: org/docs             # where epics are filed
  slices: org/svc             # where slices, bugs and follow-ups are filed
```

```yaml
prefixes:                     # other repositories' prefixes, so SVC-3 and DOCS-7 resolve to a repository
  DOCS: org/docs
```

The prefix shows wherever the change id does: the breadcrumb, Team Pulse (whose own
`team_pulse.change_id_prefix` falls back to this key), the retro, and every issue comment HITL
posts (the issue number is the digits at the end of the id, whatever the prefix). With a prefix
configured, skills take `<PREFIX>-<n>` and refuse a bare number; `linked.py resolve DOCS-7` prints
`-R org/docs 7` from `prefixes:` and the declared partners, so a skill can read a partner's issue. Skills that file issues pass
`$(python3 "$LINKED" issue-repo epic|slice|bug|followup)` to `gh issue create`; `start-change` links a
new slice issue under its epic with `linked.py link-sub org/docs#40 org/svc#12` where the host allows
sub-issues, and comments on the epic otherwise.

## Wording

A refusal names the partner and what it waits on, in the checker's words. Nothing here grants or
checks access: a contributor sees exactly what the host lets them see.
