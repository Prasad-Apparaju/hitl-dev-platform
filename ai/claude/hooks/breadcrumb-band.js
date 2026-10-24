// HITL breadcrumb band (FR-37, BM-1 to BM-9). A Claude Code mod that draws the breadcrumb as a
// band above the prompt when `.hitl/config.yaml` says `breadcrumb: band` or `breadcrumb: both`.
//
// Draw-only. It reads two files, resolves UI elements and asks for a redraw at the end of each
// turn. It never parses the change file, never renders the ribbon, and never handles tools,
// permissions, commands, the model, the clock or the network. `_steps.sh` is the one renderer:
// welcome.sh and statusline-hitl.sh write its output to `.hitl/breadcrumb.txt` and this mod only
// shows what is there. Lines 1 to 4: ribbon, step line, next-step hint, warning. Lines 5 on (BM-9):
// a header, then one line per step exactly as `hitl_steps` prints it (`n|label|status|phase|command`).
// With step lines the band draws every step as a tag grouped under its phase; without them (a cache
// written before BM-9) it draws the ribbon text as before.
//
// Validated footprint: hooks ui.render{component=AbovePrompt} and turn.complete; calls
// $.fs.exists, $.fs.read, $.ui.resolve, $.ui.invalidate. ci/breadcrumb-mod/ fails on anything else.

// The team setting: 'text' (default, also when the file or key is absent), 'band' or 'both'.
async function readMode($) {
  if (!(await $.fs.exists('.hitl/config.yaml'))) return 'text'
  const found = /^breadcrumb:\s*([a-z]+)/m.exec(asText(await $.fs.read('.hitl/config.yaml')))
  return found ? found[1] : 'text'
}

// The renderer's cache, or null when there is nothing to show. Lines 1 to 4 as before; line 5 the
// header and the lines after it the steps, both empty in a cache written before BM-9.
async function readCache($) {
  if (!(await $.fs.exists('.hitl/breadcrumb.txt'))) return null
  const lines = asText(await $.fs.read('.hitl/breadcrumb.txt')).split('\n')
  const ribbon = (lines[0] || '').trim()
  if (ribbon === '') return null
  return {
    ribbon,
    step: (lines[1] || '').trim(),
    hint: (lines[2] || '').trim(),
    warn: (lines[3] || '').trim(),
    header: (lines[4] || '').trim(),
    steps: stepRows(lines.slice(5)),
  }
}

function asText(raw) {
  return typeof raw === 'string' ? raw : ''
}

// One cache line per step, as `hitl_steps` prints it: n|label|status|phase|command. The label is
// everything between the first field and the last three, so a label holding a `|` still reads
// whole. A line without five fields, a number or a label is skipped, never guessed at.
function stepRows(lines) {
  const rows = []
  for (const raw of lines) {
    const parts = raw.replace(/\r$/, '').split('|')
    if (parts.length < 5) continue
    const n = parts[0].trim()
    const label = parts.slice(1, parts.length - 3).join('|').trim()
    const status = parts[parts.length - 3].trim()
    const phase = parts[parts.length - 2].trim()
    if (n === '' || label === '') continue
    rows.push({ n, label, status, phase })
  }
  return rows
}

// Split the ribbon into [before, current, after] so the current phase can be drawn bold. The
// renderer marks it with ◐ and separates phases with two spaces, so the current piece runs from
// the start of that phase's name to the ◐. A ribbon with no ◐ is one plain piece.
function ribbonPieces(ribbon) {
  const mark = ribbon.indexOf('◐')
  if (mark < 0) return [{ text: ribbon, bold: false }]
  const gap = ribbon.lastIndexOf('  ', mark)
  const arrow = ribbon.lastIndexOf('▸ ', mark)
  const start = Math.max(gap >= 0 ? gap + 2 : 0, arrow >= 0 ? arrow + 2 : 0)
  const end = mark + 1
  return [
    { text: ribbon.slice(0, start), bold: false },
    { text: ribbon.slice(start, end), bold: true },
    { text: ribbon.slice(end), bold: false },
  ].filter((piece) => piece.text !== '')
}

// Each step's mark is the one the status line's trail prints for that status (`hitl_render_trail`
// in _steps.sh); an unknown status reads as not started.
const MARK = { done: '✓', current: '▶', open: '·', skipped: '⊘', starter: '◐' }

// The terminal's tags: square, in the person's theme colours, the text colour chosen against the
// fill. A starter (lightened by First Pass, still to finish) has no fill, only green text.
const SQUARE = {
  done: { fill: 'success', ink: 'inverseText', bold: false },
  current: { fill: 'claude', ink: 'inverseText', bold: true },
  open: { fill: 'inactive', ink: 'inverseText', bold: false },
  skipped: { fill: 'subtle', ink: 'text', bold: false },
  starter: { fill: '', ink: 'success', bold: false },
}

