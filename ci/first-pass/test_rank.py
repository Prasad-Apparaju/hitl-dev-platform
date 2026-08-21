#!/usr/bin/env python3
"""Ranking the plan: the order a person reads, and what pins a step to the top."""
import os, sys, yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rank as R

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CAT = yaml.safe_load(open(os.path.join(ROOT, "tools", "workflow-catalog", "catalog.yaml")))
COSTS = CAT["step_costs"]
SPINE = [s for s in CAT["spine"]["steps"] if "cond" not in s]


def test_a_step_the_change_does_not_engage_drops_one_rank():
    """`iac` is medium on an infrastructure change and less than that on a copy fix."""
    e = COSTS["iac"]
    assert R.shown_rank(e, paths=["infra/main.tf"]) == "medium"
    assert R.shown_rank(e, paths=["docs/readme.md"]) == "low"


def test_an_incident_in_the_area_raises_one_rank():
    e = COSTS["docs"]
    assert R.shown_rank(e, paths=["docs/x.md"]) == "medium"
    assert R.shown_rank(e, paths=["docs/x.md"], risky_domain=True) == "high"


def test_modulation_never_moves_a_locked_step():
    """A floor or no_omit step is pinned to high however the signals fall — the rank and the flag
    must never disagree, or someone reading ranks drops something the flags protect."""
    for key in ("deploy", "promote", "red", "green"):
        assert R.shown_rank(COSTS[key], paths=["nothing/relevant"], locked=True) == "high"

    # The cases above are all base-high, so they pass even with the pin removed — mutation testing
    # caught that. `pentest` is floor AND engages only on a security change, so on any other change
    # the modulation WOULD demote it. That is the case the pin exists for.
    assert R.shown_rank(COSTS["pentest"], paths=["scripts/demo.sh"], profile="fix") == "medium", (
        "precondition: unlocked, this step demotes")
    assert R.shown_rank(COSTS["pentest"], paths=["scripts/demo.sh"], profile="fix",
                        locked=True) == "high", "a floor step must not be argued down the list"


def test_missing_data_degrades_quietly_rather_than_raising():
    """A project with no step_costs, no manifest and no registry still gets a usable order."""
    ranked = R.rank_plan(SPINE, {}, tier=1)
    assert len(ranked) == len(SPINE)
    assert all(r["rank"] in R.RANKS for r in ranked)
    assert R.shown_rank(None) == "medium"
    assert R.shown_rank({"forgo_cost": "banana"}) == "medium"
    assert R.risky_domains(None, None) == {}
    assert R.touches_risky(["a/b"], None) is False


def test_absent_engages_counts_as_engaged():
    """Guessing 'not engaged' would silently demote every step nobody annotated."""
    assert R.engaged(None) and R.engaged("") and R.engaged({}) is True


def test_locked_steps_sort_first_then_by_rank_then_catalog_order():
    ranked = R.rank_plan(SPINE, COSTS, tier=2, paths=["src/app.py"], profile="fix")
    locked = [r for r in ranked if r["locked"]]
    assert locked and all(r["locked"] for r in ranked[:len(locked)]), "locked steps must lead"
    tail = [r for r in ranked if not r["locked"]]
    idx = [R.RANKS.index(r["rank"]) for r in tail]
    assert idx == sorted(idx, reverse=True), "unlocked steps must run high -> low"
    highs = [r["pos"] for r in tail if r["rank"] == "high"]
    assert highs == sorted(highs), "ties must keep catalog order so the list is stable"


def test_the_customers_change_puts_the_cheap_stuff_last():
    """One env var in a shell script: nothing it engages should outrank what it does."""
    ranked = R.rank_plan(SPINE, COSTS, tier=1, paths=["scripts/demo.sh"], profile="fix",
                         tags=["chore"])
    order = [r["key"] for r in ranked if not r["locked"]]
    for cheap in ("figma", "roi", "training", "figma_compare", "roi_30", "roi_90"):
        assert order.index(cheap) > order.index("review1"), (
            "%s outranks the code review on a one-line script change" % cheap)


def test_every_step_carries_its_protects_sentence_through():
    ranked = R.rank_plan(SPINE, COSTS, tier=2)
    blank = [r["key"] for r in ranked if not r["protects"].strip()]
    assert not blank, "these would render an empty reason beside their checkbox: %s" % blank


# ── coherence ───────────────────────────────────────────────────────────────────────────────────
REQ = CAT["step_requires"]


def test_keeping_green_without_red_is_flagged():
    """The case that names the whole feature: a fix with no failing test behind it."""
    bad = R.incoherent({"green", "verify_green", "review1"}, REQ)
    assert ("green", "red", REQ["green"]["without_it"]) in bad
    assert any("failing test" in why for _, _, why in bad)


