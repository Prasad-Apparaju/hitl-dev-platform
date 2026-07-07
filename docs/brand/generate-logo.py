"""HITL logo generator (final: the temple scene).

Bottom: the team, evenly spaced, seated on the floor, each with their AI spark.
Middle: the doc repo, slightly elevated; everyone reads AND writes it (double
arrows). Top: the system, standing high above, built FROM the docs; a spark
rides the docs-to-system link (AI carries the docs into the build). Handoff chevrons between people show the work moving role to role (via the
docs). A dotted +1 person shows the team is extensible.

Regenerate SVGs:   python3 docs/brand/generate-logo.py
Rasterize PNGs:    see docs/brand/README.md
"""
import math, pathlib

P = dict(ink="#26242E", ring="#1E8E6E", paper="#FAF7F0", lines="#1E8E6E", spark="#1E8E6E",
         core_r="#17715B", code="#3FBF94", ghost="#9AA3AE",
         roles=["#C75B39", "#7D5BA6", "#C99A2C", "#B54A66", "#4E7DA0"])
D = dict(ink="#F5F2EA", ring="#2FBF94", paper="#FAF7F0", lines="#1E8E6E", spark="#2FBF94",
         core_r="#1E8E6E", code="#3FBF94", ghost="#6E7787",
         roles=["#E0764F", "#9B79C4", "#E0B04A", "#D66A85", "#6FA3C7"], bg="#211F29")

def spark(cx, cy, s, col):
    return (f'<path transform="translate({cx},{cy}) scale({s})" fill="{col}" '
            f'd="M0,-11 L3,-3 L11,0 L3,3 L0,11 L-3,3 L-11,0 L-3,-3 Z"/>')

def person(cx, cy, s, col, dotted=False, c=None):
    if dotted:
        return (f'<g transform="translate({cx},{cy}) scale({s})" fill="none" '
                f'stroke="{col}" stroke-width="3" stroke-dasharray="4 4">'
                f'<circle cx="0" cy="-14" r="13"/><rect x="-20" y="4" width="40" height="24" rx="12"/></g>')
    return (f'<g transform="translate({cx},{cy}) scale({s})" fill="{col}">'
            f'<circle cx="0" cy="-14" r="13"/><rect x="-20" y="4" width="40" height="24" rx="12"/></g>')

def darrow(x1, y1, x2, y2, col, w=6, head=8, dashed=False):
    """Double-headed arrow: read AND write."""
    ang1 = math.degrees(math.atan2(y1-y2, x1-x2))
    ang2 = math.degrees(math.atan2(y2-y1, x2-x1))
    ux, uy = x2-x1, y2-y1
    L = math.hypot(ux, uy); ux, uy = ux/L, uy/L
    sx, sy = x1+ux*head, y1+uy*head
    ex, ey = x2-ux*head, y2-uy*head
    dash = ' stroke-dasharray="1 11"' if dashed else ''
    tip = 'fill="none" stroke="%s" stroke-width="2.5"' if dashed else 'fill="%s"'
    a = f'<line x1="{sx:.0f}" y1="{sy:.0f}" x2="{ex:.0f}" y2="{ey:.0f}" stroke="{col}" stroke-width="{w}" stroke-linecap="round"{dash}/>'
    a += f'<polygon points="{head+4},0 -6,{head} -6,-{head}" {tip % col} transform="translate({x2:.0f},{y2:.0f}) rotate({ang2:.0f})"/>'
    a += f'<polygon points="{head+4},0 -6,{head} -6,-{head}" {tip % col} transform="translate({x1:.0f},{y1:.0f}) rotate({ang1:.0f})"/>'
    return a

