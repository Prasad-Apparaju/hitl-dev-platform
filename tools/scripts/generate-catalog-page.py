#!/usr/bin/env python3
"""Generate the portal's catalog page (site/catalog.html) from the workflow catalog.

The page lists every workflow, phase, step, and substep as a collapsible tree. It is
GENERATED so it cannot drift from tools/workflow-catalog/catalog.yaml — the same file
the derive gate verifies against the shipped runtime. Run from the repo root:

    python3 tools/scripts/generate-catalog-page.py

The Pages deploy workflow (.github/workflows/pages.yml) runs this on every deploy, so
the LIVE page always reflects the committed catalog even if the checked-in
site/catalog.html is stale.

Dependencies: Python 3.10+, PyYAML.
"""

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "workflow-catalog"))

import yaml  # noqa: E402
from derive import derive_steps, total_of, workflow_steps  # noqa: E402

# Portal presentation order. The portal documents the current 2.x line (hitl@hitl),
# which includes the docs workflow; 1.x (hitl-1x@hitl) is legacy reference.
ORDER = [
    ("spine", "Development — deliver a change", "the delivery spine every enhancement runs on"),
    ("docs", "Docs — documentation-only changes", "tracked route for docs PRs, reviewer routed by domain"),
    ("brownfield", "Brownfield — onboard an existing codebase", "run once per existing project"),
    ("greenfield", "PRD — stand up a greenfield project", "run once per new project"),
    ("migration", "Migration — set up a target system", "run once per migration"),
    ("migration_review", "Migration Review — vet external docs", "architect gate before migration design"),
    ("platform", "Platform Bootstrap — onboarded to delivery-ready", "long-lived, per project; drives the readiness register"),
]


def esc(value):
    return html.escape(str(value or ""))


def build_fragment(catalog):
    out = []
    total_rows = 0
    for cat_name, title, note in ORDER:
        raw = workflow_steps(catalog, cat_name)
        if cat_name == "spine":
            # The shipped development workflow is the spine base (no conditionals).
            raw = [s for s in raw if "cond" not in s]
        derived = derive_steps(raw)
        conds = {s["key"]: s.get("cond") for s in raw if s.get("cond")}
        total = total_of(derived)
        substeps = sum(1 for d in derived if not d["n"].isdigit())
        total_rows += len(derived)

        phases, seen = [], set()
        for d in derived:
            if d["phase"] not in seen:
                seen.add(d["phase"])
                phases.append(d["phase"])

        count_txt = f"{total} steps"
        if substeps:
            count_txt += f" + {substeps} substep" + ("s" if substeps > 1 else "")
        out.append(
            f'<details class="wf"><summary><span class="sumleft">'
            f'<span class="wfname">{esc(title)}</span>'
            f'<div class="oneliner">{esc(note)}</div></span>'
            f'<span class="wfmeta">{count_txt} · {len(phases)} phase'
            f'{"s" if len(phases) > 1 else ""}</span></summary>'
        )
        out.append('<div class="wfbody">')
        for ph in phases:
            steps = [d for d in derived if d["phase"] == ph]
            n_main = sum(1 for s in steps if s["n"].isdigit())
            out.append(
                f'<details class="phase" open><summary><span class="phname">{esc(ph)}</span>'
                f'<span class="phcount">{n_main} step{"s" if n_main != 1 else ""}</span></summary>'
            )
            for d in steps:
                sub = not d["n"].isdigit()
                badge = '<span class="mig">migration only</span>' if conds.get(d["key"]) == "migration" else ""
                cmd = d["command"] or "—"
                cmd_disp = f"/hitl:{cmd}" if cmd not in ("manual", "guided", "—") else cmd
                out.append(
                    f'<details class="steprow{" sub" if sub else ""}"><summary>'
                    f'<span class="num">{esc(d["n"])}</span>'
                    f'<span class="sname">{esc(d["name"])}</span>{badge}'
                    f'<span class="srole">{esc(d["role"] or "")}</span></summary>'
                    f'<div class="smeta"><span class="mk">key</span><code>{esc(d["key"])}</code>'
                    f'<span class="mk">executed by</span><code>{esc(cmd_disp)}</code>'
                    f'<span class="mk">owner</span><code>{esc(d["role"] or "—")}</code>'
                    f'<span class="mk">position</span><code>{esc(d["phase_step"])}</code></div></details>'
                )
            out.append("</details>")
        out.append("</div></details>")
    header = (
        f"<!-- generated from tools/workflow-catalog/catalog.yaml · "
        f"{len(ORDER)} workflows · {total_rows} step rows -->"
    )
    return header + "\n" + "\n".join(out)


