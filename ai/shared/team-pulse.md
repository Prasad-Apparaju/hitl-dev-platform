# Team Pulse conventions

Team Pulse (`/hitl:team-pulse`) reads GitHub and shows, per person and per epic, what is moving,
what is waiting on someone else, and who can unblock it. It works from three conventions. Two of
them HITL already follows; the third is a line a person writes.

## 1. An epic's checkbox list is its slice tree

An epic issue is one with the label `epic` or a title starting with `Epic:` (configurable). Its
body's checkbox list is read as the plan:

```markdown
- [ ] API #11
  - [ ] Handler #12
- [x] Schema #10
- [ ] Docs
```

Each line is a slice. Indentation is nesting. A `#N` in the line links the slice to its issue.
The pulse gives each slice one state: `done` (checked, or its issue is closed), `PR in review`,
`draft PR`, `active Nd`, `idle Nd`, or `no issue yet`. An epic written as prose gets an empty tree
and the flag "no checkbox list", never a guessed tree.

## 2. Hook and gate comments are not people

Comments whose first line starts with one of these are HITL's own machinery and never count as
human activity: `**HITL progress**`, `⏸ Gate:`, `## ⏸ Gate:`, `✅ Gate Approved`,
`## ✅ Ready for Development`, `**Skipped:**`, `<!-- hitl:`. Any skill or hook that posts to an
issue keeps its first line recognisable so the pulse can drop it. Logins ending in `[bot]` are
dropped too.

## 3. The Hours line

A person reports their own time with one line in any comment, on any issue or PR:

```
Hours: session 2.5, milestone M3 10.5/20
```

Either half may be omitted. `session` is hours spent this session; `milestone <name> <done>/<total>`
is the cumulative position on a named milestone. The pulse sums sessions inside the window and
shows the latest milestone line per person as a bar, on the leads page only. A line that does not
match exactly is ignored, never guessed at.

The end-of-session prompt a contractor pastes into Claude Code:

> End of session. Post one comment on the issue I worked on today with a line in the form
> `Hours: session <hours>, milestone <name> <done>/<total>`, using the numbers I give you now:
> [hours, milestone, done, total]. Post nothing else.

## Wording on the page

Facts from the collected data only. A note says what someone is on. A nudge names the thing that
is waiting and who can supply it ("PR #20 needs a reviewer; bob was asked"). No praise, no blame,
no hedging, no verdict on a person. Every number and event on the page links to its GitHub source.

## Two audiences

`team` (the default) gives every contributor the same page. `leads` adds one section, planning,
with session hours against milestones, review load per person and idle-owner flags, for named leads
only. In `leads` mode the skill also writes the team page, so contributors keep the self-service
view of their own PRs and reviewers. The team page never contains the planning section, and the
leads page contains everything the team page does.

## Config

Under `team_pulse:` in `.hitl/config.yaml`. Every key is optional.

| Key | Default | Meaning |
|---|---|---|
| `window_days` | 14 | how far back to read |
| `stale_review_days` | 3 | an open, non-draft PR with no review older than this needs a reviewer |
| `stale_draft_days` | 14 | a draft PR idle longer than this is listed |
| `stale_epic_days` | 14 | an epic not updated for longer than this is flagged |
| `epic_match` | `label:epic \| title:"Epic:"` | what makes an issue an epic |
| `change_id_prefix` | `GH` | how PR titles and branches name a slice issue (`GH-12`, `issue/12-`, `#12`) |
| `exclude_logins` | `[dependabot[bot], github-actions[bot]]` | logins never counted |
| `publish` | `file` | `file` writes under `docs/04-operations/`; `artifact` also publishes a page when the Artifact tool is available |
| `audience` | `team` | `team` or `leads` |
| `out_dir` | `docs/04-operations` | where the file goes |
