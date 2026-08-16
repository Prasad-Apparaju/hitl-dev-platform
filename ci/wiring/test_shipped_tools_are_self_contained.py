"""What we ship into a consumer repo must run there.

Plugin issue #29: the CI-validator sync copied `*.py` wholesale, dragging each validator's own
dev-repo test suite into consumer projects. Those tests resolve paths that exist only in this
platform repo, so a consumer got collection errors and 68 failures out of the box. It blocked a
downstream PR.

The FIRST version of this guard file was vacuous. An adversarial review reverted the fix to the
original bare glob and all six guards stayed green, because they:
  - asserted a substring that a mere comment satisfies,
  - built the consumer repo with a PYTHON REIMPLEMENTATION of the filter rather than running the
    shipped script, so they tested the test's own copy logic, and
  - pattern-matched one exact `cp` spelling, which any other spelling evades.

So these now execute the real `hitl_copy_tools` out of init-project.sh, in bash, and assert on what
actually lands on disk. A guard that cannot fail is worse than no guard.
"""
import io
import re
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
INIT = os.path.join(ROOT, "tools", "scripts", "init-project.sh")
UPDATE_SKILL = os.path.join(ROOT, "ai", "claude", "update", "SKILL.md")

# Every directory whose Python is copied into a product repo, by onboarding or by dev-update.
SYNCED_DIRS = ["ci/first-pass", "ci/manifest-agentic", "tools/manifest-agentic",
               "ci/manifest-drift", "ci/agentic-advisor"]

# Files that must never reach a consumer: pytest imports conftest.py at collection, so a
# platform-only one blocks collection exactly as a test file does.
FORBIDDEN_PREFIXES = ("test_",)
FORBIDDEN_NAMES = ("conftest.py",)


def _run_real_copy(src, dest):
    """Source hitl_copy_tools out of the SHIPPED script and run it. No reimplementation."""
    script = (
        'set -euo pipefail\n'
        'sed -n "/^hitl_copy_tools()/,/^}/p" %s > "$TMPDIR_HCT/_hct.sh"\n'
        '. "$TMPDIR_HCT/_hct.sh"\n'
        'hitl_copy_tools %s %s\n' % (
            subprocess.list2cmdline([INIT]),
            subprocess.list2cmdline([src]),
            subprocess.list2cmdline([dest]))
    )
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, TMPDIR_HCT=td)
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)


def _offenders(d):
    if not os.path.isdir(d):
        return []
    return [f for f in os.listdir(d)
            if f.startswith(FORBIDDEN_PREFIXES) or f in FORBIDDEN_NAMES or f == "__pycache__"]


@pytest.mark.parametrize("rel", SYNCED_DIRS)
def test_real_copy_helper_delivers_no_tests(tmp_path, rel):
    """Run the shipped helper against each real synced directory and inspect what lands."""
    src = os.path.join(ROOT, rel)
    if not os.path.isdir(src):
        pytest.skip("%s not present" % rel)
    dest = tmp_path / rel
    p = _run_real_copy(src, str(dest))
    assert p.returncode == 0, p.stderr
    bad = _offenders(str(dest))
    assert not bad, "%s delivered files a consumer cannot run: %s" % (rel, bad)


def test_real_copy_helper_still_delivers_the_validators(tmp_path):
    """Filtering must not become 'copy nothing' — that would pass every other guard here."""
    src = os.path.join(ROOT, "ci", "first-pass")
    dest = tmp_path / "out"
    assert _run_real_copy(src, str(dest)).returncode == 0
    got = set(os.listdir(str(dest)))
    assert "check_skips.py" in got, "the validator CI runs must still be delivered: %s" % got


def test_real_copy_helper_excludes_a_planted_test_and_conftest(tmp_path):
    """Mutation-style: plant the exact files that caused #29 and prove they do not travel."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "tool.py").write_text("# validator\n", encoding="utf-8")
    (src / "test_tool.py").write_text("import ai.shared\n", encoding="utf-8")
    (src / "conftest.py").write_text("import ai.shared\n", encoding="utf-8")
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "tool.cpython-313.pyc").write_bytes(b"\x00")
    dest = tmp_path / "dest"
    assert _run_real_copy(str(src), str(dest)).returncode == 0
    got = set(os.listdir(str(dest)))
    assert got == {"tool.py"}, "expected only the validator, got %s" % got


def test_onboarding_routes_every_tool_directory_through_the_filter(tmp_path):
    """`cp -r` on ci/manifest-drift bypassed the filter entirely and shipped its tests + .pyc."""
    text = io.open(INIT, encoding="utf-8").read()
    assert 'cp -r "$PLATFORM_ROOT/ci/manifest-drift"' not in text, (
        "manifest-drift is copied wholesale, bypassing the test filter")
    for rel in ("ci/first-pass", "ci/manifest-agentic", "tools/manifest-agentic", "ci/manifest-drift"):
        assert 'hitl_copy_tools "$PLATFORM_ROOT/%s"' % rel in text, (
            "%s does not go through hitl_copy_tools" % rel)


def test_generated_gitignore_excludes_bytecode():
    """We copy .py in, so bytecode appears next to it; without this it gets committed."""
    text = io.open(INIT, encoding="utf-8").read()
    assert "__pycache__" in text, "onboarding must add __pycache__ to the consumer .gitignore"


def test_dev_update_cleanup_is_reachable_when_already_on_the_latest_version():
    """The cleanup only ran on the update AFTER the one that shipped it.

    Step 3 said "already on the latest version — no changes" **and stop**, before the re-sync
    steps. A user whose version already matched could therefore never get the repair, which is
    precisely the state they are in when they re-run the command to fix something.
    """
    text = io.open(UPDATE_SKILL, encoding="utf-8").read()
    assert 'Already on the latest version." and stop' not in text, (
        "Step 3 still stops before the re-sync steps")
    assert "do not stop" in text.lower(), "Step 3 must continue to the re-sync steps"


def test_dev_update_rereads_itself_before_any_jump_instruction():
    """A fix shipped IN dev-update must run on the update that delivers it, not the next one.

    Placement is the whole property. The re-read first sat inside Step 3, *after* both
    "continue to Step 4" sentences — so a model following instructions literally jumps past it and
    keeps executing the old, in-context steps. Asserting the text exists is not enough; assert it
    comes before anything that jumps.
    """
    text = io.open(UPDATE_SKILL, encoding="utf-8").read()
    assert "skills/dev-update/SKILL.md" in text, (
        "dev-update must re-read its own newly installed copy after updating")

    reread = text.find("Re-read this skill from the version you just installed")
    assert reread != -1, "the re-read step is missing"
    for jump in re.finditer(r"continue to Step \d", text):
        assert jump.start() > reread, (
            "a 'continue to Step N' jump at offset %d precedes the re-read at %d — the re-read "
            "would be skipped" % (jump.start(), reread))


def test_removal_list_covers_every_test_in_a_synced_directory():
    """Add a test to a synced directory and it must also be listed for cleanup."""
    import re
    listed = set(re.findall(r"(?:ci|tools)/[a-z-]+/(test_[a-z0-9_]+\.py)",
                            io.open(UPDATE_SKILL, encoding="utf-8").read()))
    for rel in SYNCED_DIRS:
        d = os.path.join(ROOT, rel)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.startswith("test_") and f.endswith(".py"):
                assert f in listed, (
                    "%s/%s is synced-adjacent but dev-update would never clean it from a "
                    "consumer repo that already has it" % (rel, f))


def test_synced_validator_still_runs_in_a_consumer_repo(tmp_path):
    """End to end: build a consumer the real way, then run what its CI runs."""
    dest = tmp_path / "consumer"
    (dest / ".hitl").mkdir(parents=True)
    for rel in ("ci/first-pass", "ci/manifest-agentic", "tools/manifest-agentic"):
        src = os.path.join(ROOT, rel)
        if os.path.isdir(src):
            assert _run_real_copy(src, str(dest / rel)).returncode == 0
    catalog = os.path.join(ROOT, "ai", "shared", "workflows.yaml")
    if os.path.isfile(catalog):
        import shutil
        shutil.copy(catalog, str(dest / "ci" / "first-pass" / "workflows.yaml"))
    (dest / ".hitl" / "current-change.yaml").write_text(
        'id: "X-1"\ntier: 1\nfirst_pass: true\n'
        'workflow:\n  name: development\n  steps:\n'
        '    - key: "roi"\n      status: "skipped"\n', encoding="utf-8")

    collect = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "."],
                             cwd=str(dest), capture_output=True, text=True)
    assert "error" not in collect.stdout.lower(), collect.stdout[-2000:]

    run = subprocess.run([sys.executable, "ci/first-pass/check_skips.py",
                          ".hitl/current-change.yaml"], cwd=str(dest),
                         capture_output=True, text=True)
    assert run.returncode == 2, "the synced validator must still fail closed:\n%s" % (
        run.stdout + run.stderr)


def test_real_onboarding_end_to_end_delivers_nothing_unrunnable(tmp_path):
    """Run the actual onboarding script and scan the WHOLE target.

    Every string- and shape-based guard above is evadable: a reviewer reintroduced #29 by writing
    `cp -R` (which the `cp -r` check missed) plus a comment containing the literal
    `hitl_copy_tools "$PLATFORM_ROOT/ci/manifest-drift"` (which satisfied the routing check) — and
    all 61 wiring tests stayed green. Only running the real script and looking at what lands on
    disk closes that, so this is the guard of last resort: no source inspection, just the result.
    """
    init = os.path.join(ROOT, "tools", "scripts", "init-project.sh")
    target = tmp_path / "proj"
    target.mkdir()
    p = subprocess.run(["bash", init, str(target), "--tool", "claude"],
                       capture_output=True, text=True)
    assert p.returncode == 0, "onboarding failed:\n%s" % (p.stdout + p.stderr)[-3000:]

    offenders = []
    for base, dirs, files in os.walk(str(target)):
        if ".git" in base.split(os.sep):
            continue
        if os.path.basename(base) == "__pycache__":
            offenders.append(os.path.relpath(base, str(target)))
            continue
        for f in files:
            if f.startswith("test_") or f == "conftest.py" or f.endswith(".pyc"):
                offenders.append(os.path.relpath(os.path.join(base, f), str(target)))
    assert not offenders, "onboarding delivered files a consumer cannot run: %s" % sorted(offenders)

    # And it must still have delivered something — "copy nothing" would pass the check above.
    assert (target / "ci" / "first-pass" / "check_skips.py").is_file(), \
        "onboarding delivered no validator at all"


def test_onboarding_exposes_every_flat_skill_it_should(tmp_path):
    """A skill onboarding never symlinks is unreachable in a dev-mode repo.

    Source-tree checks miss this entirely: the skill exists, is registered, and still cannot be
    invoked. Run the real script and look for the command.
    """
    init = os.path.join(ROOT, "tools", "scripts", "init-project.sh")
    target = tmp_path / "proj"
    target.mkdir()
    p = subprocess.run(["bash", init, str(target), "--tool", "claude"],
                       capture_output=True, text=True)
    assert p.returncode == 0, (p.stdout + p.stderr)[-2000:]
    cmds = target / ".claude" / "commands"
    assert (cmds / "adversarial-review.md").exists(), (
        "the adversarial-review command is not exposed; onboarded repos cannot run it")
    assert (target / "ci" / "adversarial" / "check_review.py").is_file(), (
        "the release gate validator was not installed")


def _generator_source():
    """The Step 6 change-file generator, lifted out of start-change's SKILL.md."""
    skill = os.path.join(ROOT, "ai", "claude", "start-change", "SKILL.md")
    text = io.open(skill, encoding="utf-8").read()
    m = re.search(r"<< 'PY'\n(.*?)\nPY\n", text, re.S)
    assert m, "Step 6 generator not found"
    return m.group(1)