SHELL = """<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="assets/hitl-icon.svg">
<title>The complete HITL workflow catalog — every phase, step, and substep</title>
<style>
  :root {
    --ground: #F5F8F6; --panel: #FFFFFF; --ink: #1F2823; --ink-soft: #52645B;
    --line: #D6E0DA; --pine: #17453B; --leaf: #2E7D64; --leaf-wash: #E8F0EC;
    --gate: #A66B1F; --gate-wash: #F7EEDD;
    --mono: "Menlo", "SF Mono", "Consolas", monospace;
    --display: "Avenir Next", "Seravek", "Gill Sans", "Segoe UI", system-ui, sans-serif;
    --body: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  }
  @media (prefers-color-scheme: dark) {
    :root { --ground: #0F1713; --panel: #17211C; --ink: #E5EDE8; --ink-soft: #9AB0A5;
      --line: #2A3830; --pine: #57BD99; --leaf: #57BD99; --leaf-wash: #1C2A24;
      --gate: #D99A45; --gate-wash: #2A2115; }
  }
  :root[data-theme="dark"] {
    --ground: #0F1713; --panel: #17211C; --ink: #E5EDE8; --ink-soft: #9AB0A5;
    --line: #2A3830; --pine: #57BD99; --leaf: #57BD99; --leaf-wash: #1C2A24;
    --gate: #D99A45; --gate-wash: #2A2115;
  }
  :root[data-theme="light"] {
    --ground: #F5F8F6; --panel: #FFFFFF; --ink: #1F2823; --ink-soft: #52645B;
    --line: #D6E0DA; --pine: #17453B; --leaf: #2E7D64; --leaf-wash: #E8F0EC;
    --gate: #A66B1F; --gate-wash: #F7EEDD;
  }
  * { box-sizing: border-box; }
  body { background: var(--ground); color: var(--ink); font-family: var(--body);
    margin: 0; padding: 48px 20px 80px; line-height: 1.5; font-size: 15px; }
  .wrap { max-width: 880px; margin: 0 auto; }
  .sitenav { display: flex; flex-wrap: wrap; gap: 4px 14px; align-items: baseline;
    font-family: var(--mono); font-size: 11.5px; margin-bottom: 34px; }
  .sitenav .navbrand { font-weight: 700; letter-spacing: 0.14em; color: var(--leaf); margin-right: 8px; }
  .sitenav a { color: var(--ink-soft); text-decoration: none; padding: 2px 0; border-bottom: 1px solid transparent; }
  .sitenav a:hover { color: var(--pine); border-bottom-color: var(--leaf); }
  .sitenav a.here { color: var(--pine); font-weight: 700; border-bottom: 1.5px solid var(--leaf); }
  .sitenav a:focus-visible { outline: 2px solid var(--leaf); outline-offset: 2px; }

  header h1 { font-family: var(--display); font-size: 30px; font-weight: 600;
    margin: 0 0 10px; letter-spacing: -0.01em; text-wrap: balance; }
  header .sub { color: var(--ink-soft); margin: 0 0 8px; max-width: 66ch; }
  .legend { font-family: var(--mono); font-size: 11.5px; color: var(--ink-soft); margin-bottom: 14px; }
  .legend b { color: var(--leaf); }
  .controls { display: flex; gap: 10px; margin-bottom: 24px; }
  .controls button {
    font-family: var(--mono); font-size: 11.5px; color: var(--pine); background: var(--leaf-wash);
    border: 1px solid var(--line); border-radius: 5px; padding: 5px 12px; cursor: pointer;
  }
  .controls button:hover { border-color: var(--leaf); }
  .controls button:focus-visible { outline: 2px solid var(--leaf); outline-offset: 2px; }

  details.wf { background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
    margin-bottom: 12px; border-top: 3px solid var(--leaf); }
  details.wf > summary { padding: 15px 18px; cursor: pointer; list-style: none;
    display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  details.wf > summary::-webkit-details-marker { display: none; }
  details.wf > summary::before { content: "▸"; color: var(--leaf); margin-right: 10px; }
  details[open].wf > summary::before { content: "▾"; }
  details.wf > summary:focus-visible { outline: 2px solid var(--leaf); outline-offset: 2px; border-radius: 8px; }
  .sumleft { flex: 1; min-width: 240px; }
  .wfname { font-family: var(--display); font-size: 17px; font-weight: 600; }
  .oneliner { color: var(--ink-soft); font-size: 13px; margin-top: 2px; }
  .wfmeta { font-family: var(--mono); font-size: 11px; color: var(--leaf); font-weight: 700; white-space: nowrap; }
  .wfbody { border-top: 1px solid var(--line); padding: 12px 16px 14px; display: flex; flex-direction: column; gap: 10px; }

  details.phase { border: 1px solid var(--line); border-radius: 6px; background: var(--ground); }
  details.phase > summary { padding: 9px 13px; cursor: pointer; list-style: none;
    display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
  details.phase > summary::-webkit-details-marker { display: none; }
  .phname { font-family: var(--display); font-size: 13.5px; font-weight: 600;
    letter-spacing: 0.06em; text-transform: uppercase; color: var(--pine); }
  .phname::before { content: "▸ "; color: var(--leaf); }
  details[open].phase .phname::before { content: "▾ "; }
  details.phase > summary:focus-visible { outline: 2px solid var(--leaf); outline-offset: 2px; }
  .phcount { font-family: var(--mono); font-size: 10.5px; color: var(--ink-soft); }

  details.steprow { border-top: 1px solid var(--line); background: var(--panel); }
  details.steprow:last-child { border-radius: 0 0 6px 6px; }
  details.steprow > summary { padding: 8px 13px; cursor: pointer; list-style: none;
    display: flex; align-items: baseline; gap: 10px; }
  details.steprow > summary::-webkit-details-marker { display: none; }
  details.steprow > summary:focus-visible { outline: 2px solid var(--leaf); outline-offset: -2px; }
  details.steprow.sub > summary { padding-left: 34px; }
  details.steprow.sub .num { border-style: dashed; }
  .num { font-family: var(--mono); font-size: 10.5px; font-weight: 700; color: var(--leaf);
    border: 1.5px solid var(--leaf); border-radius: 10px; padding: 0 7px; min-width: 30px;
    text-align: center; font-variant-numeric: tabular-nums; flex-shrink: 0; }
  .sname { font-size: 13.5px; flex: 1; }
  .srole { font-family: var(--mono); font-size: 10px; color: var(--ink-soft); letter-spacing: 0.06em; }
  .mig { font-family: var(--mono); font-size: 9.5px; font-weight: 700; color: var(--gate);
    border: 1px solid var(--gate); border-radius: 3px; padding: 0 5px; letter-spacing: 0.05em; }
  .smeta { padding: 4px 13px 10px 53px; display: flex; flex-wrap: wrap; gap: 4px 14px;
    font-size: 12px; color: var(--ink-soft); }
  details.steprow.sub .smeta { padding-left: 74px; }
  .smeta code { font-family: var(--mono); font-size: 11.5px; color: var(--pine); }
  .mk { font-family: var(--mono); font-size: 9.5px; font-weight: 700; letter-spacing: 0.08em;
    color: var(--ink-soft); align-self: baseline; }

  .navlogo {
    width: 18px; height: 18px; display: inline-block; vertical-align: -3px; margin-right: 7px;
    background: url("assets/hitl-icon.svg") no-repeat center / contain;
  }
  @media (prefers-color-scheme: dark) { .navlogo { background-image: url("assets/hitl-icon-dark.svg"); } }
  :root[data-theme="dark"] .navlogo { background-image: url("assets/hitl-icon-dark.svg"); }
  :root[data-theme="light"] .navlogo { background-image: url("assets/hitl-icon.svg"); }

  footer { margin-top: 44px; color: var(--ink-soft); font-size: 12px; font-family: var(--mono); }
</style>

<div class="wrap">
<nav class="sitenav"><span class="navbrand"><span class="navlogo" aria-hidden="true"></span>HITL</span><a href="index.html">Home</a><a href="going-ai-native.html">The walkthrough</a><a href="architecture.html">Architecture</a><a href="catalog.html" class="here">Full catalog</a></nav>

  <header>
    <h1>The complete workflow catalog</h1>
    <p class="sub">Every workflow, phase, step, and substep that ships in HITL — generated from the same catalog file the running system executes, so this page cannot drift from reality. Expand a workflow to see its phases, a phase to see its steps, and a step to see its stable key, executor, and owner.</p>
    <p class="legend">__LEGEND_COUNTS__ · executor is a <b>/hitl:*</b> skill, <b>manual</b> (a person), or <b>guided</b> (Claude follows a reference doc)</p>
  </header>

  <div class="controls">
    <button type="button" onclick="document.querySelectorAll('details').forEach(d=>d.open=true)">expand everything</button>
    <button type="button" onclick="document.querySelectorAll('details').forEach(d=>d.open=false)">collapse everything</button>
  </div>

__FRAGMENT__

  <footer>HITL v__VERSION__ (2.x line) · generated from tools/workflow-catalog/catalog.yaml — the file the derive gate verifies against the shipped runtime</footer>
</div>
"""


def main():
    catalog = yaml.safe_load((ROOT / "tools" / "workflow-catalog" / "catalog.yaml").read_text())
    fragment = build_fragment(catalog)
    out_path = ROOT / "site" / "catalog.html"
    total_rows = fragment.count('details class="steprow')
    substeps = fragment.count('details class="steprow sub"')
    steps = total_rows - substeps
    legend = f"<b>{len(ORDER)} workflows</b> · {steps} steps"
    if substeps:
        legend += f" + {substeps} substep" + ("s" if substeps > 1 else "")
    import json
    version = json.load(open(ROOT / "ai" / "claude" / "plugin" / "plugin.json"))["version"]
    out_path.write_text(SHELL.replace("__FRAGMENT__", fragment)
                        .replace("__LEGEND_COUNTS__", legend)
                        .replace("__VERSION__", version))
    rows = total_rows
    print(f"wrote {out_path.relative_to(ROOT)} ({rows} step rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
