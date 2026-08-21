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
    # Presence of the new rule is not absence of the old one. Both sentences shipped together in
    # the same step — the fix and its cause — and every test passed, because each guard only ever
    # asserted that its own sentence existed.
    # Byte-exact matching let four rewordings through ("a distinct, stable name", "every
    # reviewer", "**distinct name**", "Each reviewer needs a distinct name"). Match the SHAPE:
    # an instruction to give reviewers names, however it is phrased.
    NAMING = re.compile(r"(?i)(give|assign)\s+(each|every|the)?\s*reviewers?\s+.{0,30}names?\b"
                        r"|reviewers?\s+needs?\s+.{0,20}\bnames?\b"
                        r"|name\s+(each|every)\s+reviewer")
    # The skill's own rule is "Do NOT give the reviewers names", which matches the same shape.
    # Judge each hit by what precedes it rather than by the hit alone.
    instructing = [m for m in NAMING.finditer(body)
                   if not re.search(r"(?i)\b(do not|don't|never|no)\s*$",
                                    body[max(0, m.start() - 24):m.start()])]
    assert not instructing, (
        "the 2.7.1 instruction to name reviewers is still here. That instruction is what stopped "
        "ten reports from ever being delivered; it cannot coexist with the fix for it")
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


HOOKS = os.path.join(AI, "claude", "hooks")


def _hook_messages():
    """Every line a hook prints to a person, by file."""
    out = {}
    for f in sorted(os.listdir(HOOKS)):
        if not f.endswith(".sh"):
            continue
        # Bash echoes AND the python heredocs. check-platform-ready.sh speaks to a user from
        # inside a `python3 << PYEOF` block via print(..., file=sys.stderr) and block(...); the
        # echo-only scan saw 8 of its lines and certified the 4 a user actually hits as fine.
        lines = [l.strip() for l in _read(os.path.join(HOOKS, f)).splitlines()
                 if re.search(r'echo\s+".*"\s*>&2', l.strip())
                 or re.search(r'(print|block)\s*\(\s*f?"', l.strip())]
        if lines:
            out[f] = lines
    return out


def test_hooks_do_not_shout_their_internal_state():
    """A gate interrupts someone mid-edit; what it says is the whole experience of being gated.

    These read as a compiler reporting internal state in capitals: "HITL CONTEXT MISMATCH", "All
    edits are blocked until the context is realigned." Nobody has a context mismatch. 2.6.0 fixed
    exactly this in the intake banner and never reached the hooks.
    """
    offenders = []
    for f, lines in _hook_messages().items():
        for l in lines:
            if re.search(r'"HITL [A-Z]{2,}', l) or re.search(r'"[A-Z]{3,}[A-Z ]{6,}:', l):
                offenders.append("%s: %s" % (f, l[:70]))
    assert not offenders, ("hook messages shouting an error code at a person:\n  "
                           + "\n  ".join(offenders))


def _message_blocks(text):
    """Consecutive stderr lines are one message; a line of real code ends it.

    Per MESSAGE, not per file. Checking the whole file passes as soon as any one message names a
    remedy, so stripping the way out of three messages stayed green while a fourth still had one —
    the guard reported on a file that no longer told most people what to do.
    """
    blocks, cur = [], []
    for line in text.splitlines():
        t = line.strip()
        if re.search(r'echo\s+".*"\s*>&2', t) or re.search(r'echo\s+""\s*>&2', t):
            cur.append(t)
        elif (t.startswith("while IFS=") or not t or t.startswith("#")
              or re.match(r"^(if|elif|else|fi|then|done|do)\b", t)):
            # Loops, conditionals, blanks and comments do not end a message. One message often
            # varies a line by a condition — the remedy can sit in the branch after the sentence
            # that announces the block, and splitting there reports a message that does not exist.
            continue
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    return [" ".join(b) for b in blocks]


def test_a_hook_that_blocks_says_what_to_do_next():
    """Being stopped with no way forward is what makes a gate feel broken rather than protective.

    2.6.1 is the case in point: a concluded change told people to run dev-switch-context, and the
    branch it named was deleted. The advice existed and could not be followed.
    """
    missing = []
    for f in sorted(os.listdir(HOOKS)):
        if not f.endswith(".sh"):
            continue
        for blk in _message_blocks(_read(os.path.join(HOOKS, f))):
            if not re.search(r"(?i)paused|blocked|stopped|on hold", blk):
                continue
            if not re.search(r"/hitl:[a-z-]+|pip install|HITL_PY|Set  ?status|Switch to", blk):
                missing.append("%s: %s" % (f, blk[:80]))
    assert not missing, ("these messages stop someone and never name a next step:\n  "
                         + "\n  ".join(missing))


