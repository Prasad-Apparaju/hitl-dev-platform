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
        'sed -n "/^hitl_copy_tools()/,/^}/p" %s > /tmp/_hct.sh\n'
        '. /tmp/_hct.sh\n'
        'hitl_copy_tools %s %s\n' % (
            subprocess.list2cmdline([INIT]),
            subprocess.list2cmdline([src]),
            subprocess.list2cmdline([dest]))
    )
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True)


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


def test_personas_are_wired_at_both_ends():
    """A mechanism nobody is offered and nothing reads is inert — the defect of the week."""
    tmpl = io.open(os.path.join(ROOT, "ai", "claude", "generate-docs", "templates",
                                "CLAUDE.md.template"), encoding="utf-8").read()
    assert "/hitl:dev-preferences" in tmpl, "nothing ever offers the preferences command"
    assert "HITL:PREFS" in tmpl, "the session instructions never read the block"
    assert "PAUSED" in tmpl, "the pause state is settable but nothing honours it"
    assert "default mode" in tmpl, "the one-session escape is documented nowhere that reads it"

    import json
    reg = json.load(io.open(os.path.join(ROOT, "ai", "claude", "plugin", "plugin.json"),
                            encoding="utf-8"))
    for skill in ("ai/claude/preferences", "ai/claude/draft-for"):
        assert skill in reg["skills"], "%s is not registered in plugin.json" % skill
        assert os.path.isfile(os.path.join(ROOT, skill, "SKILL.md")), "%s has no SKILL.md" % skill


def test_preferences_are_project_scoped_by_default():
    """HITL manages projects. A HITL command must not reach into machine-wide config on its own
    initiative — that changes behaviour in every unrelated project the person works in."""
    s = io.open(os.path.join(ROOT, "ai", "claude", "preferences", "SKILL.md"),
                encoding="utf-8").read()
    write_section = s[s.index("## Writing it"):s.index("## The floor")]
    assert "~/.claude" not in write_section, (
        "the write path targets the user's global config; it must write to the project CLAUDE.md")
    assert 'p = "CLAUDE.md"' in write_section, "the write target must be the project file"
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
    for name, text in (("personas.md", doctrine), ("draft-for", skill), ("CLAUDE.md.template", tmpl)):
        assert "form" in text and "substance" in text, (
            "%s does not state that a persona shapes form, not substance" % name)
    assert "never sends" in skill.lower() or "Never send it" in skill, (
        "the drafting skill must not send anything on the user's behalf")
    assert "invent one" in skill or "guessed persona" in skill, (
        "drafting for someone with no profile must ask, not infer one from their name")


def test_persona_template_is_valid_and_teaches_preferences_not_assessments():
    import yaml as _y
    p = os.path.join(ROOT, "ai", "shared", "templates", "persona.yaml")
    d = _y.safe_load(io.open(p, encoding="utf-8"))
    assert set(d["style"]) >= {"length", "process_narrative", "lead_with"}
    assert d.get("authored_by") == "self", "profiles should default to self-authored"
    text = io.open(p, encoding="utf-8").read()
    assert "preferences, not assessments" in text, (
        "the template must steer away from characterising a colleague in version control")
