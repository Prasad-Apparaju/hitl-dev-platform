// HITL breadcrumb band (FR-37, BM-1 to BM-7). A Claude Code mod that draws the breadcrumb as a
// band above the prompt when `.hitl/config.yaml` says `breadcrumb: band` or `breadcrumb: both`.
//
// Draw-only. It reads two files, resolves UI elements and asks for a redraw at the end of each
// turn. It never parses the change file, never renders the ribbon, and never handles tools,
// permissions, commands, the model, the clock or the network. `_steps.sh` is the one renderer:
// welcome.sh and statusline-hitl.sh write its output to `.hitl/breadcrumb.txt` (line 1 ribbon,
// line 2 step line, line 3 next-step hint, line 4 warning) and this mod only shows that text.
//
// Validated footprint: hooks ui.render{component=AbovePrompt} and turn.complete; calls
// $.fs.exists, $.fs.read, $.ui.resolve, $.ui.invalidate. ci/breadcrumb-mod/ fails on anything else.

// The team setting: 'text' (default, also when the file or key is absent), 'band' or 'both'.
async function readMode($) {
  if (!(await $.fs.exists('.hitl/config.yaml'))) return 'text'
  const found = /^breadcrumb:\s*([a-z]+)/m.exec(asText(await $.fs.read('.hitl/config.yaml')))
  return found ? found[1] : 'text'
}

// The renderer's cache, or null when there is nothing to show. Four lines: ribbon, step line,
// next-step hint, branch warning.
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
  }
}

function asText(raw) {
  return typeof raw === 'string' ? raw : ''
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
    if (cache.step !== '') rows.push(Text({ wrap: 'truncate-end', children: [cache.step] }))
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