def test_release_detection_matches_what_the_generator_actually_writes(tmp_path):
    """The gate invocation must fire on the file the sanctioned path produces.

    It did not. dev-validate grepped for `id: release`; the generator writes every scalar through
    json.dumps and emits `id: "release"`. The whole release-gate section silently never ran — round
    one's "the validator is never invoked" defect, alive behind a quoting detail. Checking that both
    files exist could never see this; only running one against the other can.
    """
    validate = io.open(os.path.join(ROOT, "ai", "claude", "validate", "SKILL.md"),
                       encoding="utf-8").read()
    assert "grep -q 'id: release" not in validate, (
        "detection is a bare grep again; it will not match the generator's quoted output")

    # Emit a change file the way the generator does, then run the detection the skill specifies.
    import json
    cc = tmp_path / "current-change.yaml"
    cc.write_text("workflow:\n  id: %s\n" % json.dumps("release"), encoding="utf-8")
    probe = ('import yaml;d=yaml.safe_load(open(%r));'
             'print((d.get("workflow") or {}).get("id",""))' % str(cc))
    got = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True).stdout.strip()
    assert got == "release", (
        "the release workflow is not detectable in the generator's own output (%r)" % got)


def test_start_change_can_actually_seed_a_release():
    """Routing to a workflow the generator will not accept is a route to nowhere."""
    s = io.open(os.path.join(ROOT, "ai", "claude", "start-change", "SKILL.md"),
                encoding="utf-8").read()
    m = re.search(r"WF=<([^>]+)>", s)
    assert m, "the WF enumeration is missing from Step 6"
    assert "release" in m.group(1).split("|"), (
        "Step 3 offers `release` but Step 6 will not seed it: %s" % m.group(1))


def _migrator():
    """The migration script, lifted out of the skill so the test cannot drift from what ships."""
    text = io.open(os.path.join(ROOT, "ai", "claude", "update", "change-file-migration.md"),
                   encoding="utf-8").read()
    m = re.search(r"<< 'PY'\n(.*?)\nPY\n", text, re.S)
    assert m, "migration script not found"
    return m.group(1)


def test_migration_never_writes_a_file_it_cannot_parse(tmp_path):
    """It wrote invalid YAML over a user's change file and reported every step as kept.

    The change file is the repo's governance state; unparseable means their CI blocks every PR
    with MALFORMED and they must hand-edit to escape. start-change already refuses to emit YAML it
    cannot load — this had no such check.
    """
    src = _migrator()
    assert "yaml.safe_load(out)" in src, "the output is written without a parse check"
    assert "MIGRATION ABORTED" in src, "a failed parse must abort, not warn"


def test_migration_refuses_block_style_rather_than_corrupting_it(tmp_path):
    """Splicing flow-map lines into a block-style list is what produced the invalid YAML."""
    mig = tmp_path / "mig.py"
    mig.write_text(_migrator(), encoding="utf-8")
    repo = tmp_path / "repo"
    (repo / ".hitl").mkdir(parents=True)
    import yaml as _y
    rt = _y.safe_load(io.open(os.path.join(ROOT, "ai", "shared", "workflows.yaml"),
                              encoding="utf-8"))["workflows"]["development"]
    doc = {"schema_version": "2.0", "change_id": "T-1", "tier": 2, "status": "pr-ready",
           "workflow": {"id": "development", "version": "2.0.0", "total": rt["total"],
                        "steps": [{"n": s["n"], "key": s["key"], "label": s.get("label"),
                                   "phase": s["phase"], "status": "open"} for s in rt["steps"][:3]]}}
    # safe_dump produces BLOCK style — the shape that corrupted.
    (repo / ".hitl" / "current-change.yaml").write_text(_y.safe_dump(doc, sort_keys=False),
                                                        encoding="utf-8")
    p = subprocess.run([sys.executable, str(mig),
                        os.path.join(ROOT, "ai", "shared", "workflows.yaml"), "9.9.9"],
                       cwd=str(repo), capture_output=True, text=True)
    assert not (repo / ".hitl" / "current-change.yaml.migrated").exists(), (
        "wrote a proposal for a shape it cannot rewrite:\n%s" % p.stdout)
    assert "ABORTED" in (p.stdout + p.stderr)
    _y.safe_load((repo / ".hitl" / "current-change.yaml").read_text(encoding="utf-8"))


def test_migration_keeps_a_teams_own_step():
    """An unknown key is the team's own step, not debris. Dropping it deletes their record."""
    src = _migrator()
    assert "kept_foreign" in src, "unknown-key steps are still dropped"
    assert 'diff.append(f"  - removed  {k}")' not in src


def test_dev_update_does_not_delete_settings_or_unowned_files():
    """Step 4.6 was hardened because a filename is not evidence of authorship. Ninety lines above
    it, the same skill deleted the team's whole settings file and an untracked script."""
    s = io.open(UPDATE_SKILL, encoding="utf-8").read()
    assert "delete `.claude/settings.json` and re-create it" not in s
    assert "settings.json.bak" in s, "the settings file must be backed up before repair"
    assert "git ls-files --error-unmatch .hitl/statusline.sh" in s, (
        "an untracked statusline.sh must not be deleted on name alone")


PREFS_SKILL = os.path.join(ROOT, "ai", "claude", "preferences", "SKILL.md")
DRAFT_SKILL = os.path.join(ROOT, "ai", "claude", "draft-for", "SKILL.md")
CLAUDE_TMPL = os.path.join(ROOT, "ai", "claude", "generate-docs", "templates", "CLAUDE.md.template")


def _markers_written_by(path):
    """The exact BEGIN/END literals the PRODUCER emits, taken from its own BLOCK definition."""
    text = io.open(path, encoding="utf-8").read()
    begins = set(re.findall(r"<!--\s*HITL:[A-Z:]*BEGIN", text))
    ends = set(re.findall(r"<!--\s*HITL:[A-Z:]*END\s*-->", text))
    return begins, ends


def test_the_marker_the_producer_writes_is_the_marker_the_consumer_reads():
    """Producer against consumer, not substrings.

    Renaming the marker in the skill alone leaves every token-based guard green while the session
    instructions grep for a string nothing writes any more. That is exactly how a release gate died
    earlier this week (`grep 'id: release'` versus `id: "release"`).
    """
    begins, ends = _markers_written_by(PREFS_SKILL)
    assert begins and ends, "could not find the markers the preferences skill writes"
    consumer = io.open(CLAUDE_TMPL, encoding="utf-8").read()
    for m in begins | ends:
        stem = m.split("BEGIN")[0].split("END")[0].replace("<!--", "").strip()
        assert stem in consumer, (
            "the skill writes %r but the session instructions never mention %r — nothing will read "
            "what it produces" % (m, stem))


def test_personas_are_wired_at_both_ends():
    """A mechanism nobody is offered and nothing reads is inert — the defect of the week."""
    tmpl = io.open(CLAUDE_TMPL, encoding="utf-8").read()
    assert "/hitl:dev-preferences" in tmpl, "nothing ever offers the preferences command"

    import json
    reg = json.load(io.open(os.path.join(ROOT, "ai", "claude", "plugin", "plugin.json"),
                            encoding="utf-8"))
    for skill in ("ai/claude/preferences", "ai/claude/draft-for"):
        assert skill in reg["skills"], "%s is not registered in plugin.json" % skill
        assert os.path.isfile(os.path.join(ROOT, skill, "SKILL.md")), "%s has no SKILL.md" % skill


def test_the_session_instructions_actually_honour_the_pause():
    """Keeping the word PAUSED while changing the rule to "follow it always" left guards green.

    Assert the whole instruction, not the token — a token survives an inversion, a sentence does not.
    """
    t = " ".join(io.open(CLAUDE_TMPL, encoding="utf-8").read().split())
    assert "unless its marker reads `status: PAUSED`, ignore it entirely and behave as default HITL" in t, (
        "the pause instruction is missing or reworded; PAUSED may be settable but unhonoured")
    assert "follow it always" not in t.lower()
    assert 'If they say "default mode"' in t, "the one-session escape is not instructed"


def test_no_persona_field_is_advertised_without_a_reader():
    """A schema field nothing consumes is the same defect in miniature: it looks like a setting,
    it is documented, and changing it does nothing."""
    import yaml as _y
    tmpl = _y.safe_load(io.open(os.path.join(ROOT, "ai", "shared", "templates", "persona.yaml"),
                                encoding="utf-8").read())
    # A mention is not a reader. This guard used to concatenate draft-for and personas.md and look
    # for the field name anywhere in the blob — so `pushback` counted as wired because personas.md
    # contains the prose 'a profile that reads "doesn't like pushback"'. The field had no row in the
    # table that turns a profile into a draft, and setting it did nothing. Require the ROW.
    text = io.open(DRAFT_SKILL, encoding="utf-8").read()
    rows = [ln for ln in text.splitlines() if ln.startswith("|")]
    style = list((tmpl.get("style") or {}).keys())
    dead = [f for f in style if not any(("`%s" % f) in ln for ln in rows)]
    assert not dead, (
        "style fields with no row in draft-for's instruction table: %s — documented, settable, "
        "and inert" % sorted(dead))

    # Same rule one level up. The first version of this half was the very substring test the
    # comment above rejects: `f not in consumers` over concatenated prose, so any field whose name
    # happens to be an English word already in the docs counted as wired. `email` passed that way.
    # Every top-level field needs a named consumer, and `name` is the only one whose consumer is
    # the lookup rather than a table row.
    top = [k for k in tmpl if k not in ("schema_version", "style")]
    LOOKUP_KEY = "name"
    for f in top:
        if f == LOOKUP_KEY:
            assert "`name:` field" in text, "nothing documents how a profile is matched"
            continue
        assert any(("`%s" % f) in ln for ln in rows), (
            "persona field %r has no row in draft-for's instruction table — documented, settable, "
            "and inert" % f)


def test_preferences_are_project_scoped_by_default():
    """HITL manages projects. A HITL command must not reach into machine-wide config on its own
    initiative — that changes behaviour in every unrelated project the person works in."""
    s = io.open(os.path.join(ROOT, "ai", "claude", "preferences", "SKILL.md"),
                encoding="utf-8").read()
    write_section = _section(s, "## The script")
    assert "~/.claude" not in write_section, (
        "the write path targets the user's global config; it must write to the project CLAUDE.md")
    # Was `p = "CLAUDE.md"`, a bare relative path -- which meant "whatever directory the session
    # started in", so a monorepo package got its own stray CLAUDE.md. The target is now resolved to
    # the repo root. Still the project's file, never the machine-wide one.
    assert "p = claude_md()" in write_section, "the write target must be the project file"
    assert "--show-toplevel" in write_section, (
        "the target must resolve to the repo root, not the current directory")
    assert "expanduser" not in write_section, (
        "the write path reaches into a home directory; it must write to the project CLAUDE.md")
    assert "Do not write there on HITL's initiative" in s, (
        "the global option must be explicitly opt-in, never HITL's default")


def test_preferences_can_be_iterated_paused_and_removed():
    """They asked for all three: keep adjusting, pause, and turn it off for good."""
    raw = io.open(os.path.join(ROOT, "ai", "claude", "preferences", "SKILL.md"),
                  encoding="utf-8").read()
    # Prose in these files is hard-wrapped, so assert on collapsed whitespace — otherwise the test
    # breaks on a reflow rather than on a missing rule.
    s = " ".join(raw.split())
    for mode in ("show", "off", "on", "reset"):
        assert "`%s`" % mode in s, "mode %r is not documented" % mode
    assert "this is an adjustment, not a fresh start" in s, (
        "re-running must adjust, not re-interrogate someone who already answered")
    assert "status: ACTIVE" in s and "PAUSED" in s, "pause must be a state in the file"
    assert "Do not edit the file for a temporary request" in s, (
        "a one-session change must not rewrite the file")


