#!/usr/bin/env python3
"""Wiring conformance — the class of defect unit tests structurally cannot catch.

Every serious defect found in the 2026-08 review rounds had the same shape: machinery that existed,
was correct, was unit-tested, and was connected to nothing.

- `permissions.decide()` was implemented and tested; no caller. CR-15 never engaged.
- `resurface.surface()` was called where its inputs could not yet exist. It matched nothing, silently.
- `check_skips.check()` was gated on a flag the driver never emitted. Certification passed on
  everything.
- The issue-#14 Python probe was fixed in the skills and never carried to `init-project.sh`, so
  onboarded repos got hooks that silently no-op on Windows.
- One false sentence about tier behaviour was copied into five files.

Unit tests passed in all five cases, because in all five cases the unit was fine. The defect lived in
the seam. These tests assert the seams.

A full end-to-end simulation of a 31-step workflow would be slow, brittle, and would still miss most
of the above. Instead this file checks three specific properties:

  REACHABILITY  — every shipped module is actually invoked by something that ships
  CONSISTENCY   — definitions that exist in more than one place agree
  COMPLETENESS  — every hook that exists is wired, and every wired hook exists

Run: python3 -m pytest ci/wiring -q
"""
import io
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))   # ci/wiring/ -> repo root
AI = os.path.join(ROOT, "ai")
HOOKS = os.path.join(AI, "claude", "hooks")


def _read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()

def _flat(path):
    """Read a doc with its hard wrapping removed.

    These files wrap at 100 columns and quote things inside blockquotes, so any phrase long enough
    to be worth asserting is usually split across a newline. Three guards in this file passed or
    failed for that reason rather than for the rule they check. Match against this, not the raw
    text.
    """
    return re.sub(r"\s+", " ", _read(path).replace("\n>", " "))



def _shipped_text():
    """Everything that ships and could reference a module: skills, hooks, CI, tools."""
    out = []
    for base in (AI, os.path.join(ROOT, "ci"), os.path.join(ROOT, "tools")):
        for dirpath, _dirs, files in os.walk(base):
            if "__pycache__" in dirpath or ".pytest_cache" in dirpath:
                continue
            for f in files:
                if f.startswith("test_") or not f.endswith((".md", ".py", ".sh", ".yml", ".yaml")):
                    continue
                out.append((os.path.join(dirpath, f), _read(os.path.join(dirpath, f))))
    return out


SHIPPED = _shipped_text()


# ── REACHABILITY ──────────────────────────────────────────────────────────────

FIRST_PASS_MODULES = ["check_skips", "resurface", "permissions", "starters",
                      "dispositions", "migrate_project"]


@pytest.mark.parametrize("mod", FIRST_PASS_MODULES)
def test_every_shipped_module_has_a_caller(mod):
    """A module nothing invokes is a promise nothing keeps.

    `permissions.py` sat like this for a full release: implemented, tested, documented in
    `first-pass/permissions.md` as the classifier the driver applies — and never called, so the
    reduced-friction policy it describes did not exist at runtime. `dispositions.py` was the same.

    Counts both call styles: a Python import, and a CLI invocation by filename (several of these
    are invoked as `python3 <path>/<mod>.py` from skill prose, which no import graph would see).
    """
    import_re = re.compile(rf"\b(?:from\s+{mod}\s+import|import\s+{mod})\b")
    cli_re = re.compile(rf"\b{mod}\.py\b")
    callers = [p for p, txt in SHIPPED
               if os.path.basename(p) != f"{mod}.py" and (import_re.search(txt) or cli_re.search(txt))]
    assert callers, (
        f"{mod}.py ships but nothing invokes it — no import, no CLI reference. Either wire it or "
        f"delete it; an untested-in-situ module is worse than an absent one because it reads as "
        f"a working guarantee.")


# ── CONSISTENCY ───────────────────────────────────────────────────────────────

