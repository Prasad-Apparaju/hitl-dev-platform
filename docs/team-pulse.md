# Team Pulse

One page that answers the question a team asks itself every day on multi-contributor work: who
is on what, what is waiting on someone else, and where would a review, a decision or a pair of
hands unblock a colleague.

```
/hitl:team-pulse
```

It reads the last two weeks of commits, pull requests, reviews, issues and comments through `gh`,
folds them per person and per epic, and writes `docs/04-operations/team-pulse.html`. Every number
and event on the page links to its GitHub source, so any sentence can be checked in one click.

## What is on the page

| Section | What it shows |
|---|---|
| Needs attention | Every epic flag, draft PRs idle past the threshold, PRs waiting for a reviewer past the threshold, PRs merged by their author with no review, commits not linked to a GitHub account |
| Epics | Each open epic's checkbox list read as a slice tree, one state per slice (`done`, `PR in review`, `draft PR`, `active Nd`, `idle Nd`, `no issue yet`), the flags, one summary and one nudge |
| People | Per person: last activity, tallies, open PRs with draft flag and idle age, latest events, one sentence saying what they are on |
| Planning (leads only) | Session hours against milestones from self-reported `Hours:` lines, review load per person, idle-owner flags |

The sentences and nudges are written by the model from the collected data only, under a wording
rule: facts, no praise, no blame, no verdict on a person. A nudge names the thing that is waiting
and who can supply it.

## Two audiences

The first run asks one question and stores the answer in `.hitl/config.yaml`.

| `audience` | Who gets the link | What it shows |
|---|---|---|
| `team` (default) | every contributor | everyone's rows, the same page for all |
| `leads` | named leads | the same page plus the planning section; the team page is still written |

The team page never contains the planning section. The leads page contains everything the team
page does.

## Conventions it relies on

Three, described in full in the shared conventions file the plugin ships (`shared/team-pulse.md`):

1. An epic is an issue labelled `epic` or titled `Epic: ...`, and its checkbox list is its slice
   tree. A `#N` on a line links the slice to its issue. Prose gets an empty tree and a flag, never
   a guess.
2. HITL's own hook and gate comments start with a recognisable first line and never count as a
   person's activity.
3. A person reports time with one line in any comment: `Hours: session 2.5, milestone M3 10.5/20`.

## Config

```yaml
# .hitl/config.yaml
team_pulse:
  window_days: 14
  stale_review_days: 3
  stale_draft_days: 14
  stale_epic_days: 14
  epic_match: label:epic | title:"Epic:"
  change_id_prefix: GH
  exclude_logins: [dependabot[bot]]
  publish: file          # or artifact, when the Artifact tool is available
  audience: team         # or leads
```

## Refreshing it on a schedule

The page is only as current as its last run. Two ways to keep it fresh.

**A scheduled cloud routine** that runs the skill and republishes the same artifact URL. Needs the
GitHub app connected to the cloud environment first; that is what blocked scheduling on the field
project, so check it before anything else. Routine definition:

| Field | Value |
|---|---|
| Schedule | weekdays at 08:00, your timezone |
| Prompt | `/hitl:team-pulse` |
| Allowed tools | Bash (gh, python3), Read, Write, Artifact |
| Repo | the product repo, default branch |

**Host cron with `claude -p`** as the fallback, on any machine that has `gh` signed in and the
plugin installed:

```cron
0 8 * * 1-5  cd /path/to/repo && claude -p "/hitl:team-pulse" >> ~/team-pulse.log 2>&1
```

Both run the same skill and write the same files. Neither posts anything to an issue.

## Limits

- The notes are model-written prose on a page leads read. The wording rule and the source links
  reduce the chance of a wrong sentence; they do not remove it.
- A per-person page can drift into surveillance. The name, the missing role prefix, the wording
  rule, the `team` default and self-reported hours are the design answer.
- About eight paginated `gh api` calls per run plus one per open epic slice not already loaded.
  Fine at a few hundred issues; not tested on very large repositories.