// The desktop's tags: rounded pills drawn as small SVG images. An image cannot read the theme, so
// these colours are fixed and were checked on a light and a dark background. Skipped and starter
// are outlines only: skipped work will not happen, starter work is only partly done.
const PILL = {
  done: { fill: '#2e7d32', stroke: '#2e7d32', ink: '#ffffff', bold: false },
  current: { fill: '#c15f3c', stroke: '#c15f3c', ink: '#ffffff', bold: true },
  open: { fill: '#6b6b6b', stroke: '#6b6b6b', ink: '#ffffff', bold: false },
  skipped: { fill: 'none', stroke: '#8a8a8a', ink: '#8a8a8a', bold: false },
  starter: { fill: 'none', stroke: '#388e3c', ink: '#388e3c', bold: false },
}
const PILL_HEIGHT = 20

function xmlText(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function pillSvg(text, pill, width) {
  const h = PILL_HEIGHT
  const r = (h - 1) / 2
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${h}" viewBox="0 0 ${width} ${h}">` +
    `<rect x="0.5" y="0.5" width="${width - 1}" height="${h - 1}" rx="${r}" ry="${r}" ` +
    `fill="${pill.fill}" stroke="${pill.stroke}"/>` +
    `<text x="${width / 2}" y="14" text-anchor="middle" font-size="12" ` +
    `font-family="Segoe UI, system-ui, -apple-system, sans-serif" font-weight="${pill.bold ? 700 : 400}" ` +
    `fill="${pill.ink}">${xmlText(text)}</text></svg>`
  )
}

// One step's tag. Keyed by the step's number, which is unique in a workflow (`18a` included).
function stepTag(ui, isPill, s) {
  const text = `${MARK[s.status] || MARK.open} ${s.label}`
  if (isPill) {
    const pill = PILL[s.status] || PILL.open
    const width = Math.ceil(text.length * 7.2) + 18
    return ui.Box({
      key: `step-${s.n}`,
      children: [ui.Svg({ source: pillSvg(text, pill, width), alt: text, width, height: PILL_HEIGHT })],
    })
  }
  const tag = SQUARE[s.status] || SQUARE.open
  const props = { key: `step-${s.n}`, paddingX: 1, children: [ui.Text({ color: tag.ink, bold: tag.bold, children: [text] })] }
  if (tag.fill !== '') props.backgroundColor = tag.fill
  return ui.Box(props)
}

// The tag rows: the header and step line on one line, then one wrapping flow of phase names, each
// followed by its own steps' tags. A phase name is a heading, never a tag: bold capitals in the
// plain text colour, orange for the phase that holds the current step.
function tagRows(ui, surface, cache) {
  const isPill = surface !== 'terminal' && typeof ui.Svg === 'function'
  const current = cache.steps.find((s) => s.status === 'current')
  const head = [ui.Text({ bold: true, children: [cache.header] })]
  if (cache.step !== '') head.push(ui.Text({ children: [`  ${cache.step}`] }))
  const flow = []
  const seen = {}
  let phase = null
  for (const s of cache.steps) {
    if (s.phase !== phase) {
      phase = s.phase
      if (phase !== '') {
        seen[phase] = (seen[phase] || 0) + 1
        const key = seen[phase] === 1 ? `phase-${phase}` : `phase-${phase}-${seen[phase]}`
        const ink = current && current.phase === phase ? 'claude' : 'text'
        flow.push(ui.Box({
          key,
          marginLeft: flow.length === 0 ? 0 : 1,
          children: [ui.Text({ bold: true, color: ink, children: [phase.toUpperCase()] })],
        }))
      }
    }
    flow.push(stepTag(ui, isPill, s))
  }
  return [
    ui.Text({ wrap: 'truncate-end', children: head }),
    ui.Box({ key: 'steps', flexDirection: 'row', flexWrap: 'wrap', columnGap: 1, rowGap: 'xs', alignItems: 'center', children: flow }),
  ]
}

// The rows as before BM-9: the ribbon with its current phase bold, then the step line.
function textRows(ui, cache) {
  const rows = [
    ui.Text({
      wrap: 'truncate-end',
      children: ribbonPieces(cache.ribbon).map((piece) =>
        piece.bold ? ui.Text({ bold: true, children: [piece.text] }) : ui.Text({ children: [piece.text] })),
    }),
  ]
  if (cache.step !== '') rows.push(ui.Text({ wrap: 'truncate-end', children: [cache.step] }))
  return rows
}

export function register(on) {
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const mode = await readMode($)
    if (mode !== 'band' && mode !== 'both') return next(e)
    const cache = await readCache($)
    if (cache === null) return next(e)

    const theirs = await next(e)
    const ui = $.ui.resolve(e)
    const rows = cache.header !== '' && cache.steps.length > 0 ? tagRows(ui, e.surface, cache) : textRows(ui, cache)
    if (cache.hint !== '') rows.push(ui.Text({ dimColor: true, children: [cache.hint] }))
    if (cache.warn !== '') rows.push(ui.Text({ color: 'red', children: [cache.warn] }))
    if (theirs) rows.push(theirs)
    return ui.Box({ flexDirection: 'column', children: rows })
  })

  // The renderer runs on each prompt; this keeps the band fresh at the end of a turn too (BM-6).
  on('turn.complete', async ($, e, next) => {
    $.ui.invalidate('ui.render')
    return next(e)
  })
}