def test_a_coherent_selection_is_silent():
    assert R.incoherent({"red", "green", "verify_green", "review1", "rerun"}, REQ) == []


def test_dropping_both_a_step_and_its_prerequisite_is_fine():
    """Skipping the whole TDD pair is a recorded skip, not an incoherence."""
    assert R.incoherent({"issue", "review1"}, REQ) == []


def test_every_prerequisite_names_a_real_step_and_a_consequence():
    keys = {s["key"] for s in CAT["spine"]["steps"]}
    for step, e in REQ.items():
        assert step in keys, "%s requires something but is not a step" % step
        for need in e["needs"]:
            assert need in keys, "%s requires %s, which does not exist" % (step, need)
        assert len(e.get("without_it", "").strip()) > 20, (
            "%s: `without_it` is the sentence shown when challenging. %r does not say what breaks."
            % (step, e.get("without_it")))


def test_it_challenges_rather_than_blocks():
    """The contract is a list to talk about, never an exception or an exit code."""
    out = R.incoherent({"promote"}, REQ)
    assert isinstance(out, list) and out and isinstance(out[0], tuple)
    assert R.incoherent(None, None) == [] and R.incoherent({"green"}, None) == []


# ── the callers actually run ─────────────────────────────────────────────────────────────────────
import json, subprocess, tempfile


def _repo(tmp="", src_only=False):
    """A real repo with a manifest, a source file and a script, on a branch with one commit."""
    d = tempfile.mkdtemp()
    run = lambda *a: subprocess.run(a, cwd=d, capture_output=True, text=True, check=True)
    run("git", "init", "-q", ".")
    run("git", "config", "user.name", "t"); run("git", "config", "user.email", "t@t")
    os.makedirs(os.path.join(d, "src")); os.makedirs(os.path.join(d, "scripts"))
    os.makedirs(os.path.join(d, "docs", "02-design")); os.makedirs(os.path.join(d, "ci", "first-pass"))
    open(os.path.join(d, "src", "app.py"), "w").write("x = 1\n")
    open(os.path.join(d, "scripts", "demo.sh"), "w").write("echo hi\n")
    open(os.path.join(d, "docs", "02-design", "system-manifest.yaml"), "w").write(
        'domains:\n  - name: app\n    paths: ["src/"]\n')
    run("git", "add", "-A"); run("git", "commit", "-qm", "base")
    run("git", "checkout", "-q", "-b", "work")
    tgt = "src/app.py" if src_only else "scripts/demo.sh"
    open(os.path.join(d, tgt), "a").write("# change\n")
    run("git", "add", "-A"); run("git", "commit", "-qm", "change")
    here = os.path.dirname(os.path.abspath(__file__))
    for f in os.listdir(here):
        if f.endswith(".py"):
            open(os.path.join(d, "ci", "first-pass", f), "w").write(open(os.path.join(here, f)).read())
    open(os.path.join(d, "ci", "first-pass", "workflows.yaml"), "w").write(
        open(os.path.join(ROOT, "ai", "shared", "workflows.yaml")).read())
    return d


def _sel(d, *args):
    return subprocess.run([sys.executable, "ci/first-pass/plan_select.py", *args],
                          cwd=d, capture_output=True, text=True)


def test_there_is_no_probe_mode():
    """The probe read `git diff` at intake, where there is nothing to diff — intake runs before a
    line is written. Its job belongs to impact analysis, which reads the code. Removed rather than
    patched: three independent causes of death meant the design was wrong, not the implementation."""
    r = _sel(_repo(), "probe")
    assert r.returncode != 0 and "invalid choice" in (r.stderr + r.stdout)


def test_render_produces_a_selection_a_person_could_answer():
    out = _sel(_repo(), "render", "--tier", "1", "--profile", "fix", "--paths", "scripts/demo.sh").stdout
    assert "Running (locked)" in out and "[x]" in out
    assert "skipped and recorded" in out
    assert out.count("[x]") <= 8, "more than eight decidable items defeats the cut"


def test_the_tail_reaches_the_choices_file():
    """The whole compensation for inverting the default. Prose describing it is not the control."""
    d = _repo()
    r = _sel(d, "choices", "--tier", "1", "--profile", "fix", "--paths", "scripts/demo.sh",
             "--keep", "issue,review1", "--actor", "priya")
    assert r.returncode == 0, r.stderr
    doc = json.loads(r.stdout)
    assert doc["actor"] == "priya"
    for collapsed in ("roi", "training", "figma"):
        assert collapsed in doc["choices"], (
            "%s was collapsed into the tail and never recorded — skipped, and NOT recorded" % collapsed)
    for key, e in doc["choices"].items():
        assert e["disposition"] == "decline" and len(e["reason"]) > 20, (key, e)