def test_icons_stay_out_of_the_aligned_trail():
    """Emoji are commonly double-width and render inconsistently across terminals.

    The breadcrumb is aligned text with its own assertion matrix, so icons belong in prose. The
    existing semantic glyphs there are single-width by construction.
    """
    emoji = re.compile("[\U0001F300-\U0001FAFF]")
    for name in ("workflow-steps.md",):
        for base in (os.path.join(AI, "claude", "dev-practices"), os.path.join(AI, "shared")):
            p = os.path.join(base, name)
            if os.path.isfile(p):
                for line in _read(p).splitlines():
                    if "·" in line and ("Phase" in line or "→" in line):
                        assert not emoji.search(line), (
                            "%s: an emoji in the breadcrumb line breaks alignment: %s" % (name, line[:70]))
    statusline = os.path.join(HOOKS, "statusline-hitl.sh")
    if os.path.isfile(statusline):
        assert not emoji.search(_read(statusline)), (
            "the statusline is width-sensitive; keep icons out of it")


def test_turning_icons_off_cannot_remove_a_warning():
    """The form/substance rule, applied to glyphs. If an icon is the only thing marking a risk,
    a plain-text project silently loses the risk."""
    txt = _flat(os.path.join(AI, "claude", "preferences", "SKILL.md"))
    assert re.search(r"(?i)icon is never the only thing", txt), (
        "preferences does not say an icon can never be the only thing carrying a warning")


def test_the_portal_agrees_with_itself_about_the_current_version():
    """catalog.html is generated and stamps plugin.json's version; four pages are hand-written.

    They drifted five versions apart once (v2.1.1 on the home page against a plugin at 2.7.1), and
    were about to drift again one version later — the same class the release claims to have closed.
    """
    import json
    ver = json.load(io.open(os.path.join(AI, "claude", "plugin", "plugin.json"), encoding="utf-8"))["version"]
    site = os.path.join(ROOT, "site")
    stale = {}
    for f in sorted(x for x in os.listdir(site) if x.endswith(".html")):
        hits = set(re.findall(r"v(\d+\.\d+\.\d+)", _read(os.path.join(site, f))))
        wrong = {h for h in hits if h != ver and not h.startswith("1.")}
        if wrong:
            stale[f] = sorted(wrong)
    assert not stale, ("these pages name a 2.x version that is not the shipped %s: %s\n"
                       "  (1.x references are the legacy line and are left alone)" % (ver, stale))


def test_both_departures_from_the_proposed_tier_are_attributed():
    """A user added one env var to a shell script and it ran 3h31m through the full spine.

    Nothing malfunctioned: intake tiered up, and at tier 2 every ceremony step runs. Three defaults
    compounded, and the load-bearing one was that the CHEAP path cost paperwork — tier 0/1 refused
    without tier_set_by/tier_reason while tier 2 was the free default. The friction was on the
    correct answer. Both departures are attributed now.
    """
    body = _read(os.path.join(AI, "claude", "start-change", "SKILL.md"))
    assert "TRIVIAL_SHAPE" in body, (
        "the generator no longer reads the shape probe, so a trivially-shaped change can be tiered "
        "up with no name against it")
    assert re.search(r"if\s+trivial\s+and\s+tier\s*>=\s*2\s+and\s+not", body), (
        "the tier 2+ attribution rule for a trivial shape is gone")
    assert re.search(r"if\s+tier\s*<=\s*1\s+and\s+not", body), (
        "the original tier 0/1 attribution rule is gone — this fix ADDS a rule, it does not "
        "trade one for the other")


def test_intake_proposes_a_tier_from_the_shape():
    """Making someone argue a tier DOWN is the friction that pushes people out of the process."""
    ref = os.path.join(AI, "claude", "start-change", "right-sizing.md")
    assert os.path.isfile(ref), "right-sizing.md is gone; intake has no shape guidance"
    txt = _flat(ref)
    assert re.search(r"(?i)git diff --name-only", txt), "the probe command is gone"
    assert re.search(r"(?i)does not lower a floor step", txt), (
        "nothing states the probe never lowers a floor — that is the line between right-sizing and "
        "weakening the gate")
    assert re.search(r"(?i)naming a key is not moving one", txt), (
        "the distinction that decides this case is gone: adding FIRECRAWL_API_KEY= to a script is "
        "a chore, changing where a secret lives is not")
    body = _flat(os.path.join(AI, "claude", "start-change", "SKILL.md"))
    assert "right-sizing.md" in body, "the skill no longer points at the shape guidance"
    assert re.search(r"(?i)at tier 0 or 1, offer it without being asked", body), (
        "First Pass is opt-in again at tier 0/1 — the one feature built for this case has to be "
        "asked for by someone who already knows it exists")