WRAPPER_MARKERS = [
    ("installed_plugins.json", "runtime plugin discovery (pre-v1.0.9 without it)"),
    ("command -v", "the multi-candidate interpreter probe (issue #14)"),
    ("import sys", "the Store-stub smoke test (issue #14)"),
    ("HITL_PY", "the resolved interpreter handed to hooks (issue #14)"),
    ("PYTHONUTF8", "UTF-8 stdout for the breadcrumb glyphs (issue #14)"),
]

# The wrapper body should exist in as FEW places as possible. It is currently two: the skill that
# defines it, and the standalone shell installer which cannot reference a skill at runtime.
WRAPPER_SOURCES = [
    os.path.join(AI, "claude", "start-from-prd", "SKILL.md"),
    os.path.join(ROOT, "tools", "scripts", "init-project.sh"),
]

# These onboarding paths must REFERENCE the definition, never restate it. Both carried their own
# copy and both went stale, shipping hooks that silently no-op on Windows.
WRAPPER_REFERENCERS = [
    os.path.join(AI, "claude", "start-brownfield", "SKILL.md"),
    os.path.join(AI, "claude", "start-migration", "SKILL.md"),
]


@pytest.mark.parametrize("src", WRAPPER_REFERENCERS, ids=lambda p: os.path.basename(os.path.dirname(p)))
def test_onboarding_paths_reference_the_wrapper_rather_than_copy_it(src):
    txt = _read(src)
    assert 'exec bash "$PLUGIN_ROOT/hooks/' not in txt, (
        f"{os.path.relpath(src, ROOT)} contains its own hook-wrapper body. Every copy has drifted "
        f"eventually; reference Step 0 of dev-start-from-prd instead.")
    assert "start-from-prd" in txt, (
        f"{os.path.relpath(src, ROOT)} neither defines nor references the wrapper — onboarding "
        f"through it would create no wrappers at all.")


@pytest.mark.parametrize("src", WRAPPER_SOURCES, ids=lambda p: os.path.basename(os.path.dirname(p)) or os.path.basename(p))
@pytest.mark.parametrize("marker,why", WRAPPER_MARKERS, ids=lambda x: x if isinstance(x, str) and " " not in x else "")
def test_every_wrapper_generator_carries_every_marker(src, marker, why):
    """The hook-wrapper body is defined in four places. It has drifted twice.

    `init-project.sh` kept emitting the pre-issue-#14 wrapper long after the skills were fixed, so
    every repo onboarded through it got hooks that silently do nothing on Windows. Nothing detected
    that, because `dev-update`'s staleness check tested one marker and the drift was in another.
    """
    txt = _read(src)
    assert marker in txt, (
        f"{os.path.relpath(src, ROOT)} generates hook wrappers without {marker!r} — {why}. "
        f"All wrapper generators must stay in step; this is the drift that shipped broken hooks.")


def test_the_generated_wrapper_matches_the_authoritative_template():
    """Beyond markers: init-project.sh's output must not diverge structurally from the skill's."""
    script = _read(os.path.join(ROOT, "tools", "scripts", "init-project.sh"))
    skill = _read(os.path.join(AI, "claude", "start-from-prd", "SKILL.md"))
    for token in ("for _c in python3 python py", "PYTHONIOENCODING"):
        assert token in script and token in skill, (
            f"{token!r} present in only one wrapper generator — they have drifted again.")


def test_doctrine_about_tiers_matches_the_catalog():
    """Prose asserting catalog facts must be checkable against the catalog.

    One false sentence — that a low tier demotes five named steps — was copied into five shipped
    files and survived review. The tier facts themselves are pinned in ci/first-pass; this asserts
    no shipped text reasserts the disproved version.
    """
    bad = []
    for p, txt in SHIPPED:
        if "demotes" in txt and re.search(r"tier\s*(<=|≤)\s*1[^.]{0,80}demotes", txt):
            bad.append(os.path.relpath(p, ROOT))
    assert not bad, (
        "these files claim tier <= 1 demotes steps from floor to standard, which the catalog "
        f"contradicts (the five-step demotion is 3 -> 2): {bad}")


