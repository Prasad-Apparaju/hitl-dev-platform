"""The release gate must fail closed, and its freshness rule must actually bite.

Written mutation-first: every rule is asserted by breaking it, because a gate that only ever sees
well-formed input is a gate nobody has tested. The freshness case is the important one — it is the
only property here that cannot be satisfied by writing a flattering record.
"""
import io
import os
import subprocess
import sys

import pytest
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_review import check  # noqa: E402

SCRIPT = os.path.join(HERE, "check_review.py")
SHA = "a" * 40


def _write(p, doc):
    os.makedirs(os.path.dirname(str(p)), exist_ok=True)
    io.open(str(p), "w", encoding="utf-8").write(yaml.safe_dump(doc, sort_keys=False))


def _setup(tmp_path, record=None, change=None):
    """Returns (change_path, reviews_dir). Pass root=str(tmp_path) so the gate never
    inspects the developer's real repository."""
    root = tmp_path
    _write(root / ".hitl" / "current-change.yaml",
           change if change is not None else {"change_id": "GH-80", "tier": 2})
    if record is not None:
        _write(root / ".hitl" / "reviews" / "GH-80-round1.yaml", record)
    return (str(root / ".hitl" / "current-change.yaml"), str(root / ".hitl" / "reviews"))


def _record(**over):
    rec = {
        "schema_version": "1.0",
        "change_id": "GH-80",
        "round": 1,
        "reviewed_sha": SHA,
        "scope": "diff v1.0.0..HEAD",
        "reviewer": {"model": "fable", "context": "clean", "spawned_by": "hitl:adversarial-review"},
        "stance": "refute",
        # `verified_by` is the reproduction re-run and its output. Nothing enforces it — the check
        # that would have was cut from 2.8.0 (#92) — but a record that fills it in is the shape the
        # next round can actually read.
        "findings": [{"id": "F1", "severity": "HIGH", "claim": "x", "reproduction": "y",
                      "status": "fixed", "verified_by": "re-ran y: exit 0, no output"}],
        "verdict": "ship",
    }
    rec.update(over)
    return rec


def _codes(blocks):
    return {b.split(":")[0].replace("[BLOCK] ", "").strip() for b in blocks}


def test_a_clean_fresh_review_passes(tmp_path):
    c, r = _setup(tmp_path, _record())
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert blocks == [], blocks


def test_no_review_at_all_blocks(tmp_path):
    c, r = _setup(tmp_path, None)
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "REVIEW_MISSING" in _codes(blocks)


def test_review_of_different_code_blocks(tmp_path):
    """THE rule. Review an early draft, keep editing, and the gate must still stop you."""
    c, r = _setup(tmp_path, _record(reviewed_sha="b" * 40))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "REVIEW_STALE" in _codes(blocks), blocks


def test_open_critical_finding_blocks(tmp_path):
    c, r = _setup(tmp_path, _record(findings=[
        {"id": "F1", "severity": "CRITICAL", "claim": "deletes user data", "status": "open"}]))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "FINDING_OPEN" in _codes(blocks)


def test_open_low_finding_does_not_block(tmp_path):
    c, r = _setup(tmp_path, _record(findings=[
        {"id": "F1", "severity": "LOW", "claim": "typo", "status": "open"}]))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert blocks == []


def test_accepted_finding_needs_an_owner(tmp_path):
    c, r = _setup(tmp_path, _record(findings=[
        {"id": "F1", "severity": "CRITICAL", "claim": "x", "status": "accepted"}]))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "UNSIGNED_ACCEPTANCE" in _codes(blocks)
    c, r = _setup(tmp_path, _record(findings=[
        {"id": "F1", "severity": "CRITICAL", "claim": "x", "status": "accepted",
         "accepted_by": "someone"}]))
    assert check(c, r, sha=SHA, root=str(tmp_path))[0] == []


def test_verdict_must_be_ship(tmp_path):
    c, r = _setup(tmp_path, _record(verdict="do-not-ship"))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "VERDICT_NOT_SHIP" in _codes(blocks)


def test_reviewer_sharing_the_authors_context_blocks(tmp_path):
    c, r = _setup(tmp_path, _record(
        reviewer={"model": "fable", "context": "inherited"}))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "NOT_INDEPENDENT" in _codes(blocks)


