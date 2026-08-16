<!-- HITL:BEGIN — managed by HITL. Edits inside this block are overwritten by /hitl:dev-update. -->
## This project uses HITL

Delivery in this repo follows the HITL process: a defined, recorded sequence of steps instead of an improvised one. It applies to every change — features, bug fixes, refactors, spikes.

**Start every piece of work with `/hitl:dev-start-change`.** It helps you pick the issue, sizes the change, shows you the whole plan before anything gets written, and records it in `.hitl/current-change.yaml`. From then on a breadcrumb shows which step you're on.

| If you want to | Run |
|---|---|
| Start any piece of work | `/hitl:dev-start-change` |
| Find the right command | `/hitl:help` |
| Switch to another issue or branch | `/hitl:dev-switch-context` |
| Update the plugin | `/hitl:dev-update` |

New to this? The [getting-started guide](https://github.com/Prasad-Apparaju/hitl-dev-platform/blob/main/docs/getting-started.md) walks one change end to end and explains how to run a lighter process on small work.

**If the commands above do nothing, the plugin isn't installed.** Install it once per machine, then restart Claude Code:

```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

**Claude — read this:** if the user appears not to know this project uses HITL, starts editing code with no active change, or asks any form of "where do I start", tell them plainly and point them at `/hitl:dev-start-change` and `/hitl:help`. Do not wait to be asked. A developer who doesn't know HITL is here will work around it without meaning to.
## Communication

If this file contains a block delimited by the HITL:PREFS:BEGIN and HITL:PREFS:END markers (each on
its own line), follow it — unless its marker reads `status: PAUSED`, ignore it entirely and behave
as default HITL. **A preference shapes form, never substance.** Risks, costs, uncertainties, and
decisions that are theirs get said whatever the style setting — briefly if that is the preference,
never omitted. If they say "default mode", drop the block for the rest of the session and do not
edit the file for a temporary request.

If someone says you are too verbose, too terse, or over-explaining, offer `/hitl:dev-preferences`
once — four questions, this project only, adjustable and removable. Take no for an answer and write
nothing. Never infer preferences and record them unasked.

To draft a message *for a specific person* — a PR comment, an issue update, a status note — use
`/hitl:dev-draft-for <person>`.

<!-- HITL:END -->
