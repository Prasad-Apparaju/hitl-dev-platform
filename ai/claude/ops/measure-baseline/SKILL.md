---
description: "Capture a performance baseline BEFORE a change lands, so the post-change measurement can be compared against it and the perf budget enforced. Run on any change carrying the `perf` tag, during the Design phase after Impact Analysis and before code is written — the recorded baseline is what `perf_budget_met` is later evaluated against."
argument-hint: "[change ID, e.g. 'GH-42'] [--scenario name]"
disable-model-invocation: true
---

**Before doing anything else:** Check whether `.hitl/` exists in the current directory. If it does not, stop immediately and output this — do not proceed with any steps:

```
This project hasn't been set up for HITL.
To get started, run one of these commands in your project directory:

  /hitl:dev-start-from-prd      new project from a PRD
  /hitl:dev-start-brownfield    adopt HITL on an existing codebase
  /hitl:dev-start-migration     migrate a system
```

---


# Measure Performance Baseline

Capture a reproducible performance baseline on the **pre-change** code so the after/before comparison is possible and the perf budget can be enforced later.

**Input:** $ARGUMENTS
- `<change-ID>` — the change being measured
- `--scenario <name>` — optional: measure a single named scenario instead of all configured ones

**Refusal rule:** If `.hitl/current-change.yaml` does not carry the `perf` tag, stop: "This change is not tagged `perf` — a baseline is only required for performance changes. Add the `perf` tag via `/hitl:dev-apply-change` if a perf budget applies, otherwise skip this step."

The baseline must be captured against the code **as it is before the change** — the current `HEAD` of the change branch with no implementation applied, or the base branch. If implementation has already started, baseline against the base branch commit and note it.

---

## Required tools

This skill shells out to whatever benchmark/profiling tool the project already uses. Detect what is present; only the matching tool is needed. If none is found, ask the operator which to use rather than guessing.

| Domain | Common tools | Baseline command (example) |
|---|---|---|
| HTTP / API latency + throughput | `k6`, `wrk`, `hey`, `ab`, `vegeta` | `k6 run --summary-export=baseline.json bench.js` |
| Micro-benchmarks (code) | `pytest-benchmark`, `go test -bench`, `cargo bench` / `criterion`, `jmh`, `benchmark.js` | `pytest --benchmark-json=baseline.json` · `go test -bench=. -benchmem` |
| Query / DB | `EXPLAIN ANALYZE`, `pgbench` | `pgbench -t 1000 -c 10` |
| Frontend / page load | `lighthouse`, Playwright traces, `web-vitals` | `lighthouse <url> --output=json --output-path=baseline.json` |
| Build / cold-start time | `hyperfine`, `time` | `hyperfine -N './build.sh'` |

If the matching tool is not installed, report exactly which one to install (and the install command if known), then stop — do not fabricate numbers or substitute an untested tool.

---

## Progress Banners

Format: `---` line, `**Measure Baseline — Step N / 4: [Name]**`, trail, `---`.

| Step | Name | Banner trail |
|---|---|---|
| 1 | Scope + scenarios | `▶ Scope · ○ Run · ○ Record · ○ Set budget` |
| 2 | Run benchmark | `✅ Scope · ▶ Run · ○ Record · ○ Set budget` |
| 3 | Record baseline | `✅ Scope · ✅ Run · ▶ Record · ○ Set budget` |
| 4 | Set the budget | `✅ Scope · ✅ Run · ✅ Record · ▶ Set budget` |

---

## Step 1 — Scope the metrics and scenarios

Read `.hitl/current-change.yaml`:
- `tags` — confirm `perf` is present
- `impact` / impact-analysis output — identify which code path or endpoint the change targets
- any existing `perf_baseline` block (a re-run overwrites it; note the previous values)

State the baseline plan before running anything:

```
Baseline plan — <ChangeID>
──────────────────────────
Target:        <endpoint / function / query / page the change affects>
Metric(s):     <p50 / p95 latency · throughput (req/s) · ns/op · allocs/op · query ms · LCP …>
Scenario(s):   <named load profiles or input sizes>
Tool:          <detected tool>
Measured against: <git ref — base branch / pre-change HEAD>  (commit <sha>)
Environment:   <local / dedicated bench host — note it; baselines are only comparable on like hardware>
```

