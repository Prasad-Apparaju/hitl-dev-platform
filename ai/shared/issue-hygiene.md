# Filing issues: search first, confirm batches, revisit after merge

HITL gates the existence of an issue thoroughly and its creation not at all (#94). Six skills file
issues from review findings, one run can file several, and nothing revisits an issue once filed. In
one consumer project a quarter of the open follow-ups were duplicates or already discharged. These
three rules apply wherever a skill runs `gh issue create`.

## 1. Search before you file

```bash
gh issue list --state all --search "<three or four words from the title>" --limit 10
```

Read the matches. If one describes the same finding, comment on it with your specific evidence and
stop; return its URL. A closed match that this finding reopens gets a comment saying why, not a new
issue. Only file when nothing matches.

## 2. More than one issue in a run is one decision

When a step would file several issues (security review, pentest, drift check, incident), list them
first: one line each, title and the finding it comes from. Take one confirmation for the list, then
file. Never file in a loop with no one watching the count.

**An unattended run files at most one issue.** A scheduled drift check or a nightly job with nobody
present opens a single rollup issue naming every item, after searching for an open rollup to append
to. Twelve issues from a cron job is noise that gets closed unread.

## 3. Revisit follow-ups when the change merges

An issue filed from a review describes the code as it stood. The retrospective step reads back every
open follow-up this change's reviews filed and checks each against what merged: close the ones the
change discharged, comment on the ones whose premise moved, leave the rest. An issue nobody
re-reads becomes wrong without anyone changing it.

## Where this is checked

The wiring suite requires every skill that runs `gh issue create` to search first or to follow this
file; the onboarding skills are exempt because they create a project's first issue.
