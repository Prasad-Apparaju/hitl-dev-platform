# Breadcrumb as a Mod: Low-Level Design

> Status: **draft v1 (2026-10-05)**. Exact shapes for FR-37. Decisions in [`02-adrs.md`](02-adrs.md).

## 1. The setting

`.hitl/config.yaml`, top level: `breadcrumb: text | band | both`. Absent, unreadable or any other
value means `text`. Read by the hooks with `hitl_breadcrumb_mode <config.yaml>` in `_steps.sh`
(uses `hitl_scalar`, so quotes and trailing comments are handled as for the change file). Read by
the mod with `/^breadcrumb:\s*([a-z]+)/m` on the file's text; no YAML parser in the mod.

## 2. The cache file

`.hitl/breadcrumb.txt`, beside the change file, UTF-8, no colour codes: four lines, then (BM-9) a
header and one line per step:

| Line | Content | Example |
|---|---|---|
| 1 | The ribbon line as `welcome.sh` prints it, without the two-space indent. The current phase is marked `◐`, phases are two spaces apart. | `HITL development ▸ GH-123 ▸ Requirements ✓  Design ✓  Build ◐  Verify ·  Assess ·  Ship ·  Post-Ship ·` |
| 2 | The step line as the banner prints it | `▸ Build: Generate Code (GREEN)   ·   tier 2` |
| 3 | The next-step hint, or empty | `→ /hitl:qa-plan-tests`, `→ yours to do, no command`, `→ say go, Claude walks it` |
| 4 | The branch warning, or empty; one form from both writers | `⚠ branch=main ≠ GH-123. Context may be stale; run /hitl:dev-switch-context` |
| 5 | The header: the ribbon line up to the change id (BM-9) | `HITL development ▸ GH-123` |
| 6 on | One line per step, exactly as `hitl_steps` prints it: `n\|label\|status\|phase\|command` (BM-9) | `9\|RED\|current\|Build\|dev-tdd` |

Written by `hitl_write_breadcrumb_cache <yaml> <ribbon> <step> <hint> <warn> [<header>]`: lines 5 on
only when a header is given, which both callers do; the steps come from `hitl_steps <yaml>`, so the
writer adds no parsing. To `.breadcrumb.txt.tmp.<pid>`
then `mv -f`, so a reader never sees a partial file. Never fails the caller (returns 0). Not written
when there is no active change or the workflow block does not render; a stale file from an earlier
change is harmless because the mod reads it only when a change is active in the renderer's terms,
and the welcome hook rewrites it on the next prompt.

Callers: `welcome.sh` after rendering the ribbon for an active change (before the mode check);
`statusline-hitl.sh` in the same branch that renders the trail. The status line passes the short
warning form it already has.

Ignored by git: `tools/scripts/init-project.sh`, `start-from-prd` Step 0 item 4 and `dev-update`
Step 4.9 each append `.hitl/breadcrumb.txt` when absent, the way `.hitl/people/` is handled.

## 3. The welcome hook in each mode

```
mode = hitl_breadcrumb_mode .hitl/config.yaml
if active change and the workflow block renders:
    write the cache
    if mode == band: print the plain-English directive line only; exit 0
print the banner as today            # text and both
```

The no-active-change path (the intake directive) is above this and unchanged in every mode.

## 4. The mod

Files, in `ai/claude/hooks/` (shipped to the plugin's `hooks/` by `build.sh`, which now copies
`*.js` and skips `tests/`):

- `hooks.json`: `{ "modules": ["./breadcrumb-band.js"] }`. No `hooks` key: the plugin's settings
  hooks stay in each product repo's `.claude/settings.json` as today.
- `breadcrumb-band.js`: the hooks module. `tests/breadcrumb-band.test.ts`: its tests, not shipped.

Module shape:

```javascript
async function readMode($) { /* fs.exists + fs.read of .hitl/config.yaml; regex; default 'text' */ }

export function register(on) {
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const mode = await readMode($)
    if (mode !== 'band' && mode !== 'both') return next(e)
    if (!(await $.fs.exists('.hitl/breadcrumb.txt'))) return next(e)
    const [ribbon, step, hint, warn] = (await $.fs.read('.hitl/breadcrumb.txt')).split('\n')
    const { Box, Text } = $.ui.resolve(e)
    const theirs = await next(e)
    return Box({ flexDirection: 'column', children: [
      /* ribbon: plain before the current phase, bold from the phase name to its ◐, plain after; wrap truncate-end */
      /* step line plain when non-empty */
      /* hint dimColor when non-empty */
      /* warn color red when non-empty */
      /* theirs when truthy */
    ] })
  })
  on('turn.complete', async ($, e, next) => { $.ui.invalidate('ui.render'); return next(e) })
}
```

Validated footprint, exact: hooks `ui.render{component=AbovePrompt}`, `turn.complete`; calls
`$.fs.exists`, `$.fs.read`, `$.ui.resolve`, `$.ui.invalidate`. `readMode` and `readCache` are
top-level functions so the validator attributes their calls (`via readCache, readMode`).

