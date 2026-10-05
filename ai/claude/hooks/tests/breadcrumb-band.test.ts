// Tests for the HITL breadcrumb band mod (BM-7). Run with `claude plugin test` on the directory
// that ci/breadcrumb-mod/assemble_plugin.py builds; `python3 -m pytest ci/breadcrumb-mod` does both.
import { expect, test } from 'claude-code/testing'

const RIBBON = 'HITL development ▸ GH-123 ▸ Requirements ✓ › Design ▶ Tests · Train · Packet › Build ·'
const HINT = '→ /hitl:qa-plan-tests'
const WARN = '⚠ branch=main ≠ GH-123'
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

const cache = (hint = HINT, warn = '') => RIBBON + '\n' + hint + '\n' + warn + '\n'

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
  expect(await ui.find({ type: 'Text', text: /drawn by Claude Code/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /GH-123/ })).toBeUndefined()
  await ui.unmount()
})

test('breadcrumb: band draws the ribbon, bold current step, dim hint, and keeps theirs', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'scenario_review_gate: on\nbreadcrumb: band\n', '.hitl/breadcrumb.txt': cache() })
  const ui = await mount($)
  const ribbon = await ui.find({ type: 'Text', text: /^HITL development .* Build ·$/ })
  expect(ribbon).toBeTruthy()
  expect(ribbon.text).toBe(RIBBON)
  expect(ribbon.props.wrap).toBe('truncate-end')
  const current = await ui.find({ type: 'Text', text: /^▶ Tests$/ })
  expect(current).toBeTruthy()
  expect(current.props.bold).toBe(true)
  const before = await ui.find({ type: 'Text', text: /^HITL development .* Design $/ })
  expect(before).toBeTruthy()
  expect(before.props.bold).toBeUndefined()
  const hint = await ui.find({ type: 'Text', text: /^→ \/hitl:qa-plan-tests$/ })
  expect(hint).toBeTruthy()
  expect(hint.props.dimColor).toBe(true)
  expect(await ui.find({ type: 'Text', text: /drawn by Claude Code/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /⚠/ })).toBeUndefined()
  await ui.unmount()
})

test('breadcrumb: band with no cache file draws nothing of ours', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: band\n' })
  const ui = await mount($)
  expect(await ui.find({ type: 'Text', text: /drawn by Claude Code/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /GH-123/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /→/ })).toBeUndefined()
  await ui.unmount()
})

test('breadcrumb: both on the desktop surface draws the same ribbon', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: both\n', '.hitl/breadcrumb.txt': cache() })
  const ui = await mount($, 'desktop')
  const ribbon = await ui.find({ type: 'Text', text: /^HITL development/ })
  expect(ribbon).toBeTruthy()
  expect(ribbon.text).toBe(RIBBON)
  expect((await ui.find({ type: 'Text', text: /^▶ Tests$/ })).props.bold).toBe(true)
  await ui.unmount()
})

test('a warning line draws red', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: band\n', '.hitl/breadcrumb.txt': cache(HINT, WARN) })
  const ui = await mount($)
  const warn = await ui.find({ type: 'Text', text: /^⚠ branch=main/ })
  expect(warn).toBeTruthy()
  expect(warn.text).toBe(WARN)
  expect(warn.props.color).toBe('red')
  await ui.unmount()
})

test('an empty hint line draws no hint', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: band\n', '.hitl/breadcrumb.txt': cache('', '') })
  const ui = await mount($)
  expect(await ui.find({ type: 'Text', text: /^HITL development/ })).toBeTruthy()
  expect(await ui.find({ type: 'Text', text: /→/ })).toBeUndefined()
  await ui.unmount()
})

test('a ribbon with no current marker draws plain and does not throw', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: band\n', '.hitl/breadcrumb.txt': 'HITL development ▸ GH-123 ▸ Done ✓\n\n\n' })
  const ui = await mount($)
  const ribbon = await ui.find({ type: 'Text', text: /^HITL development/ })
  expect(ribbon).toBeTruthy()
  expect(ribbon.text).toBe('HITL development ▸ GH-123 ▸ Done ✓')
  expect(await ui.find({ type: 'Text', text: /drawn by Claude Code/ })).toBeTruthy()
  await ui.unmount()
})

test('an empty cache file draws nothing of ours and does not throw', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: band\n', '.hitl/breadcrumb.txt': '' })
  const ui = await mount($)
  expect(await ui.find({ type: 'Text', text: /drawn by Claude Code/ })).toBeTruthy()
  expect(await ui.find({ type: 'Box' })).toBeUndefined()
  await ui.unmount()
})

test('turn.complete passes the turn on and does not throw', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: band\n', '.hitl/breadcrumb.txt': cache() })
  const result = await $.turn.complete({ turnId: 't1', answer: 'ok', durationMs: 10, isAborted: false, usage: null })
  expect(result).toEqual({ text: '' })
})
