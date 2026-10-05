// HITL breadcrumb band (FR-37, BM-1 to BM-7). A Claude Code mod that draws the breadcrumb as a
// band above the prompt when `.hitl/config.yaml` says `breadcrumb: band` or `breadcrumb: both`.
//
// Draw-only. It reads two files, resolves UI elements and asks for a redraw at the end of each
// turn. It never parses the change file, never renders the ribbon, and never handles tools,
// permissions, commands, the model, the clock or the network. `_steps.sh` is the one renderer:
// welcome.sh and statusline-hitl.sh write its output to `.hitl/breadcrumb.txt` (line 1 ribbon,
// line 2 next-step hint, line 3 warning) and this mod only shows that text.
//
// Validated footprint: hooks ui.render{component=AbovePrompt} and turn.complete; calls
// $.fs.exists, $.fs.read, $.ui.resolve, $.ui.invalidate. ci/breadcrumb-mod/ fails on anything else.

// The team setting: 'text' (default, also when the file or key is absent), 'band' or 'both'.
async function readMode($) {
  if (!(await $.fs.exists('.hitl/config.yaml'))) return 'text'
  const found = /^breadcrumb:\s*([a-z]+)/m.exec(asText(await $.fs.read('.hitl/config.yaml')))
  return found ? found[1] : 'text'
}

// The renderer's cache, or null when there is nothing to show.
async function readCache($) {
  if (!(await $.fs.exists('.hitl/breadcrumb.txt'))) return null
  const lines = asText(await $.fs.read('.hitl/breadcrumb.txt')).split('\n')
  const ribbon = (lines[0] || '').trim()
  if (ribbon === '') return null
  return { ribbon, hint: (lines[1] || '').trim(), warn: (lines[2] || '').trim() }
}

function asText(raw) {
  return typeof raw === 'string' ? raw : ''
}

// Split the ribbon into [before, current, after] so the current step (from ▶ up to the next
// ` ·` or ` ›`) can be drawn bold. A ribbon with no ▶ is one plain piece.
function ribbonPieces(ribbon) {
  const start = ribbon.indexOf('▶')
  if (start < 0) return [{ text: ribbon, bold: false }]
  const rest = ribbon.slice(start)
  let end = rest.length
  for (const sep of [' ·', ' ›']) {
    const at = rest.indexOf(sep, 1)
    if (at > 0 && at < end) end = at
  }
  return [
    { text: ribbon.slice(0, start), bold: false },
    { text: rest.slice(0, end), bold: true },
    { text: rest.slice(end), bold: false },
  ].filter((piece) => piece.text !== '')
}

export function register(on) {
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const mode = await readMode($)
    if (mode !== 'band' && mode !== 'both') return next(e)
    const cache = await readCache($)
    if (cache === null) return next(e)

    const theirs = await next(e)
    const { Box, Text } = $.ui.resolve(e)
    const rows = [
      Text({
        wrap: 'truncate-end',
        children: ribbonPieces(cache.ribbon).map((piece) =>
          piece.bold ? Text({ bold: true, children: [piece.text] }) : Text({ children: [piece.text] })),
      }),
    ]
    if (cache.hint !== '') rows.push(Text({ dimColor: true, children: [cache.hint] }))
    if (cache.warn !== '') rows.push(Text({ color: 'red', children: [cache.warn] }))
    if (theirs) rows.push(theirs)
    return Box({ flexDirection: 'column', children: rows })
  })

  // The renderer runs on each prompt; this keeps the band fresh at the end of a turn too (BM-6).
  on('turn.complete', async ($, e, next) => {
    $.ui.invalidate('ui.render')
    return next(e)
  })
}