def test_the_persona_floor_is_stated_everywhere_it_could_be_forgotten():
    """Style is negotiable; consequence is not.

    A profile saying "keep it short" must never suppress "this deletes your files" — the exact
    trade a personalisation feature makes easy to get wrong. The rule has to be present wherever
    someone acts on a profile, not only in the doctrine nobody re-reads.
    """
    doctrine = io.open(os.path.join(ROOT, "ai", "shared", "personas.md"), encoding="utf-8").read()
    skill = io.open(os.path.join(ROOT, "ai", "claude", "draft-for", "SKILL.md"), encoding="utf-8").read()
    tmpl = io.open(os.path.join(ROOT, "ai", "claude", "generate-docs", "templates",
                                "CLAUDE.md.template"), encoding="utf-8").read()
    # `"form" in text and "substance" in text` was the original assertion here, and it was
    # vacuous: both are substrings of "platform", "information", "format", "perform". It passed
    # with the entire floor deleted, and passed over a floor rewritten to permit omission when the
    # length setting is short. Assert the SENTENCE, contiguously, on whitespace-collapsed text.
    prefs = io.open(PREFS_SKILL, encoding="utf-8").read()
    block = re.search(r'BLOCK = """(.*?)"""', prefs, re.S)
    assert block, "could not find the block the preferences skill writes"

    REQUIRED = {
        "personas.md": (doctrine, [
            "**A persona shapes form. It never changes substance.**",
            "completeness wins and you compress the *rest*",
        ]),
        "draft-for": (skill, [
            "**Compress the reasoning, never the consequence.** If it will not fit, the reasoning "
            "goes and the risk stays.",
            "Item 3 survives every style setting. That is the floor.",
        ]),
        "CLAUDE.md.template": (tmpl, [
            "**A preference shapes form, never substance.** Risks, costs, uncertainties, and "
            "decisions that are theirs get said whatever the style setting",
        ]),
        # The floor lives INSIDE the emitted block on purpose: the block is what future sessions
        # read, and a floor that lives only in the setup command stops existing when setup ends.
        # Nothing asserted a word of it there, so it could be rewritten to authorise omission and
        # committed to every teammate's CLAUDE.md.
        "the written block": (block.group(1), [
            "Always state a risk, a cost, an uncertainty, or a decision that is the reader's to "
            "make — briefly if that is the setting, but never left out.",
            "cut the reasoning and keep the consequence",
        ]),
    }
    for name, (text, sentences) in REQUIRED.items():
        flat_text = " ".join(text.split())
        for want in sentences:
            assert " ".join(want.split()) in flat_text, (
                "%s no longer states the floor: missing %r" % (name, want))

    # An inversion can keep the required sentence and revoke it in the next one. These are the
    # shapes that revocation takes; each was a surviving mutation in an adversarial round.
    INVERSIONS = (
        r"may be (?:left out|omitted)", r"cut the consequence", r"the risk list goes",
        r"no longer applies", r"risks?,? costs? and uncertainties may", r"compress whatever",
    )
    for name, (text, _) in REQUIRED.items():
        flat_text = " ".join(text.split())
        for bad in INVERSIONS:
            m = re.search(bad, flat_text, re.I)
            assert not m, "%s contains language permitting omission: %r" % (name, m.group(0))

    assert "never sends" in skill.lower() or "Never send it" in skill, (
        "the drafting skill must not send anything on the user's behalf")
    # Assert the INSTRUCTION, not a token. Inverting the rule to "infer one and proceed" while
    # leaving the words "invent one" in a comment kept every token-based guard green.
    flat = " ".join(skill.split())
    assert "If there is no profile, stop and ask." in flat, (
        "the no-profile path must stop and ask; a guessed persona is a stereotype with a filename")
    assert "Do not invent one from their name, their title" in flat
    for bad in ("infer a reasonable one", "infer one from their name", "and proceed."):
        assert bad not in flat, "the no-profile path was inverted to infer-and-proceed: %r" % bad


def test_persona_template_is_valid_and_teaches_preferences_not_assessments():
    import yaml as _y
    p = os.path.join(ROOT, "ai", "shared", "templates", "persona.yaml")
    d = _y.safe_load(io.open(p, encoding="utf-8"))
    assert set(d["style"]) >= {"length", "process_narrative", "lead_with"}
    assert d.get("authored_by") == "", (
        "authored_by must have NO default. 'self' as a default is wrong on the only path that "
        "creates a profile ABOUT someone else, and it silently disables draft-for's disclosure")
    assert "identity" not in d, (
        "the template must not collect a colleague's email — nothing reads it since inbound "
        "matching was removed")
    text = io.open(p, encoding="utf-8").read()
    assert "preferences, not assessments" in text, (
        "the template must steer away from characterising a colleague in version control")


def test_persona_profiles_are_local_by_default_and_removable():
    """A description of how a colleague thinks must not land in a PR diff and git history.

    Deleting the file later does not remove it from history, and the subject is not in the room
    when it is written. Local by default; sharing is a deliberate act.
    """
    init = io.open(INIT, encoding="utf-8").read()
    assert ".hitl/people/" in init, "onboarding must gitignore persona profiles"
    doc = " ".join(io.open(os.path.join(ROOT, "ai", "shared", "personas.md"),
                           encoding="utf-8").read().split())
    assert "Local by default" in doc
    assert "rm .hitl/people/" in doc, "the subject needs a stated way to remove theirs"
    assert "Tell them it exists" in doc, (
        "a stored account of how a colleague thinks that they do not know about is the failure mode")


def test_the_save_path_reads_the_template_rather_than_inventing_a_file():
    """Every wording safeguard lives in the template. If nothing points at it on the save path,
    the discipline applies only when the model happens to have it in context."""
    doc = io.open(os.path.join(ROOT, "ai", "shared", "personas.md"), encoding="utf-8").read()
    assert "templates/persona.yaml" in doc, "the save path never opens the template"
    assert "do not invent a file" in " ".join(doc.split()).lower()


def test_preferences_will_not_record_a_preference_that_suppresses_substance():
    """"No caveats, assume I'm senior" is a reasonable complaint about tone and an unreasonable
    instruction to omit risk. Recorded verbatim it contradicts the floor three lines below it."""
    s = " ".join(io.open(os.path.join(ROOT, "ai", "claude", "preferences", "SKILL.md"),
                         encoding="utf-8").read().split())
    assert "Do not record an answer that would suppress substance" in s
    assert "not a preference this command can store" in s


def test_draft_for_will_not_post_text_the_sender_has_not_read():
    """"Draft this and post it" is permission to post a message, given before anyone saw this one."""
    s = " ".join(io.open(os.path.join(ROOT, "ai", "claude", "draft-for", "SKILL.md"),
                         encoding="utf-8").read().split())
    # Both of the original substrings survive verbatim inside a sentence that REVOKES the rule
    # ("The old rule was never post text the sender has not read; it no longer applies when they
    # asked for a post"). Assert the operative sentences whole, then check for the revocation.
    for want in (
        "**Never send it in the same turn you wrote it.**",
        "That instruction is permission to post *a message*, given before anyone had seen this one.",
        'The rule is not "never post"; it is **never post text the sender has not read**. So: show '
        "the draft, stop, and let them respond to it.",
    ):
        assert " ".join(want.split()) in s, "the no-unread-post rule is missing or reworded: %r" % want
    for bad in (r"so post it", r"post it and show the draft afterwards", r"no longer applies",
                r"standing instruction to post", r"are all fine"):
        m = re.search(bad, s, re.I)
        assert not m, "the rule was inverted while keeping its wording: %r" % m.group(0)


# --- the writer, run against the file HITL itself generates -------------------------------------
#
# Every guard above compares one file's text to another's. None of them ran the writer against a
# real generated CLAUDE.md, and that is exactly where it broke: the template describes the PREFS
# markers in prose, the writer counted marker strings anywhere in the file, so a stock new project
# looked like it already had a block. First run replaced the sentence between the two quoted
# markers -- destroying the instruction that makes the block work, and nesting the block inside it.
# The rule these encode: run the producer against the artifact it actually writes into.

MARK = "P" + "Y"


# Which SECTION of the skill each script lives in. Selecting by position, not by content.
#
# This used to pick a block by a variable name it contained ("BLOCK =", "sys.argv"). An adversarial
# round renamed that variable in the real writer, replaced its body with an unconditional
# whole-file overwrite, and pasted a verbatim copy of the original into an appendix fence. Every
# behavioural guard then exercised the appendix -- a script explicitly labelled as not run -- while
# the writer a user actually invokes destroyed their CLAUDE.md and the suite stayed green. Content-
# addressing a script by a token it happens to contain is not a link to what a user runs.
# One script now, four modes. It was three near-identical copies, and that duplication was itself
# the defect: the repo-root, fence and traceback fixes each reached some copies and not others.
PREFS_SECTIONS = {k: "## The script" for k in ("write", "flip", "reset", "show")}
PREFS_DEFAULT_MODE = {"write": "write", "reset": "reset", "show": "show"}   # flip always gets one


def _fences(text):
    """Character spans covered by ``` fenced blocks."""
    marks = [m.start() for m in re.finditer(r"^```", text, re.M)]
    return list(zip(marks[0::2], marks[1::2]))


def _section(text, heading):
    """The body of one `## ` section, from its heading to the next heading OUTSIDE a code fence.

    The fence check is load-bearing and was missing at first: the writer's own emitted block
    contains a line starting `## `, inside the heredoc. Taking the next `\n## ` naively cut the
    section in half, mid-fence, and the script could not be found at all. Same shape as the bug
    these guards exist for — a piece of content being read as structure.
    """
    i = text.find("\n" + heading + "\n")
    assert i != -1, "section %r not found" % heading
    i += 1
    spans = _fences(text)
    level = len(heading) - len(heading.lstrip("#"))
    nxt = r"\n#{1,%d} " % level
    for m in re.finditer(nxt, text[i + len(heading):]):
        pos = i + len(heading) + m.start()
        if not any(a <= pos <= b for a, b in spans):
            return text[i:pos]
    return text[i:]


def _prefs_script(kind):
    """Lift the embedded script from the SECTION that documents it. kind: write | flip | reset."""
    text = io.open(PREFS_SKILL, encoding="utf-8").read()
    body = _section(text, PREFS_SECTIONS[kind])
    blocks = re.findall(r"<<'%s'\n(.*?)\n%s\n" % (MARK, MARK), body, re.S)
    assert len(blocks) == 1, (
        "expected exactly one embedded script under %r, found %d — a second fence in the section "
        "makes it ambiguous which one a user runs" % (PREFS_SECTIONS[kind], len(blocks)))
    mode = PREFS_DEFAULT_MODE.get(kind)
    # `write` takes the four answers as arguments, because pasting them into the script made a
    # backslash a Python escape and a % a format specifier. Supply representative ones so callers
    # that only care about file handling do not have to.
    extra = (["short — lead with the answer", "only when asked",
              "the decision the reader needs to make", "say it straight"]
             if kind == "write" else [])
    prefix = ("import sys\nif len(sys.argv) < 2: sys.argv[1:] = %r\n" % ([mode] + extra)) \
        if mode else ""
    return prefix + blocks[0]


def _fresh_project(tmp_path):
    """A CLAUDE.md as REAL onboarding produces it, by running init-project.sh.

    This used to copy the template directly. Real onboarding appends the managed HITL block on top
    of it, so the fixture was ~26 lines short of what a user actually has -- and a mutation round
    put a documentation example of a PREFS block, at line start, inside that managed block. Every
    behavioural guard stayed green while the writer misbehaved on a really-onboarded project.
    A fixture that is not what onboarding emits is a fixture that tests a project nobody has.
    """
    d = tmp_path / "proj"
    d.mkdir()
    subprocess.run(["git", "init", "-q", "."], cwd=str(d), check=True)
    (d / "CLAUDE.md").write_text(_onboarded_claude_md(), encoding="utf-8")
    return d