# ── COMPLETENESS ──────────────────────────────────────────────────────────────

def _hook_names():
    return sorted(f[:-3] for f in os.listdir(HOOKS)
                  if f.endswith(".sh") and not f.startswith("_"))


@pytest.mark.parametrize("hook", _hook_names())
def test_every_hook_that_exists_is_wired_somewhere(hook):
    """A hook file nobody registers never runs. `first-pass-permissions.sh` would have been
    exactly this had the onboarding settings block not been updated alongside it."""
    refs = [p for p, txt in SHIPPED if hook in txt and not p.endswith(f"{hook}.sh")]
    assert refs, (
        f"ai/claude/hooks/{hook}.sh exists but no skill, settings template, or script references "
        f"it — it will never fire.")


def test_every_wired_hook_exists():
    """The inverse: a settings template naming a hook that isn't there fails at runtime, silently."""
    missing = []
    have = set(_hook_names())
    for p, txt in SHIPPED:
        if not p.endswith("SKILL.md"):
            continue
        for name in re.findall(r"\.hitl/hooks/([a-z0-9-]+)\.sh", txt):
            if name not in have and name != "statusline":
                missing.append((os.path.relpath(p, ROOT), name))
    assert not missing, f"settings wiring names hooks that do not exist in ai/claude/hooks/: {missing}"


def test_the_onboarding_paths_agree_on_the_hook_list():
    """Three onboarding skills each enumerate the hooks to create. They must not disagree —
    a repo's enforcement should not depend on which command onboarded it."""
    lists = {}
    for f in ("start-from-prd", "start-brownfield", "start-migration"):
        txt = _read(os.path.join(AI, "claude", f, "SKILL.md"))
        m = re.search(r"wrapper for each of these \w+ hooks: (.+?)\. \(", txt, re.S)
        assert m, f"{f}: could not find the hook list — the wording changed, so this check went blind"
        lists[f] = sorted(re.findall(r"`([a-z0-9-]+)`", m.group(1)))
    first = next(iter(lists.values()))
    assert all(v == first for v in lists.values()), f"onboarding paths disagree on hooks: {lists}"


def test_every_reviewer_agent_carries_the_adversarial_stance():
    """A reviewer asked to confirm will confirm.

    Every HITL reviewer opened with "ensure X is sound" / "verify Y is sufficient" — questions
    shaped to be answered yes. In this framework's own review rounds, the same model on the same
    code returned clean when asked to verify and returned blockers when asked to refute. The stance
    is duplicated across five agent files by necessity (they ship standalone); this makes the
    duplication a checked invariant instead of drift bait.
    """
    reviewers = [f for f in os.listdir(os.path.join(AI, "claude", "agents"))
                 if f.endswith("-reviewer.md")]
    assert reviewers, "no reviewer agents found — this check went blind"
    missing = [f for f in reviewers
               if "Try to refute, not to confirm" not in _read(os.path.join(AI, "claude", "agents", f))]
    assert not missing, f"reviewer agents without the adversarial stance: {sorted(missing)}"


def test_findings_are_put_to_a_human_before_they_are_resolved():
    """`accepted_by` is enforced by a gate that nothing ever collected a name for.

    The record template calls accepting a finding "someone's decision" and
    ci/adversarial/check_review.py blocks with UNSIGNED_ACCEPTANCE without a name. But no step asked
    anyone, which left "fix every CRITICAL and HIGH" as the only disposition an agent could reach —
    and an unbounded fix-and-re-review loop as the only shape the review could take.

    The seam is ORDER: putting findings to a human has to happen before resolving them, or it is a
    notification rather than a decision. Asserted by position, not by presence, because a triage
    section that sits after the fixes reads identically and does nothing.
    """
    body = _read(os.path.join(AI, "claude", "adversarial-review", "SKILL.md"))
    heads = re.findall(r"(?m)^## Step \d+ — (.+)$", body)
    assert heads, "no step headings in the adversarial-review skill — this check went blind"

    def _pos(pattern):
        m = re.search(r"(?m)^## Step \d+ — .*%s.*$" % pattern, body)
        return m.start() if m else -1

    triage = _pos(r"[Pp]ut it to the user")
    verify = _pos(r"[Vv]erify")
    resolve = _pos(r"[Rr]esolve")
    assert triage > 0, ("the adversarial-review skill has no step putting findings to the user; "
                        "`accepted_by` is unreachable and 'fix everything' is the only answer")
    assert verify > 0 and resolve > 0, "verify/resolve steps not found — the headings changed"
    assert verify < triage < resolve, (
        "triage must sit between verifying findings and resolving them (verify=%d, triage=%d, "
        "resolve=%d). After the fixes it is a status update, not a decision." % (verify, triage, resolve))


