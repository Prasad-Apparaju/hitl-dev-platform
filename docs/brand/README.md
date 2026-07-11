# docs/brand/

HITL brand assets. The mark: five role+AI pairs (PM, Architect, Dev, QA, Ops, each human
with a spark = their AI harness) connected hub-and-spoke into the shared document, which
fronts the 3D system being built, with code flowing in. Topology is the message: every
role collaborates through the docs, and all effort lands in the system.

Palette ("evergreen"): ink #26242E · emerald #1E8E6E · paper #FAF7F0 · roles: terracotta
#C75B39, plum #7D5BA6, ochre #C99A2C, rose #B54A66, steel #4E7DA0.

| File | Use |
|---|---|
| `hitl-logo.svg` / `.png` | Horizontal lockup, light backgrounds (PNG transparent) |
| `hitl-logo-dark.svg` / `.png` | Lockup for dark backgrounds (ink bg baked) |
| `hitl-icon.svg` + `hitl-icon-{512,256,64,32}.png` | Badge (name below mark): avatars, favicon |
| `hitl-icon-dark.svg` / `-512.png` | Badge on dark |
| `generate-logo.py` | The parameterized source. Edit palette/geometry here, never the SVGs. |

Regenerate:

```bash
python3 docs/brand/generate-logo.py   # writes the 4 SVGs
# rasterize (macOS, headless Chrome):
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
cd docs/brand
"$CHROME" --headless --disable-gpu --screenshot=hitl-icon-512.png --window-size=512,512 \
  --default-background-color=00000000 "file://$PWD/hitl-icon.svg"
for s in 256 64 32; do sips -Z $s hitl-icon-512.png --out hitl-icon-$s.png; done
```