def test_confirming_stance_blocks(tmp_path):
    c, r = _setup(tmp_path, _record(stance="confirm"))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "WRONG_STANCE" in _codes(blocks)


@pytest.mark.parametrize("bad", [
    {"findings": "not-a-list"},
    {"findings": [{"severity": "SEVERE", "claim": "x", "status": "open"}]},
    {"findings": [{"severity": "HIGH", "claim": "x", "status": "maybe"}]},
    {"reviewer": "not-a-mapping"},
    {"reviewed_sha": ""},
])
def test_malformed_records_block_rather_than_pass(tmp_path, bad):
    c, r = _setup(tmp_path, _record(**bad))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert blocks, "malformed record %r passed the gate" % bad


def test_unparseable_record_blocks(tmp_path):
    c, r = _setup(tmp_path, _record())
    io.open(os.path.join(r, "GH-80-round1.yaml"), "w", encoding="utf-8").write("{[not yaml")
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "MALFORMED" in _codes(blocks)


def test_a_review_of_a_different_change_does_not_count(tmp_path):
    c, r = _setup(tmp_path, _record(change_id="GH-79"))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "REVIEW_MISSING" in _codes(blocks)


def test_latest_round_decides(tmp_path):
    """Round 1 found a CRITICAL; round 2 is clean. The later round governs."""
    c, r = _setup(tmp_path, _record(findings=[
        {"id": "F1", "severity": "CRITICAL", "claim": "x", "status": "open"}]))
    _write(os.path.join(r, "GH-80-round2.yaml"),
           _record(round=2, findings=[{"id": "F1", "severity": "CRITICAL", "claim": "x",
                                       "status": "fixed"}]))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert blocks == [], blocks


def test_round_one_with_no_findings_warns_but_does_not_block(tmp_path):
    c, r = _setup(tmp_path, _record(findings=[]))
    blocks, warns = check(c, r, sha=SHA, root=str(tmp_path))
    assert blocks == []
    assert any("SHALLOW_REVIEW" in w for w in warns)