def icon(c, bg=None, size=512, name=True):
    parts = [f'<rect width="512" height="512" fill="{bg}"/>' if bg else '']
    cxm = 256

    # ── the system, high above: wireframe cube with emerald core + code ──
    parts.append(f'''<g transform="translate({cxm},128)">
      <g fill="none" stroke="{c['ink']}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round">
        <polygon points="0,-80 38,-61 0,-42 -38,-61"/>
        <line x1="-38" y1="-61" x2="-38" y2="-25"/>
        <line x1="38"  y1="-61" x2="38"  y2="-25"/>
        <line x1="0"   y1="-42" x2="0"   y2="-6"/>
        <polyline points="-38,-25 0,-6 38,-25"/>
      </g>
      <polygon points="0,-59 15,-51 0,-43 -15,-51" fill="{c['spark']}"/>
      <polygon points="-15,-51 0,-43 0,-28 -15,-36" fill="{c['lines']}"/>
      <polygon points="15,-51 0,-43 0,-28 15,-36" fill="{c['core_r']}"/>
      <text x="0" y="-12" text-anchor="middle" font-family="Menlo, Consolas, monospace"
            font-weight="bold" font-size="14" fill="{c['code']}">&lt;/&gt;</text>
    </g>''')

    # ── docs -> system link, with the AI spark riding it ──
    parts.append(f'<line x1="{cxm}" y1="{198}" x2="{cxm}" y2="{140}" stroke="{c["ring"]}" stroke-width="7" stroke-linecap="round"/>')
    parts.append(f'<polygon points="12,0 -8,10 -8,-10" fill="{c["ring"]}" transform="translate({cxm},134) rotate(-90)"/>')
    parts.append(spark(cxm+24, 166, 1.15, c['spark']))

    # ── the doc repo, slightly elevated: a two-page stack ──
    parts.append(f'''<g transform="translate({cxm},246)">
      <g transform="translate(10,-8) scale(1.02)" opacity="0.5">
        <path d="M -30 -38 L 14 -38 L 30 -22 L 30 38 L -30 38 Z" fill="{c['paper']}" stroke="{c['ink']}" stroke-width="4" stroke-linejoin="round"/>
      </g>
      <g transform="scale(1.06)">
        <path d="M -30 -38 L 14 -38 L 30 -22 L 30 38 L -30 38 Z" fill="{c['paper']}" stroke="{c['ink']}" stroke-width="5" stroke-linejoin="round"/>
        <path d="M 14 -38 L 14 -22 L 30 -22 Z" fill="{c['lines']}"/>
        <rect x="-18" y="-10" width="36" height="6" rx="3" fill="{c['lines']}"/>
        <rect x="-18" y="5"  width="36" height="6" rx="3" fill="{c['lines']}"/>
        <rect x="-18" y="20" width="23" height="6" rx="3" fill="{c['lines']}" opacity="0.55"/>
      </g>
    </g>''')

    # ── the team on the floor: 5 seated people + dotted +1, evenly spaced ──
    xs = [66, 142, 218, 294, 370, 446]
    doc_bottom_y = 292
    for i, x in enumerate(xs):
        is_ghost = (i == len(xs)-1)
        col = c['ghost'] if is_ghost else c['roles'][i]
        # read/write connection: from just above the spark to the doc repo underside
        tx = cxm + (x - cxm) * 0.16
        if is_ghost:
            parts.append(darrow(x, 340, tx, doc_bottom_y, c['ghost'], w=4, head=7, dashed=True))
            parts.append(person(x, 392, 1.1, c['ghost'], dotted=True))
            parts.append(f'<text x="{x+20}" y="{368}" font-family="\'Helvetica Neue\', Helvetica, Arial, sans-serif" '
                         f'font-weight="700" font-size="24" fill="{c["ghost"]}">+</text>')
        else:
            parts.append(darrow(x, 340, tx, doc_bottom_y, c['ring'], w=5, head=8))
            parts.append(person(x, 392, 1.1, col))
            parts.append(spark(x+19, 356, 1.0, c['spark']))
    # handoff chevrons: the work moves person to person, via the docs above
    for i in range(len(xs)-1):
        mx = (xs[i] + xs[i+1]) / 2
        last = (i == len(xs)-2)
        col = c['ghost'] if last else c['ring']
        dash = ' stroke-dasharray="3 5"' if last else ''
        parts.append(f'<polyline points="{mx-6:.0f},396 {mx+6:.0f},404 {mx-6:.0f},412" fill="none" '
                     f'stroke="{col}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"'
                     f'{dash} opacity="0.8"/>')
    # floor line
    parts.append(f'<line x1="40" y1="424" x2="472" y2="424" stroke="{c["ink"]}" stroke-width="3" '
                 f'stroke-linecap="round" opacity="0.35"/>')

    if name:
        parts.append(f'<text x="256" y="486" text-anchor="middle" font-family="\'Helvetica Neue\', Helvetica, Arial, sans-serif" '
                     f'font-weight="800" font-size="52" letter-spacing="6" fill="{c["ink"]}">HITL</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 512 512">{"".join(parts)}</svg>')

def inner(svg): return svg.split(">",1)[1].rsplit("</svg>",1)[0]

def lockup(c, bg=None):
    w, h = 1180, 360
    ic = inner(icon(c, name=False))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
{f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ''}
<g transform="translate(30,10) scale(0.78) translate(0,-30)">{ic}</g>
<text x="450" y="250" font-family="'Helvetica Neue', Helvetica, Arial, sans-serif" font-weight="800"
      font-size="190" letter-spacing="8" fill="{c['ink']}">HITL</text>
</svg>'''

out = pathlib.Path(__file__).resolve().parent
out.joinpath("hitl-icon.svg").write_text(icon(P))
out.joinpath("hitl-icon-dark.svg").write_text(icon(D, bg=D["bg"]))
out.joinpath("hitl-logo.svg").write_text(lockup(P))
out.joinpath("hitl-logo-dark.svg").write_text(lockup(D, bg=D["bg"]))
print("wrote temple-scene finals")