If the target is ambiguous, ask the operator which path to measure — a baseline on the wrong path is worse than none.

---

## Step 2 — Run the benchmark

Run the detected tool against the pre-change code. Rules for a trustworthy baseline:

- **Warm up.** Discard the first run(s); steady-state numbers only.
- **Repeat.** Run at least 3 iterations (or the tool's built-in repetition) and capture min / median / max — a single number is noise.
- **Isolate.** Note background load; close competing processes. Record the environment in the result.
- **Export machine-readable output** where the tool supports it (`--benchmark-json`, `--summary-export`, `--output=json`) — store it as evidence, not just the console summary.

```
Baseline run — <ISO timestamp>
──────────────────────────────
  <metric>   median <v>   p95 <v>   min <v>   max <v>   (n=<iterations>)
  <metric>   median <v>   ...
```

If the benchmark cannot run (missing fixtures, unbuildable pre-change state), stop and report what is blocking it — do not record a partial baseline as if it were complete.

---

## Step 3 — Record the baseline

The baseline is the evidence later steps compare against. Record it in two places.

**On the GitHub issue** (durable, visible to reviewers):

```bash
gh issue comment <issue-number> \
  --body "## 📊 Performance Baseline Captured

**Measured against:** \`<git ref>\` (commit <sha>)
**Tool:** <tool>  ·  **Environment:** <env>

| Metric | Median | p95 | Min | Max |
|---|---|---|---|---|
| <metric> | <v> | <v> | <v> | <v> |

Raw export attached / committed at \`<path>\`. This is the pre-change baseline for the perf budget."
```

**In `.hitl/current-change.yaml`:**

```yaml
perf_baseline:
  captured_at: <ISO timestamp>
  measured_against: <git ref>
  commit: <sha>
  tool: <tool>
  environment: <local | bench-host>
  metrics:
    - { name: <metric>, median: <v>, p95: <v>, min: <v>, max: <v>, unit: <ms|req/s|ns/op|…> }
  raw: <path to exported json, if any>
```

Commit the raw export file alongside the change if the project keeps benchmark artifacts; otherwise the issue comment is the system of record.

---

## Step 4 — Set the perf budget

A baseline with no budget cannot be enforced. Propose a budget per metric — the threshold the post-change measurement must satisfy — and get the operator to confirm it.

- Default for a non-perf-targeting change that happens to carry the tag: **no regression** (post-change median ≤ baseline median, within a stated noise margin, e.g. +5%).
- For a change whose goal is a speedup: an **improvement target** (e.g. p95 ≤ 60% of baseline).
- State the noise margin explicitly — benchmarks are not exact; a budget tighter than measurement noise is unenforceable.

Record the budget so the verify step can check `perf_budget_met`:

```yaml
perf_budget:
  set_at: <ISO timestamp>
  set_by: <operator>
  targets:
    - { metric: <metric>, direction: no-regression | improve, threshold: "<expr>", noise_margin: "<e.g. ±5%>" }
```

**On success**, report: "Baseline captured for `<ChangeID>` and budget set. Post-change measurement (during Verify) must satisfy: `<budget summary>`. `perf_baseline` and `perf_budget` recorded on the issue and in current-change.yaml."

**If the baseline could not be captured**, do not write `perf_baseline` — report what blocked it. The `perf` tag's `perf_budget_met` evidence cannot be produced without a baseline, so the change cannot complete until this is resolved.

---

## When to Run

| Workflow step | Gate |
|---|---|
| Design phase, after Impact Analysis, before implementation (`perf` tag only) | `perf_baseline` + `perf_budget` must exist before code is written — you cannot baseline code that already contains the change |
| Verify phase | the post-change measurement is compared against `perf_baseline`; the result sets `perf_budget_met` required evidence |

---

## Important Rules

- Baseline the code **before** the change, not after — a baseline taken on already-changed code measures nothing.
- A baseline measured on different hardware than the post-change run is not comparable — record the environment and keep both runs on the same host.
- One number is not a baseline — capture median + spread over multiple iterations.
- No budget means no enforcement — Step 4 is not optional.
- Do not fabricate or estimate numbers when the tool is missing or the bench cannot run — report the blocker instead.