_ONBOARDED = []


def _onboarded_claude_md():
    """Run real onboarding ONCE per session and reuse its CLAUDE.md.

    Running it per test roughly doubled the suite. The property that matters is that the fixture is
    byte-identical to what onboarding emits, not that each test re-runs the script.
    """
    if not _ONBOARDED:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init", "-q", "."], cwd=td, check=True)
            r = subprocess.run(["bash", INIT, td, "--tool", "claude", "--name", "Acme"],
                               cwd=td, capture_output=True, text=True)
            f = os.path.join(td, "CLAUDE.md")
            assert os.path.isfile(f), (
                "onboarding produced no CLAUDE.md (rc=%s)\n%s" % (r.returncode, r.stderr[-600:]))
            text = io.open(f, encoding="utf-8").read()
        assert "HITL:BEGIN" in text, (
            "onboarding did not write its managed block; the fixture would not match a real project")
        _ONBOARDED.append(text)
    return _ONBOARDED[0]


def _run(script, cwd, args=()):
    return subprocess.run([sys.executable, "-c", script, *args], cwd=str(cwd),
                          capture_output=True, text=True)


def test_the_generated_claude_md_is_not_mistaken_for_a_preferences_block(tmp_path):
    """First run on a stock project must APPEND, never edit the instructions around it."""
    d = _fresh_project(tmp_path)
    before = (d / "CLAUDE.md").read_text(encoding="utf-8")
    r = _run(_prefs_script("write"), d)
    assert r.returncode == 0, "writer refused on a stock generated project: %s" % r.stderr
    after = (d / "CLAUDE.md").read_text(encoding="utf-8")
    assert after.startswith(before.rstrip("\n")), (
        "the writer modified the generated instructions instead of appending after them")
    for line in before.splitlines():
        assert line in after.splitlines(), "generated line lost: %r" % line


def test_the_pause_instruction_survives_the_first_write(tmp_path):
    """The sentence telling Claude to obey the block is the thing the collision destroyed.

    Assert CONTIGUITY, not presence. When the block was injected mid-sentence, the tail still read
    "...behave as default HITL" further down the file, so a substring check stayed green over
    output that had the whole block wedged inside the instruction.
    """
    d = _fresh_project(tmp_path)
    instruction = " ".join(
        re.search(r"If this file contains a block.*?default HITL\.",
                  io.open(CLAUDE_TMPL, encoding="utf-8").read(), re.S).group(0).split())
    _run(_prefs_script("write"), d)
    after = " ".join((d / "CLAUDE.md").read_text(encoding="utf-8").split())
    assert instruction in after, (
        "the consumer instruction is no longer contiguous — the writer wrote into the middle of it")


def test_regenerating_claude_md_over_an_existing_block_leaves_off_working(tmp_path):
    """F1b's real path: dev-update regenerates the instructions above a block already in place.

    That file holds the template's marker mentions AND a real block. Unanchored counting sees two
    of each and refuses everything at once — `off`, `on`, `reset` and the writer — so the safety
    valve is welded shut and hand-editing markdown is the only way out.
    """
    d = _fresh_project(tmp_path)
    assert _run(_prefs_script("write"), d).returncode == 0
    p = d / "CLAUDE.md"
    p.write_text(io.open(CLAUDE_TMPL, encoding="utf-8").read() + "\n" +
                 p.read_text(encoding="utf-8"), encoding="utf-8")
    r = _run(_prefs_script("flip"), d, ["off"])
    assert r.returncode == 0, "`off` refused after a regeneration: %s%s" % (r.stdout, r.stderr)
    assert "PAUSED" in p.read_text(encoding="utf-8")


@pytest.mark.parametrize("mode", ["off", "on"])
def test_the_escape_hatches_work_on_a_stock_project(tmp_path, mode):
    """`off` is the safety valve. A second marker pair anywhere welds it shut."""
    d = _fresh_project(tmp_path)
    assert _run(_prefs_script("write"), d).returncode == 0
    r = _run(_prefs_script("flip"), d, [mode])
    assert r.returncode == 0, "`%s` failed on a stock generated project: %s" % (mode, r.stderr)
    assert ("PAUSED" if mode == "off" else "ACTIVE") in (d / "CLAUDE.md").read_text(encoding="utf-8")


def test_reset_removes_only_the_block_from_a_stock_project(tmp_path):
    d = _fresh_project(tmp_path)
    generated = (d / "CLAUDE.md").read_text(encoding="utf-8")
    assert _run(_prefs_script("write"), d).returncode == 0
    r = _run(_prefs_script("reset"), d)
    assert r.returncode == 0, "reset refused on a stock generated project: %s" % r.stderr
    assert (d / "CLAUDE.md").read_text(encoding="utf-8").rstrip("\n") == generated.rstrip("\n"), (
        "reset did not restore the file it started from")


def test_marker_tests_are_anchored_to_line_start():
    """The structural fix. Unanchored counting is what let prose impersonate a block."""
    for kind in ("write", "flip", "reset"):
        # Drop the BLOCK literal: it legitimately contains the bare marker it EMITS. Only the
        # patterns used to MATCH markers have to be anchored.
        src = re.sub(r'"""(?:.|\n)*?"""', '""', _prefs_script(kind))
        for m in re.findall(r'r?"\^?<!-- HITL:PREFS:(?:BEGIN|END)[^"]*"', src):
            assert m.lstrip("r").startswith('"^'), (
                "%s script matches %s unanchored — prose mentioning a marker will count as one"
                % (kind, m))


def test_the_writer_discloses_that_the_block_is_shared_and_names_who_set_it():
    """`CLAUDE.md` is committed, so "Scope: this project" reads as privacy but means the team.

    The persona path — which describes someone else — got gitignoring, subject rights and authorship
    disclosure. The artifact that is actually shared got none of it, and a teammate would receive a
    colleague's settings with no way to tell whose they were.
    """
    s = " ".join(io.open(PREFS_SKILL, encoding="utf-8").read().split())
    assert "committed" in s and "team" in s.lower(), "the sharing consequence is never stated"
    assert "~/.claude/CLAUDE.md" in s, "no alternative offered for someone who wants it private"
    block = re.search(r'BLOCK = """(.*?)"""', s, re.S)
    assert block and "set by %(who)s" in block.group(1), "the block does not record who set it"
    assert "git config user.name" in s, "nothing tells the writer where the name comes from"
    assert "never pasted into it" in s, (
        "the skill must say the name is read as data — instructing a model to substitute it into "
        "the script is what let a name close the string literal and execute")


def test_a_persona_note_cannot_authorize_an_omission():
    """`notes` was told to override the rows above, and the rows above include nothing but style.

    Preferences refuses to store "no warnings"; a persona file can hold that same sentence in the
    one field draft-for reads last and lets win — and can hold it in the voice of a third party who
    never said it.
    """
    draft = " ".join(io.open(os.path.join(ROOT, "ai", "claude", "draft-for", "SKILL.md"),
                             encoding="utf-8").read().split())
    assert "overrides the **style** rows above, and nothing else" in draft, (
        "notes still claims blanket override authority")
    assert "cannot authorize leaving something out" in draft.lower()
    tmpl = io.open(os.path.join(ROOT, "ai", "shared", "templates", "persona.yaml"),
                   encoding="utf-8").read()
    assert "STYLE ONLY" in tmpl, "the template invites free text without naming the limit"


def test_unset_authorship_is_never_reported_as_self_authored():
    """authored_by has no safe default, and the blank case is the one that most needs disclosing."""
    draft = " ".join(io.open(os.path.join(ROOT, "ai", "claude", "draft-for", "SKILL.md"),
                             encoding="utf-8").read().split())
    assert "empty or missing" in draft, "the unset case has no defined behaviour"
    assert "Never let an unset field read as self-authored" in draft


def test_persona_subject_rights_are_stated_as_obligations_not_capabilities():
    """The files are local, so the subject cannot run any of these commands; the holder can."""
    s = " ".join(io.open(os.path.join(ROOT, "ai", "shared", "personas.md"),
                         encoding="utf-8").read().split())
    assert "cannot list it, read it, or delete it" in s, (
        "the doc still presents these as rights the subject can exercise")


def test_off_before_setup_says_so_rather_than_blaming_the_block(tmp_path):
    """"No status marker in the block" on a project that has no block sends people hand-editing."""
    d = _fresh_project(tmp_path)
    r = _run(_prefs_script("flip"), d, ["off"])
    assert r.returncode != 0
    assert "nothing to off" in (r.stdout + r.stderr), (
        "the no-block case is reported as a malformed block: %s" % (r.stdout + r.stderr))


def test_the_main_hitl_block_matcher_is_anchored_too():
    """Same latent defect, one file over: documenting a marker must not create one."""
    src = io.open(os.path.join(ROOT, "tools", "hitl-onboarding", "ensure_claude_block.py"),
                  encoding="utf-8").read()
    assert 'r"^" + re.escape(begin)' in src, "_span/count are unanchored — prose can impersonate a block"
    assert "re.S | re.M" in src, "the span regex is not multiline-anchored"


