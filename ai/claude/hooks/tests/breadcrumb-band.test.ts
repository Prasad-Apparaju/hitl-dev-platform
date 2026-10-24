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

// Stub the project files the mod may read. Paths arrive absolute, so match on the tail. On Windows
// they arrive with backslashes, which never match a forward-slash name: turn them to slashes first
// (char code 92, so no escape can be mangled on the way into this file).
function project(on: any, files: Files) {
  const lookup = (path: string) => {
    const slashed = path.split(String.fromCharCode(92)).join('/')
    for (const name of Object.keys(files)) if (slashed.endsWith(name)) return files[name]
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

// ── Step tags (BM-9) ─────────────────────────────────────────────────────────────────────────────
// Lines 5 on of the cache, as _steps.sh writes them: the header, then `hitl_steps` output.
const HEADER = 'HITL development ▸ GH-123'
const STEPS = [
  '1|Issue|done|Requirements|manual',
  '2|Figma|skipped|Requirements|manual',
  '4|Docs|starter|Design|dev-generate-docs',
  '9|RED|current|Build|dev-tdd',
  '13|GREEN|open|Build|dev-tdd',
]
const tagged = (steps = STEPS, header = HEADER, hint = HINT, warn = '') =>
  [RIBBON, STEP, hint, warn, header, ...steps].join('\n') + '\n'
const BAND = { '.hitl/config.yaml': 'breadcrumb: band\n' }

// Every key in a found element's subtree, in document order.
function keysUnder(node: any, out: string[] = []): string[] {
  if (node && typeof node === 'object') {
    const key = typeof node.key === 'string' ? node.key : node.props?.key
    if (typeof key === 'string') out.push(key)
    for (const child of node.children ?? node.props?.children ?? []) keysUnder(child, out)
  }
  return out
}

test('step lines: the header, the step line and one flow of phase names and tags, no ribbon text', async ($, on) => {
  project(on, { ...BAND, '.hitl/breadcrumb.txt': tagged() })
  for (const surface of ['terminal', 'desktop']) {
    const ui = await mount($, surface)
    const header = await ui.find({ type: 'Text', text: /^HITL development ▸ GH-123$/ })
    expect(header).toBeTruthy()
    expect(header.props.bold).toBe(true)
    expect(await ui.find({ type: 'Text', text: /▸ Build: Generate Code \(GREEN\)/ })).toBeTruthy()
    expect(await ui.find({ type: 'Text', text: /Requirements ✓  Design/ })).toBeUndefined()
    const flow = await ui.find({ key: 'steps' })
    expect(flow.props.flexWrap).toBe('wrap')
    expect(keysUnder(flow).filter((k) => k !== 'steps')).toEqual([
      'phase-Requirements', 'step-1', 'step-2', 'phase-Design', 'step-4', 'phase-Build', 'step-9', 'step-13',
    ])
    expect((await ui.find({ type: 'Text', text: /^→ \/hitl:dev-tdd$/ })).props.dimColor).toBe(true)
    expect(await ui.find({ type: 'Text', text: /drawn by Claude Code/ })).toBeTruthy()
    await ui.unmount()
  }
})

test('phase names are bold capitals with no mark: text colour, orange for the current phase', async ($, on) => {
  project(on, { ...BAND, '.hitl/breadcrumb.txt': tagged() })
  for (const surface of ['terminal', 'desktop']) {
    const ui = await mount($, surface)
    const done = await ui.find({ type: 'Text', text: /^REQUIREMENTS$/ })
    const current = await ui.find({ type: 'Text', text: /^BUILD$/ })
    expect(done.props.bold).toBe(true)
    expect(done.props.color).toBe('text')
    expect(current.props.color).toBe('claude')
    expect(await ui.find({ type: 'Text', text: /^(REQUIREMENTS|DESIGN|BUILD) / })).toBeUndefined()
    await ui.unmount()
  }
})

test('terminal tags: square, theme colours per status, the trail marks', async ($, on) => {
  project(on, { ...BAND, '.hitl/breadcrumb.txt': tagged() })
  const ui = await mount($, 'terminal')
  const want: { [key: string]: [string | undefined, string, string] } = {
    'step-1': ['success', 'inverseText', '✓ Issue'],
    'step-2': ['subtle', 'text', '⊘ Figma'],
    'step-4': [undefined, 'success', '◐ Docs'],
    'step-9': ['claude', 'inverseText', '▶ RED'],
    'step-13': ['inactive', 'inverseText', '· GREEN'],
  }
  for (const key of Object.keys(want)) {
    const [fill, ink, text] = want[key]
    const tag = await ui.find({ key })
    expect(tag.type).toBe('Box')
    expect(tag.props.backgroundColor).toBe(fill)
    const label = tag.children[0] as any
    expect(label.props.color).toBe(ink)
    expect(tag.text).toBe(text)
  }
  expect((await ui.find({ key: 'step-9' })).children[0].props.bold).toBe(true)
  await ui.unmount()
})

test('desktop tags: rounded SVG pills, fixed colours per status, outlines for skipped and starter', async ($, on) => {
  project(on, { ...BAND, '.hitl/breadcrumb.txt': tagged() })
  const ui = await mount($, 'desktop')
  const want: { [key: string]: [string, string, string, string] } = {
    'step-1': ['#2e7d32', '#2e7d32', '#ffffff', '✓ Issue'],
    'step-2': ['none', '#8a8a8a', '#8a8a8a', '⊘ Figma'],
    'step-4': ['none', '#388e3c', '#388e3c', '◐ Docs'],
    'step-9': ['#c15f3c', '#c15f3c', '#ffffff', '▶ RED'],
    'step-13': ['#6b6b6b', '#6b6b6b', '#ffffff', '· GREEN'],
  }
  for (const key of Object.keys(want)) {
    const [fill, stroke, ink, alt] = want[key]
    const pill = (await ui.find({ key })).children[0] as any
    expect(pill.type).toBe('Svg')
    expect(pill.props.alt).toBe(alt)
    expect(pill.props.height).toBe(20)
    const source = String(pill.props.source)
    expect(source).toContain('rx="9.5"')
    expect(source).toContain(`fill="${fill}" stroke="${stroke}"`)
    expect(source).toContain(`fill="${ink}">`)
  }
  await ui.unmount()
})

test('a label with markup characters or a pipe is escaped in the pill and kept whole', async ($, on) => {
  project(on, { ...BAND, '.hitl/breadcrumb.txt': tagged(['5|A<B&C|D|open|Design|manual']) })
  const ui = await mount($, 'desktop')
  const pill = (await ui.find({ key: 'step-5' })).children[0] as any
  expect(pill.props.alt).toBe('· A<B&C|D')
  expect(String(pill.props.source)).toContain('· A&lt;B&amp;C|D</text>')
  await ui.unmount()
})

test('malformed step lines are skipped; with none left the band draws the ribbon as before', async ($, on) => {
  project(on, { ...BAND, '.hitl/breadcrumb.txt': tagged(['not a step', '7||done|Build|x', '|Z|done|Build|x']) })
  const ui = await mount($)
  expect(await ui.find({ key: 'steps' })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /GH-123 ▸ Requirements/ })).toBeTruthy()
  await ui.unmount()
})