As built (verified against the runtime with a probe, 2.1.289):

- Element factories from `$.ui.resolve(e)` take one props object with `children` inside it
  (`Text({ bold: true, children: ['x'] })`); positional children are dropped.
- `$.fs.read` resolves to a plain string and `$.fs.exists` to a boolean in the mod; the
  `{ value }` envelope is only the test stub's return shape.
- The ribbon line is one outer `Text({ wrap: 'truncate-end' })` holding three nested Text pieces
  (before, bold current phase up to its `◐`, after), not a Box row: truncation of a row Box does not cut as one
  line, nested Text does.
- A blank ribbon line draws nothing of ours (returns `next(e)`); a ribbon with no `◐` is drawn
  plain; an empty cache file draws nothing and does not throw.
- In tests, `ui.find({ text: /re/ })` matches the outer element first (its text is the
  concatenation), so the tests use anchored expressions to reach the bold piece and assert on
  `el.props`. No `session.start`, no command, no store, no
clock, no process, no network, no `$.state`.

Paths are relative to the project directory; the mods API resolves them against the session's
cwd (verified on 2.1.289 with a throwaway mod).

### 4.1 Step tags (BM-9)

`readCache` also returns `header` (line 5) and `steps` (lines 6 on). `stepRows` splits each line on
`|`: the first field is the number, the last three are status, phase and command, and the label is
everything between, so a `|` inside a label survives. A line without five fields, a number or a
label is skipped. With a header and at least one step the band draws `tagRows`; otherwise
`textRows`, the ribbon as section 4 describes, so a cache written before BM-9 draws as before.

`tagRows` draws two rows:

1. The header in bold and the step line after it, in one `Text({ wrap: 'truncate-end' })`.
2. A Box keyed `steps`, `flexDirection: 'row'`, `flexWrap: 'wrap'`: for each phase in step order,
   a Box keyed `phase-<Phase>` holding the phase name in bold capitals (`color: 'claude'` when it
   holds the current step, else `'text'`), then that phase's tags. A step with no phase gets no
   heading.

Each tag is a Box keyed `step-<n>`; its words are the trail's mark for the status
(`hitl_render_trail`: ✓ done, ▶ current, · open, ⊘ skipped, ◐ starter; unknown reads as open) and
the step's label.

| Surface | Tag | Colours |
|---|---|---|
| `terminal` | Square: the Box's `backgroundColor`, `paddingX: 1`, a Text inside | Theme keys. done `success` / `inverseText`; current `claude` / `inverseText`, bold; open `inactive` / `inverseText`; skipped `subtle` / `text`; starter no fill / `success` |
| any other with `Svg` (the desktop) | A rounded pill: one `Svg`, 20 px high, `rx` 9.5, width `7.2 × characters + 18`, `alt` the tag's words, text escaped for XML | Fixed, since an image cannot read the theme; checked on a light and a dark background. done `#2e7d32` / white; current `#c15f3c` / white, bold; open `#6b6b6b` / white; skipped outline `#8a8a8a`; starter outline `#388e3c` |

The surface is chosen by `e.surface`, not by whether the table has `Svg`: the terminal's table
answers `Svg` too (checked in the test kit on 2.1.307), so a table check would send pills to a
surface that cannot draw an image. The hint and warning rows follow as in
section 4. Footprint unchanged: the tags use only what `$.ui.resolve(e)` returns.

## 5. The guard: `ci/breadcrumb-mod/`

- `assemble_plugin.py <out>`: writes `<out>/.claude-plugin/plugin.json` (name `hitl`, version from
  `ai/claude/plugin/plugin.json`), copies `hooks.json` and `breadcrumb-band.js` to `<out>/hooks/`,
  copies `hooks/tests/*.test.ts` to `<out>/tests/`.
- `test_breadcrumb_mod.py` (pytest): skips with a reason containing "not installed" when `claude`
  is absent, so the CI skip guard fails the run rather than passing a skipped test; else runs
  `claude plugin validate --json` and asserts the hooks and calls sets are exactly section 4's;
  runs `claude plugin test` and asserts exit 0; asserts `hooks.json` lists exactly one module.
- `.github/workflows/tests.yml` installs the CLI with `npm install -g @anthropic-ai/claude-code`
  before the suite.

## 6. Build and install

- Plugin repo `scripts/build.sh`: the hooks sync copies `*.sh`, `*.json` and `*.js` from
  `ai/claude/hooks/`, excluding `tests/`. The existing `hooks.json` path rewrite is a no-op for a
  file with only `modules`.
- Nothing new is copied into product repos: the mod runs from the installed plugin; the hook
  wrappers in `.hitl/hooks/` already call the plugin's scripts, which carry the cache writer.
- `dev-update` adds the ignore line (section 2) and nothing else.

## 7. Documents

`CHANGELOG.md` under Unreleased; `docs/getting-started.md` section 4 gains the band paragraph;
`docs/01-product/prd.md` FR-37 row (Backlog until released).