def test_documenting_the_markers_does_not_create_a_block():
    """The generalised rule, asserted behaviourally: a file that only DESCRIBES the markers is a
    file with no block, for both writers."""
    import importlib.util
    p = os.path.join(ROOT, "tools", "hitl-onboarding", "ensure_claude_block.py")
    spec = importlib.util.spec_from_file_location("_ecb", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    prose = ("# Team rules\n\nThe onboarding writes a block between `<!-- HITL:BEGIN` and "
             "`<!-- HITL:END -->` markers.\n\nKeep our own rules below.\n")
    out, action = mod.apply(prose, "<!-- HITL:BEGIN -->\nx\n<!-- HITL:END -->")
    assert action == "appended", "a prose mention was treated as an existing block (%s)" % action
    assert prose.rstrip("\n") in out, "the sentence describing the markers was modified"


def _proj_with_name(tmp_path, who):
    d = _fresh_project(tmp_path)
    subprocess.run(["git", "init", "-q", "."], cwd=str(d), check=True)
    subprocess.run(["git", "config", "user.name", who], cwd=str(d), check=True)
    return d


def test_the_authors_name_is_read_as_data_not_pasted_into_the_script(tmp_path):
    """`git config user.name` accepts quotes, newlines and `-->`. The skill used to instruct a
    model to substitute it into a `\"\"\"` literal, so a name could close the string and execute."""
    payload = 'Ada """ + open("/etc/passwd").read() + """ X'
    d = _proj_with_name(tmp_path, payload)
    r = _run(_prefs_script("write"), d)
    assert r.returncode == 0, r.stderr
    text = (d / "CLAUDE.md").read_text(encoding="utf-8")
    assert "root:" not in text, "the name was evaluated as code — /etc/passwd reached CLAUDE.md"
    assert payload.split(" X")[0][:12] in text, "the name should survive as inert text"


@pytest.mark.parametrize("who,why", [
    ("Ada\nEve", "a newline would forge a second line inside the marker"),
    ("Ada --> <!-- HITL:PREFS:BEGIN", "a name must not be able to close or open a marker"),
])
def test_a_hostile_name_cannot_break_the_marker(tmp_path, who, why):
    d = _proj_with_name(tmp_path, who)
    assert _run(_prefs_script("write"), d).returncode == 0
    text = (d / "CLAUDE.md").read_text(encoding="utf-8")
    assert len(re.findall(r"^<!-- HITL:PREFS:BEGIN", text, re.M)) == 1, why
    assert len(re.findall(r"^<!-- HITL:PREFS:END -->", text, re.M)) == 1, why
    assert _run(_prefs_script("flip"), d, ["off"]).returncode == 0, (
        "the block is no longer operable after a hostile name: " + why)


def test_an_unset_name_stops_rather_than_recording_nobody(tmp_path):
    d = _fresh_project(tmp_path)
    subprocess.run(["git", "init", "-q", "."], cwd=str(d), check=True)
    subprocess.run(["git", "config", "user.name", ""], cwd=str(d), check=True)
    r = _run(_prefs_script("write"), d)
    assert r.returncode != 0, "wrote a block attributed to nobody"
    assert "user.name" in (r.stdout + r.stderr)


def test_adjusting_a_paused_block_does_not_silently_reactivate_it(tmp_path):
    """`off` then adjust rewrote the whole span from a template that hardcodes ACTIVE."""
    d = _proj_with_name(tmp_path, "Ada Lovelace")
    assert _run(_prefs_script("write"), d).returncode == 0
    assert _run(_prefs_script("flip"), d, ["off"]).returncode == 0
    r = _run(_prefs_script("write"), d)
    assert r.returncode == 0
    assert "status: PAUSED" in (d / "CLAUDE.md").read_text(encoding="utf-8"), (
        "adjusting the bullets turned the preferences back on")
    assert "PAUSED" in r.stdout, "the user is not told their pause was kept"


def test_replacing_someone_elses_name_is_reported(tmp_path):
    d = _proj_with_name(tmp_path, "Ada Lovelace")
    assert _run(_prefs_script("write"), d).returncode == 0
    subprocess.run(["git", "config", "user.name", "Bob Ross"], cwd=str(d), check=True)
    r = _run(_prefs_script("write"), d)
    assert "Ada Lovelace" in r.stdout, (
        "silently took over a teammate's block: %s" % r.stdout)


def test_reset_returns_the_file_byte_for_byte(tmp_path):
    """The message claims the rest of the file is untouched, so make that literally true."""
    d = _proj_with_name(tmp_path, "Ada Lovelace")
    before = (d / "CLAUDE.md").read_text(encoding="utf-8")
    assert _run(_prefs_script("write"), d).returncode == 0
    assert _run(_prefs_script("reset"), d).returncode == 0
    assert (d / "CLAUDE.md").read_text(encoding="utf-8") == before, "reset left the file changed"


def test_generate_docs_neither_mislocates_nor_clobbers_claude_md():
    """It pointed at a path that does not exist, and said "generate" with no preserve rule — over a
    project carrying both marked blocks that is a silent delete of onboarding AND preferences."""
    p = os.path.join(ROOT, "ai", "claude", "generate-docs", "SKILL.md")
    s = io.open(p, encoding="utf-8").read()
    # This guard resolved ${CLAUDE_PLUGIN_ROOT} against the SOURCE tree, so it happily accepted a
    # path that exists here and nowhere in the built plugin -- which is exactly what shipped.
    # build.sh flattens ai/claude/generate-docs/templates/ AND ai/shared/templates/ into
    # shared/templates/, so resolve the way the plugin lays it out, not the way the repo does.
    for m in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}[\w/.-]*CLAUDE\.md\.template", s):
        rel = m.replace("${CLAUDE_PLUGIN_ROOT}/", "")
        assert rel.startswith("shared/templates/"), (
            "%s does not resolve in the built plugin, where templates live under shared/templates/"
            % m)
        src = os.path.join(ROOT, "ai", "claude", "generate-docs", "templates",
                           os.path.basename(rel))
        alt = os.path.join(ROOT, "ai", "shared", "templates", os.path.basename(rel))
        assert os.path.isfile(src) or os.path.isfile(alt), (
            "no source file feeds %s" % m)
    assert "do not overwrite it" in s.lower(), "no preserve rule on a file teams edit"
    assert "HITL:PREFS:BEGIN" in s, "the preserve rule does not name the preferences block"


# --- the floor, pinned ---------------------------------------------------------------------------
#
# Two adversarial rounds established that a blacklist of revocation phrases cannot be completed.
# Every required sentence stayed verbatim while a NEW sentence was added beside it:
#
#   "**One practical exception.** When a profile sets `length: short`, treat the four bullets above
#    as guidance rather than requirements ... drop the risk and cost lines."
#   "The sender can lower it. If they ask for just the summary, they have taken responsibility."
#
# Nothing that greps for approved wording can see those, because they add rather than change. So
# pin the whole region instead: any edit inside it, of any shape, fails until someone updates the
# hash here. Changing the floor becomes a deliberate, reviewable act rather than a silent one.
#
# WHEN THIS TEST FAILS: read the diff. If the change genuinely belongs in the floor, run
#   python3 ci/wiring/test_shipped_tools_are_self_contained.py --print-floor-hashes
# and paste the new value in. Do not update a hash you have not read the diff for.

import hashlib

FLOOR_REGIONS = {
    "CLAUDE.md template / communication preferences": (
        ('ai', 'claude', 'generate-docs', 'templates', 'CLAUDE.md.template'), '## Communication Preferences',
        "d3f10e4c1ca94fb57273bb5421fd3a5c1e40bb8be240d8089d9c8b054dee9ca3"),
    "draft-for / find the person": (
        ('ai', 'claude', 'draft-for', 'SKILL.md'), '## Step 1 — Find the person',
        "e92fcbc99cf3ec943d0c1c91e7389aa32f980833d8a1379c9d63d474cb7f6eb4"),
    "draft-for / hand it over": (
        ('ai', 'claude', 'draft-for', 'SKILL.md'), '## Step 4 — Hand it over with its provenance',
        "c21319895e3b33480f4552838531cf3ff17cfe82477b2a9d13bb926ca73124d6"),
    "draft-for / what this is not for": (
        ('ai', 'claude', 'draft-for', 'SKILL.md'), '## What this is not for',
        "0a764e69130523218f2a00fd66c5a5ad0197b7d4f1be70ceef61aa1e4d41adac"),
    "draft-for / what you are writing": (
        ('ai', 'claude', 'draft-for', 'SKILL.md'), '## Step 2 — Establish what you are actually writing',
        "25dddd4c827233f7f8d054fc03eee363bcc092bcd479c256a1e879c43a638802"),
    "draft-for / write to the profile": (
        ('ai', 'claude', 'draft-for', 'SKILL.md'), '## Step 3 — Write to the profile',
        "6ca55d129e0b9b0bda6bfc996d54b26e7112604d01ca269495d39fbd1b6121f4"),
    "generate-docs / phase R5 process setup": (
        ('ai', 'claude', 'generate-docs', 'SKILL.md'), '### Phase R5 — Process Setup (Day 5 equivalent)',
        "8b1b7b3743d269b8893051e8348433c640c100e1d2483c4e3eec9f7f127d6e96"),
    "personas.md / offering it": (
        ('ai', 'shared', 'personas.md'), '## Offering it',
        "cba3c5b499aa96d9716a6df7977a890e44aef0fee4d0ac55586cca0772f8789f"),
    "personas.md / outbound": (
        ('ai', 'shared', 'personas.md'), '## Outbound',
        "58d5c2b4e26cb4358a9b69f7060ca34f1e961e5d49200c767a2bc1673023b3d1"),
    "personas.md / the floor": (
        ('ai', 'shared', 'personas.md'), '## The floor — read this before anything else',
        "f3051b8ffe17ae4850dd5b1c7a6d47f16d59958c9dcc8afa764cfbabf934b034"),
    "personas.md / where they live": (
        ('ai', 'shared', 'personas.md'), '## Where they live, and who can undo them',
        "704907220b4d49f520196f9fab72389be6f223e711f2696b2383672a975df23b"),
    "personas.md / whose profile is it": (
        ('ai', 'shared', 'personas.md'), '## Whose profile is it',
        "529deec65e92b6c5faf7836a755cb167fac7cf79cda0510e32dbb77a01b6efb6"),
    "preferences / if they ask for it everywhere": (
        ('ai', 'claude', 'preferences', 'SKILL.md'), '## If they ask for it everywhere',
        "049c73e140b652abfa305401ad1d73866dfca38412908e13479a68ffdaecc094"),
    "preferences / modes": (
        ('ai', 'claude', 'preferences', 'SKILL.md'), '## Modes',
        "348425cc4d5c719cf944190472a7fba9fdd5529757a21d741a8c2f4c081e77c1"),
    "preferences / setting up and adjusting": (
        ('ai', 'claude', 'preferences', 'SKILL.md'), '## Setting up, and adjusting',
        "289efeeb0ee9500642074772628cb71520dda7daa186e232d3690395bd4f1bd5"),
    "preferences / the floor lives in the file": (
        ('ai', 'claude', 'preferences', 'SKILL.md'), '## The floor, and why it lives in the file',
        "08b31fba29f94780e5bc2af96d89e9fc3e1372462f4e6c9f3dfd3284129ec36c"),
    "preferences / when to offer this": (
        ('ai', 'claude', 'preferences', 'SKILL.md'), '## When to offer this',
        "dca62287136cccf5bbf55c9f0d25735288452896319f114dd38eecd221699b8d"),
}


def _floor_text(parts, heading):
    text = io.open(os.path.join(ROOT, *parts), encoding="utf-8").read()
    return " ".join(_section(text, heading).split())


def _floor_hash(parts, heading):
    return hashlib.sha256(_floor_text(parts, heading).encode("utf-8")).hexdigest()


def _emitted_block_hash():
    """The floor inside the block the writer commits into a team's CLAUDE.md."""
    prefs = io.open(PREFS_SKILL, encoding="utf-8").read()
    block = re.search(r'BLOCK = """(.*?)"""', prefs, re.S)
    assert block, "could not find the emitted block"
    return hashlib.sha256(" ".join(block.group(1).split()).encode("utf-8")).hexdigest()


@pytest.mark.parametrize("name", sorted(FLOOR_REGIONS))
def test_the_floor_region_is_unchanged(name):
    parts, heading, pinned = FLOOR_REGIONS[name]
    got = _floor_hash(parts, heading)
    assert got == pinned, (
        "the floor region %r changed.\n"
        "Read the diff before doing anything. A sentence ADDED beside the floor can revoke it "
        "while every required phrase stays verbatim, which is how this region was defeated twice.\n"
        "If the change is intended, re-pin with --print-floor-hashes.\n"
        "  expected %s\n  got      %s" % (name, pinned, got))


def test_the_floor_inside_the_emitted_block_is_unchanged():
    """This one is committed into every teammate's CLAUDE.md, so it is the copy that matters most."""
    assert _emitted_block_hash() == EMITTED_BLOCK_SHA, (
        "the block the writer commits into a team's CLAUDE.md changed. Read the diff: an added "
        "exception here reaches every session in the repo.\n  expected %s\n  got      %s"
        % (EMITTED_BLOCK_SHA, _emitted_block_hash()))


EMITTED_BLOCK_SHA = "afeda8c4539e76bc8c98183f80a9011492fa9273d122cae35b3f4fc5b288d381"


if __name__ == "__main__":
    import sys as _s
    if "--print-floor-hashes" in _s.argv:
        for _n in sorted(FLOOR_REGIONS):
            _p, _h, _ = FLOOR_REGIONS[_n]
            print('    "%s": (\n        %r, %r,\n        "%s"),' % (_n, _p, _h, _floor_hash(_p, _h)))
        print('EMITTED_BLOCK_SHA = "%s"' % _emitted_block_hash())


# --- refusals and anchoring, asserted by BEHAVIOUR ------------------------------------------------
#
# A mutation round deleted the symlink refusal, deleted the malformed-marker refusal, and un-anchored
# the marker counting three different ways (single quotes, a built-up variable, re.escape). All
# stayed green: the guards asserted the SHAPE of the source, so any other spelling evaded them, and
# the one behavioural anchoring test used the generated template, which no longer mentions a marker
# inline. These run each real script against a fixture built to trigger the thing being guarded.

INLINE_MENTION = (
    "# Team rules\n\n"
    "Never force-push main.\n\n"
    "The preferences block sits between `<!-- HITL:PREFS:BEGIN` and `<!-- HITL:PREFS:END -->`.\n\n"
    "Run make test before every PR.\n"
)