def test_the_catalog_does_not_claim_profiles_filter_the_plan():
    """Profiles and tags are advice to intake. Nothing at runtime applies them.

    `ai/shared/workflows.yaml` — what a change file is seeded from — carries only `workflows`, and
    the generator takes the `development` block verbatim. derive.py implements excludes/activates
    and is a source-tree tool the plugin does not ship. So `fix` excluding roi has never removed a
    step, `chore` carrying tier 0 has never set a tier, and `perf` activating baseline has never
    turned it on. A user asked for one env var in a shell script and got all 31 steps.

    This asserts the catalog SAYS so. If someone later wires profiles into the runtime, the runtime
    check below starts failing and both halves get revisited together.
    """
    cat = _read(os.path.join(ROOT, "tools", "workflow-catalog", "catalog.yaml"))
    # Anchor on the top-level key, not the first occurrence of the word — the section's own header
    # comment contains "profiles:" and a naive index() cuts the note this test is looking for.
    m = re.search(r"(?m)^profiles:\s*$", cat)
    assert m, "no top-level profiles: block in the catalog"
    head = cat[:m.start()]
    assert re.search(r"(?i)advisory|advice to intake", head), (
        "the catalog presents profiles as filters again. They are not applied at runtime; saying so "
        "is the only thing stopping the next reader trusting `excludes`")

    import yaml
    runtime = yaml.safe_load(_read(os.path.join(AI, "shared", "workflows.yaml")))
    assert "profiles" not in runtime and "tags" not in runtime, (
        "the runtime catalog now carries profiles/tags. If they are genuinely applied, delete this "
        "test and the advisory note in catalog.yaml — but check the change-file generator actually "
        "uses them before believing it")


def test_every_step_declares_what_it_protects_and_what_skipping_costs():
    """The selection view shows `protects` beside an unticked box and ranks by `forgo_cost`.

    A step with no entry renders a blank reason and sorts nowhere, which is how a step quietly
    becomes the one nobody thinks about. An orphan entry is a step someone deleted while leaving its
    justification behind. Assert BOTH directions — a coverage check that only looks one way passes
    while half the data is wrong.
    """
    import yaml
    cat = yaml.safe_load(_read(os.path.join(ROOT, "tools", "workflow-catalog", "catalog.yaml")))
    steps = {s["key"] for s in cat["spine"]["steps"]}
    costs = cat.get("step_costs") or {}
    assert costs, "no step_costs block — the selection view has nothing to rank or explain"

    missing = sorted(steps - set(costs))
    orphans = sorted(set(costs) - steps)
    assert not missing, "spine steps with no protects/forgo_cost: %s" % missing
    assert not orphans, "step_costs entries for steps that do not exist: %s" % orphans

    RANKS = {"high", "medium", "low"}
    for key, e in sorted(costs.items()):
        assert e.get("forgo_cost") in RANKS, (
            "%s: forgo_cost %r is not one of %s" % (key, e.get("forgo_cost"), sorted(RANKS)))
        prot = str(e.get("protects", "")).strip()
        assert len(prot) > 25, (
            "%s: `protects` is what a person reads when deciding to untick this step. %r does not "
            "tell them what they lose." % (key, prot))
        assert not re.match(r"(?i)\s*(runs|performs|the) %s\b" % re.escape(key.replace("_", " ")), prot), (
            "%s: `protects` restates the step name instead of naming the consequence" % key)
        eng = e.get("engages")
        assert eng == "always" or isinstance(eng, dict), (
            "%s: engages must be 'always' or a dict of paths/profiles/tags/multi_domain" % key)
        if isinstance(eng, dict):
            unknown = set(eng) - {"paths", "profiles", "tags", "multi_domain"}
            assert not unknown, "%s: engages has unknown keys %s" % (key, sorted(unknown))


def test_a_floor_step_is_never_ranked_below_high():
    """Modulation reorders the list; it must not argue a floor step down it.

    A `floor` step ranked low would sort into the tail and be dropped by someone reading the ranks
    rather than the flags — the two signals must not disagree.
    """
    import yaml
    cat = yaml.safe_load(_read(os.path.join(ROOT, "tools", "workflow-catalog", "catalog.yaml")))
    costs = cat.get("step_costs") or {}
    # Only steps that are floor at EVERY tier, plus no_omit. A step that is floor at tier 3 alone
    # (packet, impact, qa_verify...) is LOCKED at that tier — it never appears in the rankable list
    # there — and is ordinarily rankable everywhere else. Treating those as "must be high" would be
    # the guard inventing a rule rather than checking one.
    bad = []
    for s in cat["spine"]["steps"]:
        crit = s.get("crit")
        if crit == "floor" or s.get("no_omit"):
            if costs.get(s["key"], {}).get("forgo_cost") != "high":
                bad.append("%s (%s) ranked %s" % (s["key"], crit, costs.get(s["key"], {}).get("forgo_cost")))
    assert not bad, ("a floor / no_omit step ranked below high, so the rank and the flag disagree: %s"
                     % bad)


