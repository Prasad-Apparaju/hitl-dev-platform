"""HITL logo generator (final: hub-and-spoke).

Five role+AI pairs (PM, Architect, Dev, QA, Ops) connect via spokes into the
shared doc, which fronts the 3D system being built; code flows in. Arrowheads
terminate each spoke at the hub: every role collaborates THROUGH the docs.

Regenerate SVGs:   python3 docs/brand/generate-logo.py
Rasterize PNGs:    see docs/brand/README.md
"""
import math, pathlib

P = dict(ink="#26242E", ring="#1E8E6E", paper="#FAF7F0", lines="#1E8E6E", spark="#1E8E6E",
         core_r="#17715B", code="#3FBF94",
         roles=["#C75B39", "#7D5BA6", "#C99A2C", "#B54A66", "#4E7DA0"])
D = dict(ink="#F5F2EA", ring="#2FBF94", paper="#FAF7F0", lines="#1E8E6E", spark="#2FBF94",
         core_r="#1E8E6E", code="#3FBF94",
         roles=["#E0764F", "#9B79C4", "#E0B04A", "#D66A85", "#6FA3C7"], bg="#211F29")

def center_art(cx, cy, s, c):
    """Flat classic doc as the BASE; outlined 3D system cube standing on it,
    with a solid mini-cube (the system's core) visible inside the wireframe."""
    return f'''<g transform="translate({cx},{cy}) scale({s})">
      <!-- outlined system cube, resting on the doc's top edge -->
      <g fill="none" stroke="{c['ink']}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round">
        <polygon points="0,-84 40,-64 0,-44 -40,-64"/>
        <line x1="-40" y1="-64" x2="-40" y2="-26"/>
        <line x1="40"  y1="-64" x2="40"  y2="-26"/>
        <line x1="0"   y1="-44" x2="0"   y2="-6"/>
        <polyline points="-40,-26 0,-6 40,-26"/>
      </g>
      <!-- detail inside: solid emerald core -->
      <g>
        <polygon points="0,-62 16,-54 0,-46 -16,-54" fill="{c['spark']}"/>
        <polygon points="-16,-54 0,-46 0,-30 -16,-38" fill="{c['lines']}"/>
        <polygon points="16,-54 0,-46 0,-30 16,-38" fill="{c['core_r']}"/>
      </g>
      <!-- flat classic doc: the base -->
      <g transform="translate(0,43) scale(1.28)">
        <path d="M -30 -38 L 14 -38 L 30 -22 L 30 38 L -30 38 Z" fill="{c['paper']}" stroke="{c['ink']}" stroke-width="5" stroke-linejoin="round"/>
        <path d="M 14 -38 L 14 -22 L 30 -22 Z" fill="{c['lines']}"/>
        <rect x="-18" y="-10" width="36" height="6" rx="3" fill="{c['lines']}"/>
        <rect x="-18" y="5"  width="36" height="6" rx="3" fill="{c['lines']}"/>
        <rect x="-18" y="20" width="23" height="6" rx="3" fill="{c['lines']}" opacity="0.55"/>
      </g>
      <!-- code flowing in -->
      <g font-family="Menlo, Consolas, monospace" font-weight="bold" fill="{c['code']}">
        <text x="58" y="-78" font-size="17" opacity="0.85">&lt;/&gt;</text>
        <text x="40" y="-54" font-size="13" opacity="0.55">&lt;/&gt;</text>
      </g>
    </g>'''

def spark(cx, cy, s, col):
    return (f'<path transform="translate({cx},{cy}) scale({s})" fill="{col}" '
            f'd="M0,-11 L3,-3 L11,0 L3,3 L0,11 L-3,3 L-11,0 L-3,-3 Z"/>')

def pair(cx, cy, s, human, c):
    return f'''<g transform="translate({cx},{cy}) scale({s})">
      <g fill="{human}" transform="translate(-4,0)">
        <circle cx="0" cy="-12" r="14"/><rect x="-21" y="6" width="42" height="24" rx="12"/>
      </g>
      {spark(20,-16,1.05,c['spark'])}
    </g>'''

def icon(c, bg=None, size=512, name=True):
    cx, cy = 256, 226
    R_pair, R_out, R_in = 168, 138, 96
    parts = [f'<rect width="512" height="512" fill="{bg}"/>' if bg else '']
    for i in range(5):
        t = math.radians(90 + i*72)
        ux, uy = math.cos(t), -math.sin(t)                 # screen-space unit outward
        ox, oy = cx + ux*R_out, cy + uy*R_out
        ix, iy = cx + ux*R_in,  cy + uy*R_in
        parts.append(f'<line x1="{ox:.0f}" y1="{oy:.0f}" x2="{ix:.0f}" y2="{iy:.0f}" '
                     f'stroke="{c["ring"]}" stroke-width="13" stroke-linecap="round"/>')
        ang = math.degrees(math.atan2(-uy, -ux))            # arrowhead at the END, into the hub
        parts.append(f'<polygon points="20,0 -9,14 -9,-14" fill="{c["ring"]}" '
                     f'transform="translate({ix:.0f},{iy:.0f}) rotate({ang:.0f})"/>')
    parts.append(center_art(cx, cy-6, 0.90, c))
    for i, col in enumerate(c['roles']):
        t = math.radians(90 + i*72)
        nx = cx + R_pair*math.cos(t); ny = cy - R_pair*math.sin(t)
        parts.append(pair(nx, ny+4, 1.14, col, c))
    if name:
        parts.append(f'<text x="256" y="478" text-anchor="middle" font-family="\'Helvetica Neue\', Helvetica, Arial, sans-serif" '
                     f'font-weight="800" font-size="60" letter-spacing="6" fill="{c["ink"]}">HITL</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 512 512">{"".join(parts)}</svg>')

def inner(svg): return svg.split(">",1)[1].rsplit("</svg>",1)[0]

def lockup(c, bg=None):
    w, h = 1180, 360
    ic = inner(icon(c, name=False))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
{f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ''}
<g transform="translate(30,35) scale(0.72) translate(0,-30)">{ic}</g>
<text x="420" y="252" font-family="'Helvetica Neue', Helvetica, Arial, sans-serif" font-weight="800"
      font-size="190" letter-spacing="8" fill="{c['ink']}">HITL</text>
</svg>'''

out = pathlib.Path(__file__).resolve().parent
out.joinpath("hitl-icon.svg").write_text(icon(P))
out.joinpath("hitl-icon-dark.svg").write_text(icon(D, bg=D["bg"]))
out.joinpath("hitl-logo.svg").write_text(lockup(P))
out.joinpath("hitl-logo-dark.svg").write_text(lockup(D, bg=D["bg"]))
print("wrote v5 hub-spoke finals")