def _prefs_bash(heading):
    text = io.open(PREFS_SKILL, encoding="utf-8").read()
    body = _section(text, heading)
    m = re.search(r"```bash\n(.*?)\n```", body, re.S)
    assert m, "no bash fence under %r" % heading
    return m.group(1)


def _proj(tmp_path, content):
    d = tmp_path / "p"
    d.mkdir()
    (d / "CLAUDE.md").write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q", "."], cwd=str(d), check=True)
    subprocess.run(["git", "config", "user.name", "Ada Lovelace"], cwd=str(d), check=True)
    return d


@pytest.mark.parametrize("kind", ["write", "flip", "reset"])
def test_a_marker_named_in_prose_is_not_treated_as_a_block(tmp_path, kind):
    """Any file may DESCRIBE the markers. Only a line that starts with one is a block."""
    d = _proj(tmp_path, INLINE_MENTION)
    before = (d / "CLAUDE.md").read_text(encoding="utf-8")
    r = _run(_prefs_script(kind), d, ["off"] if kind == "flip" else [])
    after = (d / "CLAUDE.md").read_text(encoding="utf-8")
    if kind == "write":
        assert r.returncode == 0, "the writer refused on a file that merely mentions a marker"
        assert after.startswith(before.rstrip("\n")), "the writer edited the prose instead of appending"
    else:
        assert r.returncode != 0, "%s acted on a file with no block" % kind
        assert after == before, "%s modified a file that only mentions the markers" % kind


@pytest.mark.parametrize("kind", ["write", "flip", "reset"])
def test_no_script_writes_through_a_symlink(tmp_path, kind):
    """CLAUDE.md symlinked to ~/.claude/CLAUDE.md is a real setup, and that target is the one file
    this feature promises never to touch on its own initiative."""
    d = tmp_path / "p"
    d.mkdir()
    target = tmp_path / "machine-wide.md"
    target.write_text("# my own global rules\n", encoding="utf-8")
    (d / "CLAUDE.md").symlink_to(target)
    subprocess.run(["git", "init", "-q", "."], cwd=str(d), check=True)
    subprocess.run(["git", "config", "user.name", "Ada Lovelace"], cwd=str(d), check=True)
    r = _run(_prefs_script(kind), d, ["off"] if kind == "flip" else [])
    assert r.returncode != 0, "%s wrote through a symlink" % kind
    assert target.read_text(encoding="utf-8") == "# my own global rules\n", (
        "%s edited the symlink target" % kind)


@pytest.mark.parametrize("kind", ["write", "flip", "reset"])
@pytest.mark.parametrize("label,body", [
    ("duplicate", "# Rules\n\n<!-- HITL:PREFS:BEGIN status: ACTIVE -->\na\n<!-- HITL:PREFS:END -->\n"
                  "\n<!-- HITL:PREFS:BEGIN status: ACTIVE -->\nb\n<!-- HITL:PREFS:END -->\n"),
    ("orphan-begin", "# Rules\n\n<!-- HITL:PREFS:BEGIN status: ACTIVE -->\n\nour own rules\n"),
])
def test_malformed_markers_are_refused_not_guessed(tmp_path, kind, label, body):
    """A wrong guess about which span is ours deletes content HITL does not own."""
    d = _proj(tmp_path, body)
    before = (d / "CLAUDE.md").read_text(encoding="utf-8")
    r = _run(_prefs_script(kind), d, ["off"] if kind == "flip" else [])
    assert r.returncode != 0, "%s guessed on %s markers instead of refusing" % (kind, label)
    assert (d / "CLAUDE.md").read_text(encoding="utf-8") == before, (
        "%s modified a file with %s markers" % (kind, label))


def test_show_reports_the_block_and_only_the_block(tmp_path):
    """`show` was guarded by nothing at all. Unanchored, it opened a range at a prose mention and
    printed to end of file, presenting most of CLAUDE.md as "your current settings"."""
    d = _proj(tmp_path, INLINE_MENTION)
    r = _run(_prefs_script("show"), d)
    assert "No HITL preferences set" in r.stdout, (
        "show reported settings for a project that has none: %r" % r.stdout[:200])
    assert "Never force-push main" not in r.stdout, "show dumped the team's own rules"

    assert _run(_prefs_script("write"), d).returncode == 0
    r2 = _run(_prefs_script("show"), d)
    assert "HITL:PREFS:BEGIN" in r2.stdout and "HITL:PREFS:END" in r2.stdout
    assert "Never force-push main" not in r2.stdout, "show printed content outside the block"


