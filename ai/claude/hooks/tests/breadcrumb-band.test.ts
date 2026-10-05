// Tests for the HITL breadcrumb band mod (BM-7). Run with `claude plugin test` on the directory
// that ci/breadcrumb-mod/assemble_plugin.py builds; `python3 -m pytest ci/breadcrumb-mod` does both.
// The fixture lines are what _steps.sh really writes: the current phase is marked ◐ and phases are
// two spaces apart (a validation review caught a made-up shape here).
import { expect, test } from 'claude-code/testing'

const RIBBON = 'HITL development ▸ GH-123 ▸ Requirements ✓  Design ✓  Build ◐  Verify ·  Assess ·  Ship ·  Post-Ship ·'
const STEP = '▸ Build: Generate Code (GREEN)   ·   tier 2'
const HINT = '→ /hitl:dev-tdd'
const WARN = '⚠ branch=main ≠ GH-123. Context may be stale; run /hitl:dev-switch-context'
const THEIRS = 'drawn by Claude Code'

type Files = { [name: string]: string }

// Stub the project files the mod may read. Paths arrive absolute, so match on the tail.
function project(on: any, files: Files) {
  const lookup = (path: string) => {
    for (const name of Object.keys(files)) if (path.endsWith(name)) return files[name]
    return undefined
  }
  on('fs.exists', (_$: any, e: any) => ({ value: lookup(e.path) !== undefined }))
  on('fs.read', (_$: any, e: any) => ({ value: lookup(e.path) ?? '' }))
  on('ui.render', () => ({ type: 'Text', props: {}, children: [THEIRS] }))
  on('turn.complete', () => ({ text: '' }))
}

function mount($: any, surface: string = 'terminal') {
  return $.ui.mount({
    plugin: 'hitl', component: 'AbovePrompt', requestId: 'above-prompt', surface,
    viewport: { columns: 100, rows: 30 },
    props: { hasSurvey: false, isWorking: false, maxRows: 5, bodyColumns: 80, scroll: { offset: 0, bodyRows: 3 }, view: {} },
  })
}

const cache = (ribbon = RIBBON, step = STEP, hint = HINT, warn = '') => [ribbon, step, hint, warn].join('\n') + '\n'

test('config absent: only what Claude Code draws', async ($, on) => {
  project(on, { '.hitl/breadcrumb.txt': cache() })
  const ui = await mount($)
  expect(await ui.find({ type: 'Text', text: /drawn by Claude Code/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /GH-123/ })).toBeUndefined()
  await ui.unmount()
})

test('breadcrumb: text draws nothing of ours', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: text\n', '.hitl/breadcrumb.txt': cache() })
  const ui = await mount($)
  expect(await ui.find({ type: 'Text', text: /GH-123/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /drawn by Claude Code/ })).toBeTruthy()
  await ui.unmount()
})

test('breadcrumb: band draws the ribbon with the current phase bold, the step line, a dim hint, and keeps theirs', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: band\n', '.hitl/breadcrumb.txt': cache() })
  const ui = await mount($)
  expect(await ui.find({ type: 'Text', text: /GH-123 ▸ Requirements/ })).toBeTruthy()
  const current = await ui.find({ type: 'Text', text: /^Build ◐$/ })
  expect(current).toBeTruthy()
  expect(current.props.bold).toBe(true)
  const before = await ui.find({ type: 'Text', text: /^HITL development ▸ GH-123 ▸ Requirements ✓  Design ✓  $/ })
  expect(before).toBeTruthy()
  expect(before.props.bold).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /^▸ Build: Generate Code \(GREEN\)/ })).toBeTruthy()
  const hint = await ui.find({ type: 'Text', text: /^→ \/hitl:dev-tdd$/ })
  expect(hint).toBeTruthy()
  expect(hint.props.dimColor).toBe(true)
  expect(await ui.find({ type: 'Text', text: /drawn by Claude Code/ })).toBeTruthy()
  await ui.unmount()
})

test('breadcrumb: band with no cache file draws nothing of ours', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: band\n' })
  const ui = await mount($)
  expect(await ui.find({ type: 'Text', text: /GH-123/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /drawn by Claude Code/ })).toBeTruthy()
  await ui.unmount()
})

test('breadcrumb: both on the desktop surface draws the ribbon', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: both\n', '.hitl/breadcrumb.txt': cache() })
  const ui = await mount($, 'desktop')
  expect(await ui.find({ type: 'Text', text: /GH-123 ▸ Requirements/ })).toBeTruthy()
  await ui.unmount()
})

test('a warning line draws red', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: band\n', '.hitl/breadcrumb.txt': cache(RIBBON, STEP, HINT, WARN) })
  const ui = await mount($)
  const warn = await ui.find({ type: 'Text', text: /^⚠ branch=main/ })
  expect(warn).toBeTruthy()
  expect(warn.props.color).toBe('red')
  await ui.unmount()
})

test('an empty hint draws no hint line', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: band\n', '.hitl/breadcrumb.txt': cache(RIBBON, STEP, '', '') })
  const ui = await mount($)
  expect(await ui.find({ type: 'Text', text: /^→/ })).toBeUndefined()
  await ui.unmount()
})

test('a ribbon with no current marker draws plain', async ($, on) => {
  const plain = 'HITL development ▸ GH-123 ▸ Requirements ✓  Design ✓'
  project(on, { '.hitl/config.yaml': 'breadcrumb: band\n', '.hitl/breadcrumb.txt': cache(plain) })
  const ui = await mount($)
  const el = await ui.find({ type: 'Text', text: /^HITL development ▸ GH-123 ▸ Requirements ✓  Design ✓$/ })
  expect(el).toBeTruthy()
  expect(el.props.bold).toBeUndefined()
  await ui.unmount()
})

test('an empty cache file draws nothing and does not throw', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: band\n', '.hitl/breadcrumb.txt': '' })
  const ui = await mount($)
  expect(await ui.find({ type: 'Text', text: /GH-123/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /drawn by Claude Code/ })).toBeTruthy()
  await ui.unmount()
})

test('turn.complete passes the event on', async ($, on) => {
  project(on, {})
  const out = await $.turn.complete({ turnId: 't1', answer: 'ok', durationMs: 10, isAborted: false, usage: null })
  expect(out).toEqual({ text: '' })
})
