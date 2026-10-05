# Breadcrumb as a Mod: Requirements

> **What this is.** HITL's breadcrumb, the line that says which change you are on and where it
> stands, drawn as a persistent band above the prompt by a Claude Code mod, as a team option.
> The text breadcrumb in the transcript stays the floor and the default. This is **FR-37** in the
> [PRD](../prd.md) backlog table (§5.7), ticket
> [#150](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/150), status Backlog. The
> design (how it is built) is in `docs/design/breadcrumb-mod/`.
> Status: **draft v1 (2026-10-05)**, not reviewed. Related: the welcome hook, the status line,
> `_steps.sh` (the one breadcrumb renderer), the breadcrumb matrix (`ci/breadcrumb/`).

## 1. The problem

The breadcrumb is printed into the transcript on every prompt by a shell hook, and a compact form
sits in the status line. Both scroll or compete for one line. Claude Code 2.1.287 added mods:
plugin code that runs inside Claude Code and can draw a band directly above the prompt that stays
put while the transcript scrolls. The breadcrumb is the natural first use. It is also the first
time HITL would ask a team to run code inside their Claude Code with their permissions, so the
mod has to be small, draw-only, and off by default.

| What exists | What it does | What it misses |
|---|---|---|
| `welcome.sh` (UserPromptSubmit hook) | Prints the ribbon into the transcript each prompt | Scrolls away; repeats every prompt |
| `statusline-hitl.sh` | One line under the prompt: change, step, trail window, context bar | One line shared with model and context; no phase ribbon |
| `_steps.sh` | The one parser and renderer, matrix-locked (271 assertions) | Nothing; it is the source of truth this feature must not fork |

## 2. Who needs it

- **A developer in a terminal or the Desktop app** who wants to see where the change stands
  without scrolling up or re-reading the status line.
- **A team lead** who wants the option without changing anything for people on older Claude
  Code, in the VS Code panel, or in `claude -p`, where a mod cannot draw.

## 3. Scope

**In.** A mod inside the existing HITL plugin that draws the breadcrumb band. A team setting
that turns it on. The shell renderer writing its result where the mod can read it. The
transcript breadcrumb quieting down when the band is on. Tests the mod runs without a session.
Onboarding and update wiring for the one new ignored file.

**Out.** Panes, commands, buttons, tool-call handlers, permission decisions, model calls,
network, timers, the gate or the welcome directive as a mod, a second plugin, any change to the
ribbon's content or to `_steps.sh`'s rules.

**Slices.** One slice. The feature is small enough to ship whole.

## 4. Goals

1. A person who turns the band on sees the same breadcrumb they see today, always in view.
2. Nobody who leaves the setting alone sees any change.
3. One renderer. The band and the transcript never disagree.
4. The mod's validated footprint is small enough that a reviewer reads it in a minute.

## 5. Requirements

Requirement IDs are `BM-<n>`.

| ID | Requirement | Priority |
|---|---|---|
| **BM-1** | **The band shows the breadcrumb.** With the setting on, a band above the prompt shows the workflow, the change id, the phase ribbon with the current step marked, and the next-step hint (what to run), the same content the transcript line shows. | Must |
| **BM-2** | **A team setting, off by default.** `.hitl/config.yaml` gets `breadcrumb: text` (default, absent means text), `band`, or `both`. `text` is today's behaviour unchanged. `band` draws the band and the transcript prints nothing for an active change (the intake directive for no active change still prints). `both` draws and prints. | Must |
| **BM-3** | **One renderer.** The mod draws text the shell renderer wrote; it never parses the change file and never re-renders the ribbon. The welcome hook and the status line write the rendered line to a cache file next to the change file. The cache file is ignored by git. | Must |
| **BM-4** | **Draw-only, and provably so.** The mod handles the band's render event and the turn-end event, and calls only the file-read, file-exists, resolve and invalidate methods of the mods API. A wiring test runs `claude plugin validate --json` on the built plugin and fails if any other event or call appears. | Must |
| **BM-5** | **Degrades to today.** On Claude Code older than 2.1.287, with mods disabled, in the VS Code panel, in `claude -p` and in cloud sessions, nothing changes: the transcript line and the status line behave as the setting says for text. The docs say plainly that `band` on a surface that cannot draw shows nothing, and that mixed teams should pick `both`. | Must |
| **BM-6** | **Fresh within a turn.** The band reflects the change file after the next prompt or the end of the current turn, whichever comes first. | Should |
| **BM-7** | **Tested without a session.** `claude plugin test` covers: setting absent draws nothing; `band` draws the ribbon and marks the current step; cache file missing draws nothing; the Desktop surface draws the same text. The breadcrumb matrix gains one case: the renderer writes the cache file and its content equals the printed ribbon. | Must |
| **BM-8** | **Ships and updates in place.** The mod lives in the HITL plugin's own hooks directory, so `claude plugin install hitl@hitl` and `/hitl:dev-update` carry it. Update also adds the ignore line for the cache file to the product repo. | Must |

## 6. Rules the design must keep

- The mod never approves, denies or rewrites anything. If a later change wants a mod that does,
  it is a new requirement with its own review, not an extension of this one.
- `_steps.sh` stays the only renderer. A second rendering of the ribbon anywhere is a defect.
- Default is text. Turning the band on is a team decision recorded in `.hitl/config.yaml`,
  like `scenario_review_gate`.
- Everything the band shows is already in the transcript or the status line today. No new
  information is invented for the band.

## 7. Not doing

- The welcome directive, the gate, Team Pulse or the step picker as panes.
- Buttons on the band (for example "advance step"). A band that acts is a different trust
  level.
- A `userConfig` prompt at install. The setting is per team, not per person.
- Any Codex-side change (not maintained).

## 8. How we know it worked

| Measure | Target |
|---|---|
| Validated footprint | `claude plugin validate` lists exactly two events and four calls for the HITL plugin's module. |
| Default unchanged | The breadcrumb matrix passes unchanged, and a repo with no `breadcrumb` key produces byte-identical transcript output to 2.17.0. |
| Band equals text | In `both` mode the band's text and the transcript ribbon are the same string for every matrix fixture. |
| Install | A fresh install in a sandbox shows the band after `breadcrumb: band` is set and a prompt is sent; the same repo on 2.17.0 shows the transcript line. |

## 9. Version

| Version | Date | Change |
|---|---|---|
| draft v1 | 2026-10-05 | First draft from the 2026-10-05 discussion: a draw-only mod, one renderer, a team setting defaulting to text. Not reviewed. |

## 10. Where to look

- `ai/claude/hooks/_steps.sh`, `welcome.sh`, `statusline-hitl.sh`: the renderer and its two callers
- `ci/breadcrumb/run_matrix.sh`: the matrix that locks the renderer
- `ai/shared/templates/change-context.schema.yaml`: the change file the renderer reads
- Claude Code mods: https://code.claude.com/docs/en/plugins/mods/overview

## 11. Review history

None yet.