def test_step_costs_reach_the_runtime_and_something_reads_them():
    """Data nobody reads is this repo's recurring defect: `excludes`, `activates`, `chore: tier 0`
    are all correct, all tested, all consumed by nothing.

    step_costs is only worth carrying if it reaches the file intake actually reads AND something
    turns it into an order. Assert both ends, so the middle cannot quietly fall out.
    """
    import yaml
    cat = yaml.safe_load(_read(os.path.join(ROOT, "tools", "workflow-catalog", "catalog.yaml")))
    run = yaml.safe_load(_read(os.path.join(AI, "shared", "workflows.yaml")))
    assert run.get("step_costs"), (
        "ai/shared/workflows.yaml has no step_costs. That is the file a plan is seeded from and the "
        "only one the plugin ships — without it the selection has nothing to rank or explain")
    assert run["step_costs"] == cat["step_costs"], (
        "the runtime step_costs has drifted from the catalog; regenerate it from the catalog")

    ranker = os.path.join(ROOT, "ci", "first-pass", "rank.py")
    assert os.path.isfile(ranker), "ci/first-pass/rank.py is gone — nothing turns costs into an order"
    src = _read(ranker)
    for fn in ("shown_rank", "rank_plan", "engaged", "risky_domains"):
        assert "def %s(" % fn in src, "rank.py no longer defines %s()" % fn

    sel = os.path.join(AI, "claude", "start-change", "selection.md")
    assert os.path.isfile(sel), "the selection spec is gone; intake has nothing to show"
    body = _flat(os.path.join(AI, "claude", "start-change", "SKILL.md"))
    assert "selection.md" in body, (
        "Step 4 no longer routes into the selection, so the ranking is computed for nobody")


def test_the_selection_keeps_its_load_bearing_rules():
    """Three rules are the difference between right-sizing and quietly running less process."""
    sel = _flat(os.path.join(AI, "claude", "start-change", "selection.md"))
    assert re.search(r"(?i)below the cut line is skipped, and recorded", sel), (
        "nothing says the tail is recorded — an unshown default that runs nothing is exactly the "
        "silent lightening CR-1 was written to prevent")
    assert re.search(r"(?i)floor can be unticked", sel) and re.search(r"(?i)waiver", sel), (
        "the floor is either locked out of the view or unticked with a name against it; this says "
        "neither")
    assert re.search(r"(?i)never quote a duration|quote step counts", sel), (
        "the duration rule is gone. Two shipped estimates in this repo were wrong because elapsed "
        "time is mostly waiting for a human")


def test_coherence_is_checked_and_challenges_rather_than_blocks():
    """Keeping a step while dropping what it requires makes a claim the plan cannot support.

    Two halves have to stay true together: the data exists in both catalog and runtime, and the
    thing that reads it returns a list to talk about rather than refusing. A coherence check that
    blocks would be the only hard refusal in a framework built on recorded exceptions.
    """
    import yaml
    cat = yaml.safe_load(_read(os.path.join(ROOT, "tools", "workflow-catalog", "catalog.yaml")))
    run = yaml.safe_load(_read(os.path.join(AI, "shared", "workflows.yaml")))
    req = cat.get("step_requires")
    assert req, "no step_requires — nothing knows that GREEN is defined against RED"
    assert run.get("step_requires") == req, "runtime step_requires has drifted from the catalog"

    keys = {s["key"] for s in cat["spine"]["steps"]}
    for step, e in req.items():
        assert step in keys and all(n in keys for n in e["needs"]), (
            "%s: a prerequisite that names no real step can never fire" % step)

    src = _read(os.path.join(ROOT, "ci", "first-pass", "rank.py"))
    assert "def incoherent(" in src, "rank.py no longer implements the coherence check"
    assert "raise" not in src.split("def incoherent(")[1].split("\ndef ")[0], (
        "incoherent() raises. It must return findings to challenge with, not refuse")

    sel = _flat(os.path.join(AI, "claude", "start-change", "selection.md"))
    assert "incoherent" in sel and re.search(r"(?i)do not block it", sel), (
        "the selection no longer cites the check, or no longer says it challenges")


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