def test_onboarding_actually_ignores_persona_profiles(tmp_path):
    """The guard asserted the path appeared in init-project.sh. A COMMENT satisfied that, while the
    real grep and the real printf both carried a typo and the profiles stayed tracked."""
    d = tmp_path / "proj"
    d.mkdir()
    subprocess.run(["git", "init", "-q", "."], cwd=str(d), check=True)
    r = subprocess.run(["bash", INIT, str(d), "--tool", "claude", "--name", "Acme"],
                       capture_output=True, text=True, cwd=str(d))
    gi = d / ".gitignore"
    assert gi.is_file(), "onboarding produced no .gitignore (rc=%s) %s" % (r.returncode, r.stderr[-400:])
    lines = [ln.strip() for ln in gi.read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    assert ".hitl/people/" in lines, (
        "a profile describing a colleague would be committed. .gitignore rules: %s" % lines)


@pytest.mark.parametrize("kind", ["flip", "reset", "write"])
def test_a_prose_mention_beside_a_real_block_does_not_weld_the_controls_shut(tmp_path, kind):
    """The harm case for unanchored counting, which the prose-only fixture cannot reach.

    With a mention AND a block present, unanchored counting sees two of each and every control
    refuses at once: `off` (the safety valve), `on`, `reset`, and the writer. The only way out is
    hand-editing markdown. A prose-only file still errors for an unrelated reason, so it passes
    even while this is broken -- which is exactly how an un-anchored `flip` survived a mutation
    round after the anchoring fix was supposedly in place.
    """
    d = _proj(tmp_path, INLINE_MENTION)
    assert _run(_prefs_script("write"), d).returncode == 0, "setup: could not write the block"
    p = d / "CLAUDE.md"
    assert "<!-- HITL:PREFS:BEGIN" in p.read_text(encoding="utf-8").split("\n", 4)[4], "setup"

    r = _run(_prefs_script(kind), d, ["off"] if kind == "flip" else [])
    assert r.returncode == 0, (
        "`%s` refused while a block was present, because a marker named in prose was counted as "
        "one: %s%s" % (kind, r.stdout, r.stderr))
    text = p.read_text(encoding="utf-8")
    if kind == "flip":
        assert "status: PAUSED" in text, "the pause did not take"
    elif kind == "reset":
        assert "<!-- HITL:PREFS:BEGIN" not in text.replace("`<!-- HITL:PREFS:BEGIN", ""), "block not removed"
        assert "Never force-push main" in text, "reset took the team's rules with it"


def test_the_persona_directory_agrees_across_every_file_that_names_it():
    """S11: the read side was renamed to `.hitl/profiles/` and nothing noticed.

    Onboarding gitignores one path, the doctrine documents one, and the skill lists another. Rename
    any one of them and profiles are read from a directory that is not the ignored one, so they get
    committed. Producer against consumer, not each file against itself.
    """
    files = {
        "init-project.sh": io.open(INIT, encoding="utf-8").read(),
        "personas.md": io.open(os.path.join(ROOT, "ai", "shared", "personas.md"),
                               encoding="utf-8").read(),
        "draft-for/SKILL.md": io.open(DRAFT_SKILL, encoding="utf-8").read(),
        "persona.yaml": io.open(os.path.join(ROOT, "ai", "shared", "templates", "persona.yaml"),
                                encoding="utf-8").read(),
    }
    for name, text in files.items():
        # Only lines that are ABOUT profiles. init-project.sh legitimately names .hitl/hooks/ and
        # other unrelated directories.
        lines = [ln for ln in text.splitlines()
                 if re.search(r"\.hitl/[a-z-]+/", ln)
                 and re.search(r"persona|profile|people|<slug>|kishor", ln, re.I)]
        found = set()
        for ln in lines:
            found |= set(re.findall(r"\.hitl/[a-z-]+/", ln))
        assert found, "%s names no persona directory at all" % name
        assert found == {".hitl/people/"}, (
            "%s refers to %s for profiles. Onboarding gitignores .hitl/people/, so a profile "
            "describing a colleague would be read from a directory that is still tracked."
            % (name, sorted(found)))


def test_both_personal_commands_stay_user_initiated():
    """S18: `disable-model-invocation` could be dropped from both skills, unguarded.

    One writes a persistent block into the team's committed CLAUDE.md; the other composes a message
    under the user's name from a colleague's stored profile. Neither is something to start on its
    own initiative, and both docs say so in prose while nothing checked the frontmatter that
    enforces it.
    """
    for path in (PREFS_SKILL, DRAFT_SKILL):
        fm = re.match(r"---\n(.*?)\n---", io.open(path, encoding="utf-8").read(), re.S)
        assert fm, "%s has no frontmatter" % path
        assert re.search(r"^disable-model-invocation:\s*true\s*$", fm.group(1), re.M), (
            "%s may be invoked by the model on its own initiative" % os.path.basename(
                os.path.dirname(path)))


def test_the_session_instructions_offer_both_commands():
    """S17: draft-for could be dropped from the template entirely and stay green.

    A registered, documented, tested command that nothing ever surfaces is the defect class this
    whole file exists for: a mechanism nobody is offered.
    """
    t = io.open(CLAUDE_TMPL, encoding="utf-8").read()
    for cmd in ("/hitl:dev-preferences", "/hitl:dev-draft-for"):
        assert cmd in t, (
            "the session instructions never mention %s, so nobody is told it exists" % cmd)


def test_every_embedded_script_lives_in_a_section_we_test():
    """M29: a fourth fence can be added and is lifted by nobody.

    The round added a plausible `global` mode after `## The floor` that copied the block into
    ~/.claude/CLAUDE.md with no anchoring, no symlink check and no confirmation -- the one thing
    "Scope: this project" promises never happens. It was never run, never syntax-checked, and never
    seen by any guard, because selection enumerates three sections and ignores the rest.
    """
    text = io.open(PREFS_SKILL, encoding="utf-8").read()
    known = set()
    for heading in PREFS_SECTIONS.values():
        known |= {b for b in re.findall(r"<<'%s'\n(.*?)\n%s\n" % (MARK, MARK),
                                        _section(text, heading), re.S)}
    every = set(re.findall(r"<<'%s'\n(.*?)\n%s\n" % (MARK, MARK), text, re.S))
    every |= set(re.findall(r"```bash\n(.*?)\n```", text, re.S))
    # bash fences that merely wrap a python heredoc are represented by the heredoc body
    stray = {b for b in every - known if MARK not in b}
    assert not stray, (
        "the preferences skill contains %d embedded script(s) that no guard runs:\n%s"
        % (len(stray), "\n---\n".join(sorted(stray))[:900]))


def test_the_persona_template_is_unchanged():
    """M43: the template's comments are the instructions for filling it in. Its header once
    advertised an inbound path the feature does not have; the wording discipline and the
    style-only limit on `notes` live here too."""
    import hashlib
    t = io.open(os.path.join(ROOT, "ai", "shared", "templates", "persona.yaml"),
                encoding="utf-8").read()
    got = hashlib.sha256(" ".join(t.split()).encode("utf-8")).hexdigest()
    assert got == PERSONA_TEMPLATE_SHA, (
        "ai/shared/templates/persona.yaml changed. Read the diff: this file teaches what to write "
        "about a colleague.\n  expected %s\n  got      %s" % (PERSONA_TEMPLATE_SHA, got))


PERSONA_TEMPLATE_SHA = "9fbcc923e566cf0d91a31257450c72ac8642a79280f5a94174cd0bf58eb24d82"


@pytest.mark.parametrize("mode", ["", "toggle", "off on", "--off", "of", "on;rm -rf ."])
def test_flip_refuses_any_mode_it_does_not_recognise(tmp_path, mode):
    """Guessing here once turned preferences ON when the user asked for OFF.

    Case variants are NOT in this list: the script lowercases deliberately, so `OFF` is a user
    typing, not an unrecognised mode. Asserting they are refused would pin a behaviour the design
    does not want.
    """
    d = _proj(tmp_path, INLINE_MENTION)
    assert _run(_prefs_script("write"), d).returncode == 0
    before = (d / "CLAUDE.md").read_text(encoding="utf-8")
    r = _run(_prefs_script("flip"), d, [mode] if mode else [])
    assert r.returncode != 0, "flip acted on an unrecognised mode %r" % mode
    assert (d / "CLAUDE.md").read_text(encoding="utf-8") == before, (
        "flip modified the file for mode %r" % mode)


def test_a_name_containing_an_end_marker_cannot_terminate_the_block(tmp_path):
    """The name is the one value that comes from outside. It must not be able to close the block."""
    d = tmp_path / "p"
    d.mkdir()
    (d / "CLAUDE.md").write_text(INLINE_MENTION, encoding="utf-8")
    subprocess.run(["git", "init", "-q", "."], cwd=str(d), check=True)
    subprocess.run(["git", "config", "user.name", "Ada <!-- HITL:PREFS:END --> Lovelace"],
                   cwd=str(d), check=True)
    assert _run(_prefs_script("write"), d).returncode == 0
    text = (d / "CLAUDE.md").read_text(encoding="utf-8")
    assert len(re.findall(r"^<!-- HITL:PREFS:END -->", text, re.M)) == 1, (
        "the name forged a second END marker")
    assert _run(_prefs_script("flip"), d, ["off"]).returncode == 0, "the block is now inoperable"


def test_adjusting_preferences_does_not_invent_a_pause(tmp_path):
    """The pause-preservation test read the block's own explanatory prose.

    The block body says: "If the marker above reads `status: PAUSED`, ignore this whole block".
    An unanchored search for that string matched THAT sentence, so the first adjust flipped a
    never-paused block to PAUSED and printed that it had "kept" a pause the user never set. The
    skill actively tells people to re-run it to adjust, so this was the ordinary path.
    """
    d = _proj(tmp_path, "# My Project\n\nteam rules here\n")
    assert _run(_prefs_script("write"), d).returncode == 0
    assert "status: ACTIVE" in (d / "CLAUDE.md").read_text(encoding="utf-8")
    r = _run(_prefs_script("write"), d)
    assert r.returncode == 0
    text = (d / "CLAUDE.md").read_text(encoding="utf-8")
    marker = re.search(r"^<!-- HITL:PREFS:BEGIN[^\n]*", text, re.M).group(0)
    assert "status: ACTIVE" in marker, "adjusting turned the user's preferences off: %s" % marker
    assert "PAUSED" not in r.stdout, "claimed to keep a pause that was never set: %r" % r.stdout


def test_the_upgrade_path_gitignores_persona_profiles():
    """Onboarding adds the ignore rule. dev-update did not, and every current user is on that path.

    A team that onboarded before this feature gets the commands and none of the protection, so the
    first profile of a named colleague is an untracked file in a directory teams `git add -A`.
    HITL meanwhile tells the author it is local.
    """
    s = io.open(UPDATE_SKILL, encoding="utf-8").read()
    assert ".hitl/people/" in s, "dev-update never ensures persona profiles are ignored"
    assert 'grep -q "^\\.hitl/people/"' in s, (
        "the upgrade path must use the same idempotent check as onboarding")
    assert "git ls-files" in s, (
        "a profile already committed is not covered by adding an ignore rule; the upgrade must "
        "say so rather than implying it is now safe")


def test_the_save_path_verifies_the_ignore_rather_than_asserting_it():
    """Doctrine stated locality as an accomplished fact, so the model repeats it to the user.

    Nothing checked at write time, and telling someone a file is local when it is about to be
    committed is worse than saying nothing, because then they do not check.
    """
    s = " ".join(io.open(os.path.join(ROOT, "ai", "shared", "personas.md"),
                         encoding="utf-8").read().split())
    assert "git check-ignore" in s, "nothing verifies the profile is actually ignored before writing"
    assert "say so before you write" in s, (
        "there is no instruction to stop and tell the user when it cannot be made local")


FENCED_EXAMPLE = ("# Rules\n\nExample header:\n\n```markdown\n"
                  "<!-- HITL:PREFS:BEGIN status: ACTIVE -->\nmy documentation line\n"
                  "<!-- HITL:PREFS:END -->\n```\n\nnot a real block.\n")


def test_a_fenced_example_of_the_block_is_not_the_block(tmp_path):
    """Anchoring is not enough: inside a fence, a marker still begins its line.

    A team documenting the block format in their own CLAUDE.md had that example treated as the
    real block -- their line replaced, and the block written INSIDE the fence, where no session
    would ever read it as an instruction. Destructive and inert at once.
    """
    d = _proj(tmp_path, FENCED_EXAMPLE)
    assert _run(_prefs_script("write"), d).returncode == 0
    t = (d / "CLAUDE.md").read_text(encoding="utf-8")
    assert "my documentation line" in t, "the team's own text inside the fence was overwritten"
    assert t.index("set by") > t.rindex("```"), "the block was written inside the code fence"
    assert _run(_prefs_script("flip"), d, ["off"]).returncode == 0, "the real block is not operable"
    assert _run(_prefs_script("reset"), d).returncode == 0
    back = (d / "CLAUDE.md").read_text(encoding="utf-8")
    assert back.count("```") == 2 and "my documentation line" in back, "reset damaged the fence"


@pytest.mark.parametrize("kind", ["write", "flip", "reset"])
def test_crlf_files_stay_crlf(tmp_path, kind):
    """Writing LF back into a CRLF file rewrites every line, so `off` produced a 300-line diff."""
    d = tmp_path / "p"
    d.mkdir()
    (d / "CLAUDE.md").write_bytes(b"# R\r\n\r\nrules\r\n")
    subprocess.run(["git", "init", "-q", "."], cwd=str(d), check=True)
    subprocess.run(["git", "config", "user.name", "Ada Lovelace"], cwd=str(d), check=True)
    assert _run(_prefs_script("write"), d).returncode == 0
    if kind != "write":
        assert _run(_prefs_script(kind), d, ["off"] if kind == "flip" else []).returncode == 0
    raw = (d / "CLAUDE.md").read_bytes()
    assert raw.replace(b"\r\n", b"").count(b"\n") == 0, (
        "%s left bare LF line endings in a CRLF file" % kind)


@pytest.mark.parametrize("kind", ["write", "flip", "reset"])
def test_an_unwritable_file_is_reported_not_traced(tmp_path, kind):
    """A raw Python traceback tells the user nothing about what did or did not happen."""
    d = _proj(tmp_path, "# Rules\n\nteam rules\n")
    assert _run(_prefs_script("write"), d).returncode == 0
    before = (d / "CLAUDE.md").read_bytes()
    os.chmod(str(d / "CLAUDE.md"), 0o444)
    try:
        r = _run(_prefs_script(kind), d, ["off"] if kind == "flip" else [])
    finally:
        os.chmod(str(d / "CLAUDE.md"), 0o644)
    assert r.returncode != 0
    assert "Traceback" not in r.stderr, "%s dumped a traceback at the user: %s" % (kind, r.stderr[-300:])
    assert "Nothing changed" in (r.stdout + r.stderr), "%s did not say the file was untouched" % kind
    assert (d / "CLAUDE.md").read_bytes() == before


def test_a_percent_in_an_answer_does_not_crash_the_write(tmp_path):
    """Round 9 removed a `\"\"\"` hazard by switching to %-formatting, which added a % hazard on the
    same line. "cut preamble by 90%" gave the user a traceback and no saved preferences after they
    had just answered a four-question interview."""
    d = _proj(tmp_path, "# Rules\n\nteam rules\n")
    hostile = r"short - by 90% and paths like C:\notes"
    r = _run(_prefs_script("write"), d,
             ["write", hostile, "only when asked", "the decision", "say it straight"])
    assert r.returncode == 0, "a hostile answer crashed the write: %s" % r.stderr[-300:]
    saved = (d / "CLAUDE.md").read_text(encoding="utf-8")
    assert hostile in saved, (
        "the answer was mangled on the way in. A %% used to crash the write and a backslash used "
        "to be read as a Python escape, saving C:\\notes as a newline followed by 'otes'.\n%s"
        % saved[:400])


@pytest.mark.parametrize("kind", ["write", "flip", "reset"])
def test_the_block_belongs_to_the_repo_not_the_current_directory(tmp_path, kind):
    """A session started in a monorepo package wrote a second CLAUDE.md there containing only the
    block. From the root, show/off/reset then all reported nothing was set while it was live."""
    d = _proj(tmp_path, "# Monorepo\n\nTeam rules.\n")
    sub = d / "packages" / "api"
    sub.mkdir(parents=True)
    assert _run(_prefs_script("write"), sub).returncode == 0
    assert not (sub / "CLAUDE.md").exists(), "wrote a stray CLAUDE.md in the subdirectory"
    assert "<!-- HITL:PREFS:BEGIN" in (d / "CLAUDE.md").read_text(encoding="utf-8")
    r = _run(_prefs_script(kind), sub, ["off"] if kind == "flip" else [])
    assert r.returncode == 0, "%s run from a subdirectory could not see the block: %s" % (kind, r.stdout)


def _ignore_script():
    s = io.open(os.path.join(ROOT, "ai", "shared", "personas.md"), encoding="utf-8").read()
    # Selected by what it DOES (the check-ignore verify), not by its first line -- which is how
    # this helper broke the moment the block gained a `cd` to the repo root.
    m = re.search(r"```bash\n((?:(?!```).)*?check-ignore(?:(?!```).)*?)\n```", s, re.S)
    assert m, "the locality pre-check is gone from personas.md"
    return m.group(1)


@pytest.mark.parametrize("case,setup,expect", [
    ("clean repo", "git init -q .", "OK"),
    ("no repo", "true", "NOT A GIT REPO"),
    ("already tracked",
     "git init -q . && git config user.email a@b.c && git config user.name A && "
     "mkdir -p .hitl/people && echo 'name: x' > .hitl/people/k.yaml && "
     "git add -A >/dev/null && git commit -qm x",
     "ALREADY TRACKED"),
])
def test_the_locality_check_verifies_instead_of_announcing(tmp_path, case, setup, expect):
    """It appended a rule and declared success. .gitignore does not untrack a tracked file, and
    outside a repo check-ignore fails in a way that looks like "not ignored" -- so it printed the
    false assurance that the paragraph beneath it warns against."""
    d = tmp_path / "p"
    d.mkdir()
    subprocess.run(["bash", "-c", setup], cwd=str(d), check=True, capture_output=True)
    r = subprocess.run(["bash", "-c", _ignore_script()], cwd=str(d), capture_output=True, text=True)
    assert expect in r.stdout, "%s: expected %r, got %r" % (case, expect, r.stdout)
    if expect != "OK":
        assert "OK —" not in r.stdout, "%s: claimed the profile would be local" % case


def test_the_description_does_not_advertise_a_mode_that_does_not_exist():
    """The picker text promised a one-session off. No mode does that; `off` persists, and being in
    a committed file it applies to teammates until someone runs `on`."""
    fm = re.match(r"---\n(.*?)\n---", io.open(PREFS_SKILL, encoding="utf-8").read(), re.S).group(1)
    assert "for one session" not in fm, (
        "the description steers people to `off` for a one-session pause, which persists")


def test_a_teammate_is_told_whose_preferences_are_in_force(tmp_path):
    """The mitigation only fired if the teammate opened CLAUDE.md.

    The skill names the problem itself: people "who never ran the command and cannot tell whose
    settings are in force". What they actually experience is HITL going terse with no attribution
    in the session, and the closing paragraph of the block never reaches them. The instruction now
    lives in the block, which is what a session reads.
    """
    d = _proj(tmp_path, "# Rules\n\nteam rules\n")
    assert _run(_prefs_script("write"), d).returncode == 0
    block = re.search(r"^<!-- HITL:PREFS:BEGIN.*?^<!-- HITL:PREFS:END -->",
                      (d / "CLAUDE.md").read_text(encoding="utf-8"), re.S | re.M).group(0)
    assert "is not Ada Lovelace" in block, (
        "the block does not tell a session to name whose settings it is applying")
    assert "default mode" in block


@pytest.mark.parametrize("kind,expect", [("flip", "whole team"), ("reset", "gone for everyone")])
def test_pausing_or_deleting_says_whose_settings_they_were(tmp_path, kind, expect):
    """The write path discloses team scope; off/on/reset did not, and they edit the same committed
    file. A teammate following the block's own advice to run `off` silently paused a named
    colleague's settings for the whole repo."""
    d = _proj(tmp_path, "# Rules\n\nteam rules\n")
    subprocess.run(["git", "config", "user.name", "Priya Nair"], cwd=str(d), check=True)
    assert _run(_prefs_script("write"), d).returncode == 0
    subprocess.run(["git", "config", "user.name", "Sam Ortiz"], cwd=str(d), check=True)
    r = _run(_prefs_script(kind), d, ["off"] if kind == "flip" else [])
    assert r.returncode == 0
    assert "Priya Nair" in r.stdout, "%s did not say whose settings it changed: %r" % (kind, r.stdout)
    assert expect in r.stdout, "%s did not state the blast radius: %r" % (kind, r.stdout)


def test_whether_the_subject_was_told_is_recorded_and_surfaced():
    """"Tell them it exists" is the doctrine's central obligation and it lived exactly one turn.

    HITL suggested it, the sender said sure, and from the next session nobody -- human or model --
    could tell whether it happened. The profile is the only thing that outlives the conversation,
    so it has to carry the answer.
    """
    tmpl = io.open(os.path.join(ROOT, "ai", "shared", "templates", "persona.yaml"),
                   encoding="utf-8").read()
    import yaml as _y
    fields = _y.safe_load(tmpl)
    for f in ("subject_told", "written"):
        assert f in fields, "the profile records no %r" % f
    draft = io.open(DRAFT_SKILL, encoding="utf-8").read()
    rows = [ln for ln in draft.splitlines() if ln.startswith("|")]
    for f in ("subject_told", "written"):
        assert any(("`%s" % f) in ln for ln in rows), "%r has no reader in draft-for" % f
    flat = " ".join(draft.split())
    assert "Say it every time, not once." in flat, (
        "a one-time mention is what the recording exists to replace")
    assert "Do not refuse to draft" in flat, (
        "an unrecorded answer must not become a blocker; honest defaults have to stay usable")


def test_show_finds_the_block_from_a_subdirectory(tmp_path):
    """`show` is bash and was left out of BOTH the repo-root fix and the fence fix.

    From a subdirectory it reported "No HITL preferences set in this project" while `off` in that
    same directory happily paused the real block. The two commands disagreed about whether the
    feature was even on.
    """
    d = _proj(tmp_path, "# Rules\n\nteam rules\n")
    sub = d / "sub" / "deep"
    sub.mkdir(parents=True)
    assert _run(_prefs_script("write"), d).returncode == 0
    out = _run(_prefs_script("show"), sub).stdout
    assert "HITL:PREFS:BEGIN" in out, "show from a subdirectory could not see the block: %r" % out
    assert "No HITL preferences set" not in out


@pytest.mark.parametrize("kind", ["write", "flip", "reset"])
def test_an_unterminated_fence_is_refused_not_guessed(tmp_path, kind):
    """Fence masking toggled on any ``` line, so an ODD count inverted the whole file: the real
    block looked masked, a SECOND block was written, and off/reset then denied any block existed."""
    d = _proj(tmp_path, "# R\n\n```markdown\n<!-- HITL:PREFS:BEGIN status: ACTIVE -->\nx\n"
                        "<!-- HITL:PREFS:END -->\n")
    before = (d / "CLAUDE.md").read_text(encoding="utf-8")
    r = _run(_prefs_script(kind), d, ["off"] if kind == "flip" else [])
    assert r.returncode != 0, "%s acted on a file with an unterminated fence" % kind
    assert "unterminated" in (r.stdout + r.stderr)
    assert (d / "CLAUDE.md").read_text(encoding="utf-8") == before


def test_tilde_fences_are_masked_too(tmp_path):
    """The ``` fix was not applied to the other fence character markdown allows."""
    d = _proj(tmp_path, "# R\n\n~~~markdown\n<!-- HITL:PREFS:BEGIN status: ACTIVE -->\nexample\n"
                        "<!-- HITL:PREFS:END -->\n~~~\n\nreal text\n")
    assert _run(_prefs_script("write"), d).returncode == 0
    t = (d / "CLAUDE.md").read_text(encoding="utf-8")
    assert "\nexample\n" in t, "the team's ~~~ fenced example was overwritten"
    assert t.index("set by") > t.rindex("~~~"), "the block was written inside the ~~~ fence"


def test_an_orphan_end_marker_is_refused(tmp_path):
    """The writer appended beside a lone END, then off/reset saw 1/2 markers and refused forever."""
    d = _proj(tmp_path, "# R\n\nteam rules\n\n<!-- HITL:PREFS:END -->\n")
    before = (d / "CLAUDE.md").read_text(encoding="utf-8")
    r = _run(_prefs_script("write"), d)
    assert r.returncode != 0, "wrote a block beside an orphan END, wedging the file"
    assert (d / "CLAUDE.md").read_text(encoding="utf-8") == before


@pytest.mark.parametrize("kind", ["write", "flip", "reset"])
def test_a_non_utf8_file_is_reported_not_traced(tmp_path, kind):
    """The traceback fix wrapped the write and left the read bare."""
    d = tmp_path / "p"
    d.mkdir()
    (d / "CLAUDE.md").write_bytes(b"\xff\xfe not utf8\n")
    subprocess.run(["git", "init", "-q", "."], cwd=str(d), check=True)
    subprocess.run(["git", "config", "user.name", "Ada"], cwd=str(d), check=True)
    r = _run(_prefs_script(kind), d, ["off"] if kind == "flip" else [])
    assert r.returncode != 0
    assert "Traceback" not in r.stderr, "%s dumped a traceback: %s" % (kind, r.stderr[-200:])
    assert "Nothing changed" in (r.stdout + r.stderr)


def test_profiles_are_read_and_written_at_the_repo_root():
    """Same subdirectory defect as the block, in the two places that fix did not reach.

    A profile saved from a subdirectory landed in <subdir>/.hitl/people/, invisible to draft-for at
    the root, which would then offer to create a second one for the same person.
    """
    for name, path in (("personas.md", os.path.join(ROOT, "ai", "shared", "personas.md")),
                       ("draft-for", DRAFT_SKILL)):
        s = io.open(path, encoding="utf-8").read()
        assert "--show-toplevel" in s, (
            "%s resolves .hitl/people/ from the current directory, not the repo" % name)


HITL_BLOCK = os.path.join(ROOT, "ai", "shared", "templates", "claude-md-hitl-block.md")
ONBOARD_SKILLS = ["start-from-prd", "start-brownfield", "start-migration"]


def test_the_installed_block_carries_the_feature_instructions():
    """The only place that told a session these commands exist was CLAUDE.md.template.

    An upgraded project never receives that template. What it receives is the marker block, which
    both init-project.sh and dev-update Step 4.8 install -- and that block said nothing about
    preferences, "default mode", or draft-for. So the feature reached the project and nothing in
    the project ever mentioned it: the whole defect class this repo keeps catching.
    """
    s = io.open(HITL_BLOCK, encoding="utf-8").read()
    for cmd in ("/hitl:dev-preferences", "/hitl:dev-draft-for"):
        assert cmd in s, "the installed block never mentions %s" % cmd
    assert "status: PAUSED" in s, "the block does not tell a session to honour a pause"
    assert "default mode" in s, "the one-session escape is not instructed where sessions read it"
    assert "never omitted" in s, "the floor is absent from the block every project actually gets"


@pytest.mark.parametrize("skill", ONBOARD_SKILLS)
def test_plugin_native_onboarding_ignores_persona_profiles(skill):
    """init-project.sh adds the rule, and a plugin-installed team never runs init-project.sh.

    These three are the documented onboarding commands. Without the rule, the first profile a team
    saves is committed while personas.md tells the author it is local.
    """
    s = io.open(os.path.join(ROOT, "ai", "claude", skill, "SKILL.md"), encoding="utf-8").read()
    assert ".hitl/people/" in s, "%s onboards a project without excluding persona profiles" % skill
    assert "git check-ignore" in s, "%s asserts the exclusion instead of verifying it" % skill


def test_the_hook_rewire_branch_returns_for_the_remaining_steps():
    """Step 4 sends the model into another command's Step 0, which ends "restart and re-run this
    command". Followed literally on an old repo -- the exact audience -- Steps 4.5 through 4.9 and
    the completion message never run, and nothing tells the user anything was skipped."""
    s = " ".join(io.open(UPDATE_SKILL, encoding="utf-8").read().split())
    assert "sub-steps 1-3 only" in s, "the jump does not bound what to run"
    assert "come straight back here to Step 4.5" in s, "the jump never returns"
    assert "Ignore its closing" in s, "the restart instruction is not neutralised"


def test_the_upgrade_gitignore_step_verifies_its_own_outcome():
    """It printed the tick unconditionally. Same false assurance personas.md was fixed for."""
    s = io.open(UPDATE_SKILL, encoding="utf-8").read()
    i = s.index("## Step 4.9")
    body = s[i:s.index("## Step 5", i)]
    assert "git check-ignore -q" in body, "Step 4.9 asserts the exclusion instead of verifying it"
    assert "COULD NOT exclude" in body, "there is no honest branch when the rule does not take"


def test_no_update_step_inherits_a_plugin_root_from_an_earlier_step():
    """Shell state does not persist between tool calls, so `${CLAUDE_PLUGIN_ROOT:-$ROOT}` in a
    later step resolved to empty.

    Step 4.8 then reported "No HITL block template in this plugin build — skipping", which is false
    and benign-sounding, while Step 5 announced a successful update. The block carries the only
    instructions telling a session these commands exist, so the headline fix reached nobody. The
    step's own comment warns against exactly this ("dress a path defect up as a legitimate
    absence") and the code did it anyway.
    """
    s = io.open(UPDATE_SKILL, encoding="utf-8").read()
    assert "${CLAUDE_PLUGIN_ROOT:-$ROOT}" not in s, (
        "a step inherits $ROOT from an earlier Bash call, which is always empty")
    for step in ("## Step 4.7", "## Step 4.8"):
        i = s.index(step)
        body = s[i:i + 2000]
        assert "installed_plugins.json" in body, (
            "%s does not resolve the plugin root itself" % step)


def test_the_installed_block_and_the_template_agree():
    """Both must tell a session the commands exist: onboarding installs one, upgrades the other."""
    block = io.open(HITL_BLOCK, encoding="utf-8").read()
    tmpl = io.open(CLAUDE_TMPL, encoding="utf-8").read()
    for cmd in ("/hitl:dev-preferences", "/hitl:dev-draft-for"):
        assert cmd in block and cmd in tmpl, "%s is missing from one of the two" % cmd