test('step lines with no header draw the ribbon as before', async ($, on) => {
  project(on, { ...BAND, '.hitl/breadcrumb.txt': tagged(STEPS, '') })
  const ui = await mount($)
  expect(await ui.find({ key: 'steps' })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /GH-123 ▸ Requirements/ })).toBeTruthy()
  await ui.unmount()
})

test('a warning still draws red under the tags', async ($, on) => {
  project(on, { ...BAND, '.hitl/breadcrumb.txt': tagged(STEPS, HEADER, HINT, WARN) })
  const ui = await mount($)
  expect(await ui.find({ key: 'steps' })).toBeTruthy()
  expect((await ui.find({ type: 'Text', text: /^⚠ branch=main/ })).props.color).toBe('red')
  await ui.unmount()
})

test('breadcrumb: text with step lines still draws nothing of ours', async ($, on) => {
  project(on, { '.hitl/config.yaml': 'breadcrumb: text\n', '.hitl/breadcrumb.txt': tagged() })
  const ui = await mount($)
  expect(await ui.find({ key: 'steps' })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /drawn by Claude Code/ })).toBeTruthy()
  await ui.unmount()
})

test('turn.complete passes the event on', async ($, on) => {
  project(on, {})
  const out = await $.turn.complete({ turnId: 't1', answer: 'ok', durationMs: 10, isAborted: false, usage: null })
  expect(out).toEqual({ text: '' })
})