def test_an_unanswered_finding_is_never_accepted_on_someones_behalf():
    """The failure mode of asking is an agent answering for the person it asked.

    A name written into `accepted_by` that nobody said turns the one field the gate trusts into
    decoration. Both the skill and the shared guidance have to carry the rule, because an agent
    running the command reads one and an agent doing it by hand reads the other.
    """
    for rel in (os.path.join(AI, "claude", "adversarial-review", "SKILL.md"),
                os.path.join(AI, "shared", "adversarial-review.md")):
        txt = _flat(rel)
        assert re.search(r"(?i)not answered|unanswered|did not say", txt), (
            "%s does not say what happens to a finding nobody answered — the default has to be "
            "`open`, or silence reads as consent" % os.path.basename(rel))


def test_the_review_cost_is_quoted_per_round_not_per_review():
    """Ten minutes is a round. A change needing three rounds costs a working day.

    Quoting the round as the whole review is what makes the estimate stop being believed, and it is
    the sentence a user weighs the offer against.
    """
    for rel in (os.path.join(AI, "claude", "adversarial-review", "SKILL.md"),
                os.path.join(AI, "shared", "adversarial-review.md")):
        # Normalise first. These files are hard-wrapped and the shared doc quotes the offer inside a
        # blockquote, so "ten minutes" is routinely split as "ten\n> minutes". A raw substring test
        # silently skips the file it is meant to check — the same blindness that let a broken link
        # pass 53/53 in 2.4.7.
        flat = re.sub(r"\s+", " ", _read(rel).replace("\n>", " "))
        if "ten minutes" not in flat.lower():
            continue
        assert re.search(r"(?i)a round takes.{0,30}ten minutes|ten minutes.{0,40}(is|=).{0,20}round|"
                         r"cost of a round", flat), (
            "%s quotes ten minutes without tying it to a single round" % os.path.basename(rel))


def test_the_lens_catalog_and_the_gate_agree():
    """The catalog is prose and the gate is code; the ids have to be the same set.

    The catalog deliberately does not ship as a data file. `scripts/build.sh` ships shared prose
    from an explicit allowlist and `dev-update` copies only *.py into ci/adversarial/, so a
    lenses.yaml would be missing from the built plugin and from every repo onboarded before it —
    the "ships to shared/ but nothing copies it in" defect of 2.4.1 and 2.6.2. The cost of keeping
    it as prose is that it can drift from the validator, which is what this asserts.
    """
    sys.path.insert(0, os.path.join(ROOT, "ci", "adversarial"))
    try:
        import check_review
    finally:
        sys.path.pop(0)

    doc = _read(os.path.join(AI, "shared", "adversarial-review.md"))
    start = doc.find("## The lens catalog")
    assert start > 0, "the lens catalog section is gone — this check went blind"
    end = doc.find("### Older names", start)
    assert end > start, "the catalog's alias section is gone — this check went blind"

    documented = set(re.findall(r"(?m)^\| `([a-z]+)` \|", doc[start:end]))
    documented |= set(re.findall(r"\| `([a-z]+)` \| (?:Does|What|When|Someone|This)",
                                 doc[start:end]))
    assert documented, "no lens ids parsed from the catalog table — the format changed"

    in_code = set(check_review.LENSES)
    missing = sorted(documented - in_code)
    extra = sorted(in_code - documented)
    assert not missing, ("lenses documented but unknown to the gate, so a record using one warns "
                         "UNKNOWN_LENS: %s" % missing)
    assert not extra, ("lenses the gate knows but the catalog never offers, so nobody can pick "
                       "them: %s" % extra)

    # `[a-z-]+`, not `[a-z]+`: a hyphenated older name (`blast-radius`) is exactly the kind of
    # alias someone adds, and the narrower class skipped it silently.
    aliases = set(re.findall(r"`([a-z][a-z-]*)` →", doc[start:]))
    unmapped = sorted(a for a in aliases if a not in check_review.LENS_ALIASES)
    assert not unmapped, ("the catalog promises these older names still resolve, and the gate does "
                          "not map them: %s" % unmapped)