def test_choices_refuses_without_a_named_actor():
    r = _sel(_repo(), "choices", "--tier", "1", "--paths", "scripts/demo.sh", "--keep", "issue", "--actor", "")
    assert r.returncode == 2 and "accountable to a person" in r.stderr


def test_an_incoherent_keep_is_reported_when_the_choices_are_written():
    """green/red cannot demonstrate this: red is no_omit, so it is locked and always kept — the
    incoherence is unreachable by construction. reconcile/review1 are both ordinary steps."""
    d = _repo()
    r = _sel(d, "choices", "--tier", "2", "--paths", "scripts/demo.sh", "--keep", "reconcile", "--actor", "p")
    assert r.returncode == 0, r.stderr
    assert "incoherent: keeping reconcile while dropping review1" in r.stderr, r.stderr
    assert "review that did not happen" in r.stderr


def test_locking_a_prerequisite_removes_the_incoherence():
    """A locked prerequisite is kept, so keeping its dependant is coherent — no false alarm."""
    d = _repo()
    r = _sel(d, "choices", "--tier", "2", "--paths", "scripts/demo.sh", "--keep", "green", "--actor", "p")
    assert "incoherent" not in r.stderr, (
        "red is no_omit and therefore kept; flagging green would be a false positive")


def test_the_ranker_and_the_validator_agree_on_the_floor_at_every_tier():
    """They disagreed: rank.py used crit_by_tier[tier], a plain lookup, while check_skips resolves
    monotonically — floor at 3 means floor at 3 AND ABOVE. At tier 4 six steps the validator blocks
    you for skipping were offered in the selection as ordinary choices.

    Ranging over 0..4 matters: they agreed at 1 and 2 and diverged above.
    """
    import check_skips as CS
    for tier in (0, 1, 2, 3, 4):
        locked = {r["key"] for r in R.rank_plan(SPINE, COSTS, tier=tier) if r["locked"]}
        expect = {s["key"] for s in SPINE
                  if CS.resolve_crit(s, tier) == "floor" or s.get("no_omit")}
        assert locked == expect, (
            "tier %d: the selection and the validator disagree about what is locked. "
            "only-selection=%s only-validator=%s"
            % (tier, sorted(locked - expect), sorted(expect - locked)))


def test_a_repo_without_step_costs_collapses_nothing():
    """The upgrade case that mattered: a project on 2.8.0 refreshes the plugin but not its copy of
    ci/first-pass/workflows.yaml.

    Without step_costs every step ranks the same, so the order falls back to catalog order — which
    is CHRONOLOGY. The first eight are the Design phase; the tail is review1, review2, qa_verify,
    verify_pr, arch_review, rerun, reconcile and rollout. Collapsing that tail and skipping it by
    default is strictly worse than the problem this release exists to fix.
    """
    import plan_select as P
    locked, offered, tail = P.build(SPINE, {}, {}, tier=2, paths=["src/a.py"], profile="fix",
                                    tags=[], manifest={}, incidents={})
    assert tail == [], "a plan with no ranking data must not be collapsed at all"
    for k in ("review1", "qa_verify", "verify_pr", "rollout"):
        assert k in {r["key"] for r in offered}, "%s must stay on the plan, not fall off it" % k


def test_a_repo_with_step_costs_does_collapse():
    """The other half: opting in must still lighten the plan, or the guard above is a way of
    disabling the feature."""
    import plan_select as P
    locked, offered, tail = P.build(SPINE, COSTS, {}, tier=2, paths=["src/a.py"], profile="fix",
                                    tags=[], manifest={}, incidents={})
    assert tail, "with ranking data present the tail must collapse"
    assert len(offered) <= 8
    for k in ("review1", "qa_verify", "verify_pr"):
        assert k not in {r["key"] for r in tail}, (
            "%s ranked into the skipped tail even with costs present" % k)


def test_partial_step_costs_is_treated_as_no_basis():
    """Half a catalog is not a ranking. A handful of entries must not license collapsing the rest."""
    import plan_select as P
    few = {k: COSTS[k] for k in list(COSTS)[:3]}
    _, offered, tail = P.build(SPINE, few, {}, tier=2, paths=[], profile="", tags=[],
                               manifest={}, incidents={})
    assert tail == [], "three entries out of thirty-eight is not enough to rank a plan"
