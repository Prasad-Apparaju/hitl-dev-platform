# Breadcrumb as a Mod: Test Plan

> Status: **draft v1 (2026-10-05)**. What must fail for FR-37.

## 1. Renderer: `ci/breadcrumb/run_matrix.sh`, case "breadcrumb band cache"

| Assertion | Expect |
|---|---|
| Default mode writes the cache | file exists, three lines |
| Line 1 equals the banner's ribbon line without indent | string equality |
| Line 2 empty when the step has no command (the fixtures carry none) | empty |
| Default mode banner unchanged | contains `HITL development ▸` |
| `band`: banner prints nothing for an active change; cache still written | empty stdout; file non-empty |
| `both`: banner prints; status line unchanged; status line wrote the cache | contains the ribbon; contains `HITL ▸`; file non-empty |
| `band` with no active change: intake directive prints; no cache written | contains `NO ACTIVE CHANGE`; no file |
| Every pre-existing assertion | unchanged, 271 |

## 2. Mod: `ai/claude/hooks/tests/breadcrumb-band.test.ts`, run by `claude plugin test`

| Case | Stubs | Expect |
|---|---|---|
| config absent | `fs.exists` false for config | only the stub's text in the band, no ribbon |
| `breadcrumb: text` | config present, text | same |
| `breadcrumb: band`, cache present | both files | ribbon text found; the segment from `▶` is a bold Text; hint line dim; the stub's text still present |
| `breadcrumb: band`, cache missing | config present, cache absent | nothing of ours drawn |
| `breadcrumb: both`, surface desktop | both files | ribbon found |
| warning line | cache with a third line | a red Text with the warning |
| `turn.complete` | stub returns `{ text: '' }` | the hook calls next and does not throw |

## 3. Footprint guard: `ci/breadcrumb-mod/test_breadcrumb_mod.py`

| Case | Expect |
|---|---|
| `claude plugin validate --json` on the assembled directory | passes; hooks set equals `{ui.render{component=AbovePrompt}, turn.complete}`; calls set equals `{fs.exists, fs.read, ui.resolve, ui.invalidate}` |
| Mutation check | with `on('tool.call', ...)` added to a copy of the module, the hooks assertion fails |
| `claude plugin test` on the assembled directory | exit 0 |
| `hooks.json` | exactly one module, `./breadcrumb-band.js` |
| CLI absent | the module skips with a reason containing "not installed" (so CI's skip guard fails the run) |

## 4. Wiring: additions to `ci/wiring/`

| Case | Asserts |
|---|---|
| The plugin build ships the module | after `build.sh`, `hooks/breadcrumb-band.js` and `hooks/hooks.json` exist in the plugin tree and `hooks/tests/` does not (checked in the upgrade review; a wiring test asserts the build script's find pattern names `*.js` and excludes `tests`) |
| Ignore line in three places | `init-project.sh`, `start-from-prd` Step 0, `dev-update` Step 4.9 each mention `.hitl/breadcrumb.txt` |
| `_steps.sh` is the only renderer | no file under `ai/claude/hooks/` other than `_steps.sh` contains the ribbon separators `›` and `▶` in a render context (grep: the mod file contains `▶` only to find the current step, never to compose a ribbon) |

## 5. By hand

1. Start a session in a repo with an active change and no `breadcrumb` key: transcript ribbon and
   status line as in 2.17.0, no band.
2. Set `breadcrumb: band`, send a prompt: the band appears above the prompt with the current step
   bold; the transcript shows no ribbon; the status line unchanged.
3. Advance the step (edit the change file), finish a turn: the band updates by the end of the turn.
4. Set `breadcrumb: both`: band and transcript ribbon.
5. `claude --plugin-dir` on the assembled directory in a product repo, then `/plugin`: the dim
   line reads `1 mod active · hitl`.
6. In the VS Code panel or `claude -p` with `band`: no ribbon in the transcript, status line
   present; with `both`: the ribbon prints.