def test_reviewers_hand_their_report_over_through_a_file():
    """A named agent becomes an addressable peer, not a task that returns — it does the work and the
    report never comes back. The skill instructed naming and its next step said "reports come back".

    Verified directly: an unnamed agent returned its content in under two seconds; the named one
    delivered nothing, never appeared in the subagent list, and did not answer a direct message.
    So the report has to arrive through a file, and the skill must not instruct a name.
    """
    body = _flat(os.path.join(AI, "claude", "adversarial-review", "SKILL.md"))
    assert ".hitl/reviews/incoming/" in body, (
        "no file-based report path; the skill is back to hoping reports are returned")
    assert re.search(r"(?i)do not give the reviewers names|not give .{0,20}names", body), (
        "the skill no longer warns against naming reviewers, which is what suppresses delivery")
    assert re.search(r"(?i)missing file .{0,30}(unknown|never failed)|unknown, never failed", body), (
        "nothing says a missing report is UNKNOWN — recording a reviewer as failed on a transcript "
        "read is how a real lens was written off as incomplete")
    assert re.search(r"(?i)do not read a reviewer's transcript|not read .{0,20}transcript", body), (
        "the transcript race is not warned against; the last message is unflushed when an agent "
        "goes idle, so a read returns a stub")


def test_the_loop_stops_and_asks():
    """Two rounds then a human decision. Not a prohibition — this repo's own 2.7.x work ran to
    round 15 — but round 3 has to be a choice someone makes rather than a continuation."""
    body = _flat(os.path.join(AI, "claude", "adversarial-review", "SKILL.md"))
    assert re.search(r"(?i)two rounds, then ask", body), "no stop condition on the fix loop"
    assert not re.search(r"(?i)keep going until a round comes back with nothing new", body), (
        "the unbounded 'keep going until convergence' rule is back")
    assert re.search(r"(?i)scope question", body), (
        "nothing tells the reader that the same decision blocking twice is a scope question")


def test_the_brief_asks_for_intra_file_consistency():
    """Two contradictory claims twenty lines apart survive every cross-file comparison, because
    every other document agrees with the stale half. Found at round 4 on GH-371."""
    body = _flat(os.path.join(AI, "claude", "adversarial-review", "SKILL.md"))
    assert re.search(r"(?i)each file against itself", body), (
        "the brief never asks a reviewer to check a file against itself first")


def test_the_skip_ledger_is_never_retired_with_the_change_file():
    """CR-10 makes the ledger durable across changes. The retirement step removes the change file
    and handoff prose at `promote`; if it ever removed the ledger too, every past skip would vanish
    and resurfacing would only ever see the current change."""
    txt = _read(os.path.join(AI, "claude", "dev-practices", "workflow-steps.md"))
    assert "Retire the change's working artifacts" in txt, "the retirement step is gone"
    retire = txt[txt.index("Retire the change's working artifacts"):][:1200]
    assert "skip-ledger.yaml" in retire and "Do not touch" in retire, (
        "the retirement step must explicitly protect .hitl/skip-ledger.yaml")
    assert not re.search(r"rm\b[^\n]*skip-ledger", retire), (
        "the retirement step deletes the durable ledger — CR-10 violation")