def test_cli_exit_codes(tmp_path):
    c, r = _setup(tmp_path, _record())
    ok = subprocess.run([sys.executable, SCRIPT, "--change", c, "--reviews", r, "--sha", SHA,
                         "--root", str(tmp_path)],
                        capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr

    c2, r2 = _setup(tmp_path / "b", _record(reviewed_sha="c" * 40))
    bad = subprocess.run([sys.executable, SCRIPT, "--change", c2, "--reviews", r2, "--sha", SHA,
                          "--root", str(tmp_path)],
                         capture_output=True, text=True)
    assert bad.returncode == 2
    assert "REVIEW_STALE" in bad.stdout


def test_gate_defaults_to_head_when_no_sha_given(tmp_path):
    """In a real repo the gate must compare against HEAD without being told."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(repo), check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "config", k, v], cwd=str(repo), check=True)
    (repo / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(repo), check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=str(repo), check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                          capture_output=True, text=True).stdout.strip()

    c, r = _setup(repo, _record(reviewed_sha=head))
    assert check(c, r, root=str(repo))[0] == []

    c, r = _setup(repo, _record(reviewed_sha="d" * 40))
    assert "REVIEW_STALE" in _codes(check(c, r, root=str(repo))[0])


def test_offer_steps_exist_at_the_phase_boundaries():
    """The offers must be real steps, or declining them cannot be recorded or resurfaced."""
    import yaml as _y
    rt = _y.safe_load(io.open(
        os.path.join(HERE, "..", "..", "ai", "shared", "workflows.yaml"), encoding="utf-8"))
    dev = rt["workflows"]["development"]["steps"]
    by_key = {s["key"]: s for s in dev}
    for key, phase in (("adv_design", "Design"), ("adv_code", "Build")):
        assert key in by_key, "%s is not in the development workflow" % key
        s = by_key[key]
        assert s["phase"] == phase
        # ceremony = freely declined. Anything heavier turns an offer into an obstacle.
        assert s.get("crit") == "ceremony", "%s must be freely declinable, got %r" % (key, s.get("crit"))
        assert not s.get("no_omit"), "%s must not be mandatory" % key

    # Each offer sits at the END of its phase — the point where the work is actually finished.
    for key, phase in (("adv_design", "Design"), ("adv_code", "Build")):
        in_phase = [s["key"] for s in dev if s["phase"] == phase]
        assert in_phase[-1] == key, "%s should be last in %s, order is %s" % (key, phase, in_phase)


def test_release_review_is_floor_with_a_real_escape_path():
    """Floor, not no_omit.

    no_omit admits NO path at all, while the prose promised one "through the explicit
    acknowledgement path". Shipping both is shipping two truths, and the one people meet at 2am is
    the one that says no — at which point the gate gets deleted from the process. Floor keeps it
    mandatory-by-default and survivable.
    """
    import yaml as _y
    rt = _y.safe_load(io.open(
        os.path.join(HERE, "..", "..", "ai", "shared", "workflows.yaml"), encoding="utf-8"))
    rel = {s["key"]: s for s in rt["workflows"]["release"]["steps"]}
    assert rel["adversarial_review"]["crit"] == "floor"
    assert not rel["adversarial_review"].get("no_omit"), (
        "no_omit leaves no escape, contradicting the documented acknowledgement path")


def test_the_driver_skill_exists_and_ships_what_it_references():
    """A gate with no driver does not run — the failure mode behind first_pass and CLAUDE.md.

    Also guards the 2.4.7 defect class: a skill that references a shared file which the build does
    not package resolves in the source repo and points at nothing for every user.
    """
    root = os.path.join(HERE, "..", "..")
    skill = os.path.join(root, "ai", "claude", "verification-review", "SKILL.md")
    assert os.path.isfile(skill), "the verification-review skill is missing"
    body = io.open(skill, encoding="utf-8").read()

    # It must actually spawn independent reviewers, not just describe the idea.
    assert "clean-context" in body or "clean context" in body
    assert "checklist" in body.lower(), "a verification review is a checklist run, or it is an opinion"
    assert "refute" not in body.lower(), "the attack instruction is back (#101)"
    assert "reproduc" in body.lower(), "the reproduction rule is what keeps this from being theatre"
    assert "reviewed_sha" in body, "the driver must write the field the gate binds to"

    # The anti-bias rule is the difference between a review and an echo.
    assert "conclusions" in body.lower()

    # Registered, or the plugin never exposes it.
    import json
    reg = json.load(io.open(os.path.join(root, "ai", "claude", "plugin", "plugin.json"),
                            encoding="utf-8"))
    assert "ai/claude/verification-review" in reg["skills"], "skill not registered in plugin.json"

    # Every shared/ file it points at must exist in the source tree that the build packages.
    import re
    for ref in sorted(set(re.findall(r"`(shared/[a-z0-9/._-]+)`", body))):
        tail = ref[len("shared/"):]
        candidates = [os.path.join(root, "ai", "shared", tail),
                      os.path.join(root, "ai", "claude", "generate-docs", "templates",
                                   os.path.basename(tail))]
        assert any(os.path.exists(c) for c in candidates), (
            "%s is referenced by the skill but no source file maps to it" % ref)



def test_acknowledged_skip_lets_a_release_through_but_says_so_loudly(tmp_path):
    c, r = _setup(tmp_path, None, change={
        "change_id": "GH-80", "tier": 2,
        "skips": [{"step": "adversarial_review", "disposition": "decline",
                   "reason": "sev-1 hotfix", "ack_by": "lead"}]})
    blocks, warns = check(c, r, sha=SHA, root=str(tmp_path))
    assert blocks == [], blocks
    assert any("REVIEW_WAIVED" in w for w in warns)
    assert any("lead" in w and "sev-1 hotfix" in w for w in warns), warns


def test_an_unattributed_acknowledgement_is_not_one(tmp_path):
    c, r = _setup(tmp_path, None, change={
        "change_id": "GH-80", "tier": 2,
        "skips": [{"step": "adversarial_review", "disposition": "decline", "reason": "busy"}]})
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "REVIEW_MISSING" in _codes(blocks), "a skip with nobody's name on it must not clear the gate"


def test_committing_the_record_does_not_stale_it(tmp_path):
    """The gate must be passable by its own documented procedure.

    Comparing raw shas made it impossible: the skill says commit the record, and committing it
    moved HEAD. The only ways through were --sha or editing reviewed_sha — the exact faked record
    the gate exists to prevent, taught on the first release.
    """
    repo = tmp_path / "repo"
    (repo / ".hitl" / "reviews").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(repo), check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "config", k, v], cwd=str(repo), check=True)
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")
    _write(repo / ".hitl" / "current-change.yaml", {"change_id": "GH-80", "tier": 2})
    subprocess.run(["git", "add", "-A"], cwd=str(repo), check=True)
    subprocess.run(["git", "commit", "-qm", "code"], cwd=str(repo), check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                          capture_output=True, text=True).stdout.strip()

    _write(repo / ".hitl" / "reviews" / "GH-80-round1.yaml", _record(reviewed_sha=head))
    c = str(repo / ".hitl" / "current-change.yaml")
    r = str(repo / ".hitl" / "reviews")
    assert check(c, r, root=str(repo))[0] == [], "should pass before the record is committed"

    subprocess.run(["git", "add", "-A"], cwd=str(repo), check=True)
    subprocess.run(["git", "commit", "-qm", "record the review"], cwd=str(repo), check=True)
    assert check(c, r, root=str(repo))[0] == [], "committing the record must not invalidate it"

    # ...but touching real code must.
    (repo / "code.py").write_text("x = 2\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-qam", "change code"], cwd=str(repo), check=True)
    blocks = check(c, r, root=str(repo))[0]
    assert "REVIEW_STALE" in _codes(blocks), "freshness must still bite on a code change"
    assert any("code.py" in b for b in blocks), "the block should name what changed"


def test_debris_from_another_change_does_not_block_forever(tmp_path):
    """Records are kept forever, so one corrupt old file must not block every future release."""
    c, r = _setup(tmp_path, _record())
    io.open(os.path.join(r, "GH-11-round1.yaml"), "w", encoding="utf-8").write("{[not yaml")
    blocks, warns = check(c, r, sha=SHA, root=str(tmp_path))
    assert blocks == [], blocks
    assert any("UNREADABLE_RECORD" in w for w in warns)


def test_our_own_corrupt_record_still_blocks(tmp_path):
    c, r = _setup(tmp_path, _record())
    io.open(os.path.join(r, "GH-80-round2.yaml"), "w", encoding="utf-8").write("{[not yaml")
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "MALFORMED" in _codes(blocks)


def test_built_plugin_resolves_the_skill_references(tmp_path):
    """The defect this guards is invisible in source: paths resolve here and nowhere for a user.

    Skipped when the plugin repo is not checked out beside this one.
    """
    plugin = os.path.abspath(os.path.join(HERE, "..", "..", "..", "hitl-claude-plugin"))
    skill = os.path.join(plugin, "skills", "dev-verification-review", "SKILL.md")
    if not os.path.isfile(skill):
        pytest.skip("plugin repo not present")
    body = io.open(skill, encoding="utf-8").read()
    import re
    bare = re.findall(r"(?<![}/\w])shared/[a-z0-9/._-]+", body)
    assert not bare, (
        "the built skill carries bare shared/ paths, which resolve against the user's project "
        "rather than the plugin: %s" % sorted(set(bare)))
    for ref in sorted(set(re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/(shared/[a-z0-9/._-]+)", body))):
        assert os.path.exists(os.path.join(plugin, ref)), (
            "%s is referenced by the built skill but is not packaged" % ref)


def test_a_review_step_marked_done_with_no_record_is_caught(tmp_path):
    """"Done" with nothing written down is the silent skip this whole feature exists to kill —
    and the branch that built it had exactly that in its own change file."""
    c, r = _setup(tmp_path, None, change={
        "change_id": "GH-80", "tier": 2,
        "workflow": {"id": "development", "steps": [
            {"n": "9a", "key": "adv_design", "status": "done"}]}})
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "UNBACKED_REVIEW" in _codes(blocks), blocks


def test_a_branch_name_as_reviewed_sha_is_refused(tmp_path):
    """A ref that moves with the branch is permanently fresh — the opposite of the guarantee."""
    for bad in ("myfeature", "--cached", "HEAD~1"):
        c, r = _setup(tmp_path, _record(reviewed_sha=bad))
        blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
        assert "REVIEW_STALE" in _codes(blocks), "%r accepted as a commit id" % bad


def test_a_waiver_surfaces_an_existing_adverse_verdict(tmp_path):
    """Waiving is allowed. Hiding a do-not-ship verdict behind the waiver is not."""
    c, r = _setup(tmp_path, _record(verdict="do-not-ship"), change={
        "change_id": "GH-80", "tier": 2,
        "skips": [{"step": "adversarial_review", "reason": "hurry", "ack_by": "someone"}]})
    blocks, warns = check(c, r, sha=SHA, root=str(tmp_path))
    assert blocks == []
    joined = " ".join(warns)
    assert "do-not-ship" in joined, "the waiver hid an adverse verdict: %s" % warns


def test_two_lenses_in_one_round_is_the_practice_not_a_duplicate(tmp_path):
    """The skill mandates two reviewers per round. Recording both must be possible.

    DUPLICATE_ROUND was right about the danger — a second record silently overriding a verdict —
    and wrong to conflate it with the two-lens practice it also mandates. I found this by trying to
    file my own round-3 paperwork and being blocked by my own check.
    """
    c, r = _setup(tmp_path, _record(lens="correctness"))
    _write(os.path.join(r, "GH-80-round1-consequence.yaml"), _record(lens="consequence"))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert blocks == [], blocks


def test_same_lens_twice_in_a_round_still_blocks(tmp_path):
    c, r = _setup(tmp_path, _record(lens="correctness"))
    _write(os.path.join(r, "GH-80-round1-again.yaml"), _record(lens="correctness", verdict="ship"))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "DUPLICATE_ROUND" in _codes(blocks)


def test_one_adverse_lens_decides_the_round(tmp_path):
    """A clean second opinion is not a veto override."""
    c, r = _setup(tmp_path, _record(lens="correctness", verdict="ship"))
    _write(os.path.join(r, "GH-80-round1-bypass.yaml"),
           _record(lens="bypass", verdict="do-not-ship"))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "VERDICT_NOT_SHIP" in _codes(blocks), blocks


def test_a_squash_merged_review_counts_when_the_tree_is_identical(tmp_path):
    """Two-person release: reviewer on a branch, publisher on a fresh clone.

    The commit is unreachable after a squash-merge, so an identical tree reported STALE and the
    two-minute exit was to sed reviewed_sha — the forgery the gate exists to refuse.
    """
    repo = tmp_path / "repo"
    (repo / ".hitl" / "reviews").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(repo), check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "config", k, v], cwd=str(repo), check=True)
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")
    _write(repo / ".hitl" / "current-change.yaml", {"change_id": "GH-80", "tier": 2})
    subprocess.run(["git", "add", "-A"], cwd=str(repo), check=True)
    subprocess.run(["git", "commit", "-qm", "work"], cwd=str(repo), check=True)
    tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=str(repo),
                          capture_output=True, text=True).stdout.strip()

    c = str(repo / ".hitl" / "current-change.yaml")
    r = str(repo / ".hitl" / "reviews")
    _write(repo / ".hitl" / "reviews" / "GH-80-round1.yaml",
           _record(reviewed_sha="f" * 40, reviewed_tree=tree))
    blocks, _ = check(c, r, root=str(repo))
    assert blocks == [], "an unreachable commit with an identical tree must still count:\n%s" % blocks

    # A different tree must not.
    _write(repo / ".hitl" / "reviews" / "GH-80-round1.yaml",
           _record(reviewed_sha="f" * 40, reviewed_tree="e" * 40))
    assert "REVIEW_STALE" in _codes(check(c, r, root=str(repo))[0])


def test_untracked_build_output_does_not_trap_the_gate(tmp_path):
    """`build` creates dist/, then re-running the gate said 'commit it' — wrong advice, and the
    loop it starts ends at sed-ing the sha."""
    repo = tmp_path / "repo"
    (repo / ".hitl" / "reviews").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(repo), check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "config", k, v], cwd=str(repo), check=True)
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")
    _write(repo / ".hitl" / "current-change.yaml", {"change_id": "GH-80", "tier": 2})
    subprocess.run(["git", "add", "-A"], cwd=str(repo), check=True)
    subprocess.run(["git", "commit", "-qm", "work"], cwd=str(repo), check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                          capture_output=True, text=True).stdout.strip()
    _write(repo / ".hitl" / "reviews" / "GH-80-round1.yaml", _record(reviewed_sha=head))

    (repo / "dist").mkdir()
    (repo / "dist" / "bundle.js").write_text("built\n", encoding="utf-8")
    c = str(repo / ".hitl" / "current-change.yaml")
    r = str(repo / ".hitl" / "reviews")
    assert check(c, r, root=str(repo))[0] == [], "build output must not block the gate"

    # ...but unreviewed SOURCE still must.
    (repo / "code.py").write_text("x = 2\n", encoding="utf-8")
    assert "UNCOMMITTED_CHANGES" in _codes(check(c, r, root=str(repo))[0])

# ---------------------------------------------------------------------------
# Lens vocabulary (#90)
# ---------------------------------------------------------------------------

def _multi(tmp_path, lenses, workflow_id=None):
    """A round reviewed through several lenses, one record each."""
    root = tmp_path
    change = {"change_id": "GH-80", "tier": 2}
    if workflow_id:
        change["workflow"] = {"id": workflow_id, "steps": []}
    _write(root / ".hitl" / "current-change.yaml", change)
    for i, lens in enumerate(lenses, 1):
        _write(root / ".hitl" / "reviews" / ("GH-80-round1-%d.yaml" % i), _record(lens=lens))
    return (str(root / ".hitl" / "current-change.yaml"), str(root / ".hitl" / "reviews"))


def test_a_numbered_second_lens_no_longer_hides_a_duplicate(tmp_path):
    """`consequence-2` is a second reviewer on the same question, and it read as a distinct lens.

    Grouping compared raw strings, so the downstream project's extra consequence reviewer was
    invisible to the duplicate check. Two reviewers on one lens find the same things twice, which
    is the cost this check exists to prevent.
    """
    c, r = _multi(tmp_path, ["consequence", "consequence-2"])
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "DUPLICATE_ROUND" in _codes(blocks), blocks


@pytest.mark.parametrize("alias,canon", [("destructiveness", "consequence"), ("migration", "data"),
                                         ("install", "upgrade"), ("perf", "scalability")])
def test_older_lens_names_still_validate(tmp_path, alias, canon):
    """Records written before the catalog existed must keep passing.

    A vocabulary that rejects yesterday's records is a reason to delete the check rather than
    rename the lens.
    """
    c, r = _multi(tmp_path, ["correctness", alias])
    blocks, warns = check(c, r, sha=SHA, root=str(tmp_path))
    assert not blocks, blocks
    assert not any("UNKNOWN_LENS" in w for w in warns), warns


def test_an_alias_collides_with_its_canonical_name(tmp_path):
    """`consequence` + `destructiveness` is one lens twice, however it is spelled."""
    c, r = _multi(tmp_path, ["consequence", "destructiveness"])
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "DUPLICATE_ROUND" in _codes(blocks), blocks


def test_an_unknown_lens_warns_but_never_blocks(tmp_path):
    c, r = _multi(tmp_path, ["correctness", "vibes"])
    blocks, warns = check(c, r, sha=SHA, root=str(tmp_path))
    assert not blocks, blocks
    assert any("UNKNOWN_LENS" in w for w in warns), warns






def _rel(tmp_path, findings, round_=1, extra_change=None):
    root = tmp_path
    change = {"change_id": "GH-80", "tier": 2, "workflow": {"id": "release", "steps": []}}
    if extra_change:
        change.update(extra_change)
    _write(root / ".hitl" / "current-change.yaml", change)
    for i, lens in enumerate(("correctness", "consequence"), 1):
        rec = _record(lens=lens, round=round_, findings=findings if i == 1 else [])
        _write(root / ".hitl" / "reviews" / ("GH-80-round%d-%d.yaml" % (round_, i)), rec)
    return (str(root / ".hitl" / "current-change.yaml"), str(root / ".hitl" / "reviews"))






def test_round_three_says_it_should_have_been_a_decision(tmp_path):
    c, r = _rel(tmp_path, [], round_=3)
    blocks, warns = check(c, r, sha=SHA, root=str(tmp_path))
    assert not blocks, blocks
    assert any("ROUND_DEPTH" in w for w in warns), warns


def test_two_rounds_do_not_warn(tmp_path):
    c, r = _rel(tmp_path, [], round_=2)
    _, warns = check(c, r, sha=SHA, root=str(tmp_path))
    assert not any("ROUND_DEPTH" in w for w in warns), warns


def test_the_same_finding_in_consecutive_rounds_is_flagged_as_scope(tmp_path):
    """GH-458 re-scoped at round 4 and the recurring finding dissolved. It was available at round 2."""
    root = tmp_path
    _write(root / ".hitl" / "current-change.yaml", {"change_id": "GH-80", "tier": 2})
    shared = {"id": "F1", "severity": "HIGH", "claim": "the shared account makes runs collide",
              "reproduction": "run twice", "status": "fixed", "verified_by": "re-ran: passes"}
    _write(root / ".hitl" / "reviews" / "GH-80-round1.yaml", _record(round=1, findings=[shared]))
    _write(root / ".hitl" / "reviews" / "GH-80-round2.yaml", _record(round=2, findings=[shared]))
    _, warns = check(str(root / ".hitl" / "current-change.yaml"),
                     str(root / ".hitl" / "reviews"), sha=SHA, root=str(root))
    assert any("RECURRING_FINDING" in w for w in warns), warns


def test_distinct_findings_across_rounds_are_not_flagged(tmp_path):
    root = tmp_path
    _write(root / ".hitl" / "current-change.yaml", {"change_id": "GH-80", "tier": 2})
    for n, claim in ((1, "the shared account collides"), (2, "the retry loop never terminates")):
        _write(root / ".hitl" / "reviews" / ("GH-80-round%d.yaml" % n),
               _record(round=n, findings=[{"id": "F1", "severity": "HIGH", "claim": claim,
                                           "reproduction": "r", "status": "fixed",
                                           "verified_by": "re-ran: passes"}]))
    _, warns = check(str(root / ".hitl" / "current-change.yaml"),
                     str(root / ".hitl" / "reviews"), sha=SHA, root=str(root))
    assert not any("RECURRING_FINDING" in w for w in warns), warns


def test_a_second_reviewers_open_critical_is_not_invisible(tmp_path):
    """Findings were read off ONE record per round — the first adverse one, or the last if all said
    ship. So an unresolved CRITICAL in the other reviewer's record shipped unseen.

    Same shape as the duplicate-lens hole: two reviewers per round is the design, and half of them
    were not being read. Found by writing a test that put the finding on the record the gate did not
    happen to select.
    """
    root = tmp_path
    _write(root / ".hitl" / "current-change.yaml", {"change_id": "GH-80", "tier": 2})
    _write(root / ".hitl" / "reviews" / "GH-80-round1-a.yaml",
           _record(lens="correctness",
                   findings=[{"id": "F1", "severity": "CRITICAL", "claim": "unfixed data loss",
                              "reproduction": "r", "status": "open"}]))
    _write(root / ".hitl" / "reviews" / "GH-80-round1-b.yaml",
           _record(lens="consequence", findings=[]))
    blocks, _ = check(str(root / ".hitl" / "current-change.yaml"),
                      str(root / ".hitl" / "reviews"), sha=SHA, root=str(root))
    assert "FINDING_OPEN" in _codes(blocks), blocks


# ── the verification-review record (schema 2.0, #101) ────────────────────────────────────────────
# Two shapes are read. The old one (severity, stance: refute, ship) keeps validating — every test
# above still runs against it. The new one carries a checks table and three finding classes.

def _v2(**over):
    rec = {
        "schema_version": "2.0",
        "change_id": "GH-80",
        "round": 1,
        "reviewed_sha": SHA,
        "scope": "diff v1.0.0..HEAD",
        "reviewer": {"model": "fable", "context": "clean", "spawned_by": "hitl:verification-review"},
        "checks": [{"check": "gate exits 0 on a clean record", "command": "python3 check_review.py",
                    "result": "pass", "output": "exit 0"}],
        "findings": [],
        "verdict": "verified",
    }
    rec.update(over)
    return rec


def test_a_verified_record_with_checks_passes_and_needs_no_stance(tmp_path):
    c, r = _setup(tmp_path, _v2())
    blocks, warns = check(c, r, sha=SHA, root=str(tmp_path))
    assert blocks == [], blocks
    assert not any("SHALLOW_REVIEW" in w for w in warns), "a full checks table with nothing found is the expected clean outcome"
    assert "WRONG_STANCE" not in _codes(blocks)


def test_a_1_0_record_still_requires_refute_and_ship(tmp_path):
    c, r = _setup(tmp_path, _record(stance="verify"))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "WRONG_STANCE" in _codes(blocks)


def test_stops_and_decide_block_while_open_minor_never_does(tmp_path):
    for cls, blocks_expected in (("stops", True), ("decide", True), ("minor", False)):
        c, r = _setup(tmp_path / cls, _v2(findings=[{"id": "F1", "class": cls, "claim": "x",
                                                     "evidence": "ran y: boom", "status": "open"}]))
        blocks, _ = check(c, r, sha=SHA, root=str(tmp_path / cls))
        assert ("FINDING_OPEN" in _codes(blocks)) is blocks_expected, (cls, blocks)


def test_a_decided_point_needs_a_name(tmp_path):
    c, r = _setup(tmp_path, _v2(findings=[{"id": "F1", "class": "decide", "claim": "x",
                                           "evidence": "e", "status": "accepted"}]))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "UNSIGNED_ACCEPTANCE" in _codes(blocks)


def test_an_unknown_class_is_malformed(tmp_path):
    c, r = _setup(tmp_path, _v2(findings=[{"id": "F1", "class": "critical", "claim": "x", "status": "open"}]))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "REVIEW_MALFORMED" in _codes(blocks)


def test_not_verified_blocks(tmp_path):
    c, r = _setup(tmp_path, _v2(verdict="not-verified"))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "VERDICT_NOT_SHIP" in _codes(blocks)


def test_a_failed_check_contradicts_a_verified_verdict(tmp_path):
    c, r = _setup(tmp_path, _v2(checks=[{"check": "install is 2.10.1", "command": "cat plugin.json",
                                         "result": "fail", "output": "2.10.0"}]))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "VERDICT_CONTRADICTED" in _codes(blocks), blocks


def test_no_checks_and_unknown_checks_warn_but_do_not_block(tmp_path):
    c, r = _setup(tmp_path / "none", _v2(checks=[]))
    blocks, warns = check(c, r, sha=SHA, root=str(tmp_path / "none"))
    assert blocks == [] and any("NO_CHECKS" in w for w in warns), (blocks, warns)
    c, r = _setup(tmp_path / "unk", _v2(checks=[{"check": "x", "command": "y", "result": "unknown"}]))
    blocks, warns = check(c, r, sha=SHA, root=str(tmp_path / "unk"))
    assert blocks == [] and any("UNKNOWN_CHECK" in w for w in warns), (blocks, warns)


def test_a_bad_check_result_is_malformed(tmp_path):
    c, r = _setup(tmp_path, _v2(checks=[{"check": "x", "command": "y", "result": "ok"}]))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert "REVIEW_MALFORMED" in _codes(blocks)


def test_old_and_new_shapes_mix_across_rounds(tmp_path):
    """A repo upgraded mid-change has a 1.0 round 1 and a 2.0 round 2. The newest round decides."""
    c, r = _setup(tmp_path, _record(round=1, verdict="do-not-ship",
                                    findings=[{"id": "F1", "severity": "HIGH", "claim": "x", "status": "open"}]))
    _write(os.path.join(r, "GH-80-round2.yaml"), _v2(round=2))
    blocks, _ = check(c, r, sha=SHA, root=str(tmp_path))
    assert blocks == [], blocks
