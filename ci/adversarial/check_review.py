#!/usr/bin/env python3
"""Fail-closed gate: a release must carry a fresh, independent adversarial review.

    check_review.py [--change .hitl/current-change.yaml] [--reviews .hitl/reviews] [--sha <sha>]

Exit 0 = clean, 2 = blocked, 1 = usage error.

WHAT THIS CAN AND CANNOT DO — read before trusting it.

It cannot verify that a review was genuinely adversarial, or that the reviewer was genuinely
independent. Those are properties of an LLM's behaviour, and a record asserting them is an
attestation, not proof. Anyone determined to fake this can.

What it CAN verify is freshness, and that is the load-bearing rule: the record names the commit it
reviewed, and the gate fails unless that matches what is about to ship. You cannot review an early
draft, keep editing, and still pass — the record goes stale the moment the code moves. Everything
else here is bookkeeping around that one fact.

The failure this exists to prevent is specific and observed: a release was published on the
author's own verification, and shipped a defect that destroyed user data. The point is not to prove
a review happened; it is to make skipping one impossible to do silently.
"""
import argparse
import io
import os
import re
import subprocess
import sys

try:
    import yaml
except Exception:  # pragma: no cover - environment without PyYAML
    sys.stderr.write("[BLOCK] MALFORMED: PyYAML is required to verify the review gate\n")
    sys.exit(2)

BLOCKING = ("CRITICAL", "HIGH")
SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
OPEN_STATES = ("open",)
RESOLVED_STATES = ("fixed", "accepted")

# The lens vocabulary, mirrored from the catalog in ai/shared/adversarial-review.md. Kept here as
# data rather than read from a file on purpose: this validator is copied into product repos, and
# `dev-update` copies only *.py into ci/adversarial/ — a catalog file would be absent in every
# repo onboarded before it existed, which is the "ships to shared/ but nothing copies it in"
# defect from 2.4.1 and 2.6.2. A test asserts these ids match the catalog.
LENSES = ("fitness", "correctness", "consequence", "upgrade", "security", "data", "scalability",
          "operability", "compatibility", "bypass", "interfaces", "user", "cost")

# Older names that still appear in records written before the catalog existed.
LENS_ALIASES = {"destructiveness": "consequence", "migration": "data", "install": "upgrade",
                "perf": "scalability", "functionality": "fitness"}


def canonical_lens(raw):
    """Resolve a recorded lens to its catalog id.

    Duplicate detection groups by lens, and it compared raw strings — so a second consequence
    reviewer filed as `consequence-2` was invisible to it, which is exactly what happened
    downstream. Strip the disambiguating suffix people reach for, then apply the alias map.
    """
    lens = str(raw or "").strip().lower()
    lens = re.sub(r"[\s_-]*\d+$", "", lens)
    lens = re.sub(r"[\s_-]*(bis|b|two|second)$", "", lens)
    return LENS_ALIASES.get(lens, lens)


def _fail(findings, code, msg):
    findings.append("[BLOCK] %s: %s" % (code, msg))


def _head_sha(root):
    try:
        out = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                             capture_output=True, text=True)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


# Writing the review down is part of the procedure, and it necessarily changes the repo. Comparing
# raw commit shas made the gate impossible to pass honestly: record the review, commit it as the
# skill instructs, and the record you just wrote is stale. The only escapes were --sha or editing
# reviewed_sha — i.e. the gate trained people to fake exactly what it exists to prevent.
#
# So freshness is about the CODE, not the commit. These paths are governance bookkeeping, not
# shippable content, and a difference confined to them does not invalidate a review.
# `.hitl/` is governance state, never shipped code, and `git status` reports an untracked
# directory as `.hitl/` rather than its files — so the prefix has to cover the directory too.
EXEMPT_PREFIXES = (".hitl/",)
EXEMPT_PATHS = (".hitl",)


def _exempt(p):
    return p in EXEMPT_PATHS or any(p.startswith(x) for x in EXEMPT_PREFIXES)


MIN_SHA = 7


BUILD_OUTPUT = ("dist/", "build/", "out/", "target/", "node_modules/", ".venv/", "__pycache__/")


def _looks_like_build_output(path):
    return any(path == d.rstrip("/") or path.startswith(d) for d in BUILD_OUTPUT)


def _dirty(root):
    """Paths modified in the working tree that would ship but were never reviewed."""
    r = subprocess.run(["git", "-C", root, "status", "--porcelain"], capture_output=True, text=True)
    if r.returncode != 0:
        return []
    out = []
    for line in r.stdout.splitlines():
        status, path = line[:2], line[3:].strip()
        if not path or _exempt(path):
            continue
        # Untracked build output is not unreviewed source. Telling someone to commit dist/ is wrong
        # advice, and the loop it creates (ignore it -> .gitignore is dirty -> commit -> stale)
        # ends at sed-ing the sha.
        if status == "??" and _looks_like_build_output(path):
            continue
        out.append(path)
    return out


def _tree(root, ref):
    r = subprocess.run(["git", "-C", root, "rev-parse", "%s^{tree}" % ref],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def _is_fresh(root, reviewed, target, reviewed_tree=""):
    """(fresh, reason). Fail closed: anything we cannot determine is stale."""
    # It must be a commit id, not any ref git will accept. A branch name resolves to whatever the
    # branch points at TODAY, so a record naming one is permanently fresh no matter how far the code
    # moves — and a leading dash is an option, not a ref.
    if not re.fullmatch(r"[0-9a-fA-F]{%d,40}" % MIN_SHA, reviewed):
        return False, ("reviewed_sha %r is not a commit id (need %d-40 hex chars). A branch or tag "
                       "name would never go stale, which is the whole guarantee" % (reviewed, MIN_SHA))
    if target.startswith(reviewed) or reviewed.startswith(target):
        return True, ""
    r = subprocess.run(["git", "-C", root, "diff", "--name-only", reviewed, target],
                       capture_output=True, text=True)
    if r.returncode != 0:
        # The reviewed commit is unreachable here — squash-merged, branch deleted, fresh clone.
        # If the record captured the tree it reviewed and that tree is what is about to ship, the
        # content is identical and re-reviewing it would be theatre. Without a tree, fail closed.
        if reviewed_tree:
            here = _tree(root, target)
            if here and here == reviewed_tree:
                return True, ""
            return False, ("the reviewed commit is unreachable here and the reviewed tree does not "
                           "match what would ship")
        return False, ("cannot compare them in this repo (record has no reviewed_tree; if this was "
                       "squash-merged, re-review at the merge commit)")
    changed = [l.strip() for l in r.stdout.splitlines() if l.strip()]
    substantive = [c for c in changed if not _exempt(c)]
    if substantive:
        head = ", ".join(substantive[:3])
        more = "" if len(substantive) <= 3 else " (+%d more)" % (len(substantive) - 3)
        return False, "%s changed since%s" % (head, more)
    return True, ""


def _acknowledged_skip(change):
    """The skip record that lets a release proceed with no review, or None.

    Requires an owner. An unattributed acknowledgement is not an acknowledgement — it is the
    absence of one, written down.
    """
    skips = change.get("skips")
    if not isinstance(skips, list):
        return None
    for s in skips:
        if not isinstance(s, dict):
            continue
        if str(s.get("step", "")).strip() != "adversarial_review":
            continue
        by = ""
        for field in ("ack_by", "accepted_by", "authorized_by", "acknowledged_by"):
            if str(s.get(field, "")).strip():
                by = str(s.get(field)).strip()
                break
        if not by:
            continue
        return {"by": by, "reason": str(s.get("reason", "")).strip()}
    return None


def _claimed_without_record(change, reviews_dir, change_id):
    """adv_* steps marked done while nothing was written down."""
    wf = change.get("workflow")
    steps = wf.get("steps") if isinstance(wf, dict) else None
    if not isinstance(steps, list):
        return []
    if os.path.isdir(reviews_dir):
        for n in os.listdir(reviews_dir):
            if not n.endswith((".yaml", ".yml")):
                continue
            doc, err = _load(os.path.join(reviews_dir, n))
            # Match the change_id FIELD, as every other lookup here does. Matching the filename
            # let a valid record be honoured and reported missing in the same run.
            if not err and isinstance(doc, dict) and \
                    str(doc.get("change_id", "")).strip() == change_id:
                return []
    return [str(s.get("key")) for s in steps
            if isinstance(s, dict) and str(s.get("key", "")).startswith("adv_")
            and str(s.get("status", "")).strip() == "done"]


def _adverse_verdict(reviews_dir, change_id):
    """(path, verdict) of the newest record for this change whose verdict is not 'ship'."""
    if not os.path.isdir(reviews_dir):
        return None
    best = None
    for name in sorted(os.listdir(reviews_dir)):
        if not name.endswith((".yaml", ".yml")):
            continue
        doc, err = _load(os.path.join(reviews_dir, name))
        if not err and isinstance(doc, dict) and str(doc.get("change_id", "")).strip() != change_id:
            continue
        if err or not isinstance(doc, dict):
            continue
        v = str(doc.get("verdict", "")).strip().lower()
        if v and v != "ship":
            try:
                n = int(doc.get("round", 0))
            except Exception:
                n = 0
            if best is None or n >= best[0]:
                best = (n, os.path.join(reviews_dir, name), doc.get("verdict"))
    return (best[1], best[2]) if best else None


def _load(path):
    """Return (doc, error). A file we cannot parse blocks — it is never treated as absent."""
    try:
        with io.open(path, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
    except Exception as exc:
        return None, str(exc)
    if doc is None:
        return None, "file is empty"
    if not isinstance(doc, dict):
        return None, "expected a mapping, got %s" % type(doc).__name__
    return doc, None


def check(change_path, reviews_dir, sha=None, root="."):
    out = []
    change, err = _load(change_path)
    if err:
        _fail(out, "MALFORMED", "%s: %s" % (change_path, err))
        return out, []
    change_id = str(change.get("change_id") or change.get("id") or "").strip()
    if not change_id:
        _fail(out, "MALFORMED", "change file has no change_id")
        return out, []

    target = (sha or _head_sha(root)).strip()
    if not target:
        _fail(out, "NO_SHA", "cannot determine the commit under review (not a git repo?)")
        return out, []

    # The floor path: a release CAN go out without a review, but only on a recorded, attributed
    # acknowledgement. Without this the gate had no honest escape at all, and a gate with no escape
    # is one that gets deleted from the process the first time it is inconvenient at 2am.
    dirty = _dirty(root)

    ack = _acknowledged_skip(change)
    if ack:
        if dirty:
            head = ", ".join(dirty[:3])
            more = "" if len(dirty) <= 3 else " (+%d more)" % (len(dirty) - 3)
            _fail(out, "UNCOMMITTED_CHANGES",
                  "%s%s modified but not committed. A waiver covers the review, not this: the "
                  "build packages the working tree, so this would ship unseen by anyone."
                  % (head, more))
            return out, []
        adverse = _adverse_verdict(reviews_dir, change_id)
        extra = ""
        if adverse:
            extra = ("\n        NOTE: a review of this change exists and its verdict is %r (%s). "
                     "The waiver is overriding it." % (adverse[1], os.path.basename(adverse[0])))
        return [], ["[warn] REVIEW_WAIVED: %s is shipping WITHOUT an adversarial review.\n"
                    "        Acknowledged by %s: %s%s\n"
                    "        Recorded in the change file, and it stays there."
                    % (change_id, ack.get("by") or "?", ack.get("reason") or "no reason given", extra)]

    for step in _claimed_without_record(change, reviews_dir, change_id):
        _fail(out, "UNBACKED_REVIEW",
              "step '%s' is marked done but no review record exists for %s. A review with nothing "
              "written down is the silent skip this gate exists to catch." % (step, change_id))

    if not os.path.isdir(reviews_dir):
        _fail(out, "REVIEW_MISSING",
              "no %s/ — an adversarial review is required before publishing %s.\n"
              "        Run /hitl:dev-adversarial-review, or record an explicit acknowledgement "
              "to ship without one." % (reviews_dir, change_id))
        return out, []

    records = []
    warn_unreadable = []
    for name in sorted(os.listdir(reviews_dir)):
        if not name.endswith((".yaml", ".yml")):
            continue
        path = os.path.join(reviews_dir, name)
        doc, err = _load(path)
        if err:
            # A record we cannot read is not a record we can trust — but only if it is OURS.
            # Records are kept forever, so unrelated debris from a long-closed change must not
            # block every future release.
            if os.path.basename(path).startswith(change_id + "-"):
                _fail(out, "MALFORMED", "%s: %s" % (path, err))
            else:
                warn_unreadable.append(path)
            continue
        if str(doc.get("change_id", "")).strip() == change_id:
            records.append((path, doc))

    if not records:
        _fail(out, "REVIEW_MISSING",
              "no review record for %s in %s/" % (change_id, reviews_dir))
        return out, []

    # The newest round is the one that decides. Earlier rounds are history.
    def _round(item):
        try:
            return int(item[1].get("round", 0))
        except Exception:
            return 0
    seen = {}
    for pth, doc in records:
        n = _round((pth, doc))
        lens = canonical_lens(doc.get("lens"))
        seen.setdefault((n, lens), []).append(pth)
    dupes = sorted((n, l) for (n, l), paths in seen.items() if len(paths) > 1)
    records.sort(key=_round)
    top = _round(records[-1])
    latest = [r for r in records if _round(r) == top]
    # Any lens saying do-not-ship decides the round. A second opinion is not a veto override.
    adverse_in_round = [r for r in latest
                        if str(r[1].get("verdict", "")).strip().lower() != "ship"]
    path, rec = (adverse_in_round[0] if adverse_in_round else latest[-1])
    warnings = ["[warn] UNREADABLE_RECORD: %s could not be parsed (not this change — ignored)" % u
                for u in warn_unreadable]

    for key in dupes:
        n, lens = key
        _fail(out, "DUPLICATE_ROUND",
              "round %s has more than one record for lens %r (%s). Two reviewers in one round is "
              "expected — but on DIFFERENT lenses, or they find the same things twice. Names are "
              "resolved to the catalog id first, so `%s-2` counts as `%s`: pick a second lens from "
              "the catalog in shared/adversarial-review.md instead of numbering this one."
              % (n, lens or "(unset)", ", ".join(seen[key]), lens or "x", lens or "x"))

    # An unrecognised lens is information, never a block. Records written before the catalog
    # existed have to keep validating, and a vocabulary that rejects them would be a reason to
    # delete the check rather than fix the name.
    for pth, doc in latest:
        raw = str(doc.get("lens", "")).strip()
        if raw and canonical_lens(raw) not in LENSES:
            warnings.append(
                "[warn] UNKNOWN_LENS: %s uses lens %r, which is not in the catalog "
                "(shared/adversarial-review.md). It still counts; the id is what lets the gate "
                "group reviewers and what tells the next round what was already looked at."
                % (os.path.basename(pth), raw))

    if top >= 3:
        warnings.append(
            "[warn] ROUND_DEPTH: this is round %d. Two rounds then a human decision is the rule — "
            "round 3 onward is a choice someone makes, not a continuation. Later rounds mostly read "
            "fixes written minutes earlier, and find the ones that were right about the defect and "
            "wrong about its class." % top)

    # A finding that survives consecutive rounds is a scope question, not a fix question. Narrowing
    # the change often dissolves the whole cluster, and it is cheapest before three rounds of
    # repairs are built on top of it. Compared on the claim, because ids restart per round.
    by_round = {}
    for _, doc in records:
        try:
            n = int(doc.get("round", 0))
        except Exception:
            continue
        for f in (doc.get("findings") or []):
            if not isinstance(f, dict):
                continue
            claim = re.sub(r"[^a-z0-9 ]", "", str(f.get("claim", "")).lower()).strip()[:60]
            if claim:
                by_round.setdefault(n, set()).add(claim)
    recurring = []
    for n in sorted(by_round):
        if n - 1 in by_round:
            recurring.extend(sorted(by_round[n] & by_round[n - 1])[:3])
    if recurring:
        warnings.append(
            "[warn] RECURRING_FINDING: the same finding appears in consecutive rounds (%s). Two "
            "rounds blocked by one underlying decision is a scope question for a human, not another "
            "fix." % "; ".join('"%s..."' % c for c in recurring[:3]))

    if dirty:
        head = ", ".join(dirty[:3])
        more = "" if len(dirty) <= 3 else " (+%d more)" % (len(dirty) - 3)
        _fail(out, "UNCOMMITTED_CHANGES",
              "%s%s modified but not committed. The build packages the working tree, so this would "
              "ship unreviewed. Commit it and re-review." % (head, more))

    reviewed = str(rec.get("reviewed_sha", "")).strip()
    if not reviewed:
        _fail(out, "REVIEW_MALFORMED", "%s: reviewed_sha is missing" % path)
    else:
        fresh, why = _is_fresh(root, reviewed, target,
                                str(rec.get("reviewed_tree", "")).strip())
        if not fresh:
            # THE load-bearing rule.
            _fail(out, "REVIEW_STALE",
                  "%s reviewed %s but %s is about to ship — %s. Re-review the current code."
                  % (path, reviewed[:12], target[:12], why))

    reviewer = rec.get("reviewer")
    if not isinstance(reviewer, dict):
        _fail(out, "REVIEW_MALFORMED", "%s: reviewer must be a mapping" % path)
        reviewer = {}
    if str(reviewer.get("context", "")).strip().lower() != "clean":
        _fail(out, "NOT_INDEPENDENT",
              "%s: reviewer.context must be 'clean' — a reviewer that shares the author's context "
              "is not an independent check" % path)

    if str(rec.get("stance", "")).strip().lower() != "refute":
        _fail(out, "WRONG_STANCE",
              "%s: stance must be 'refute'. A reviewer setting out to confirm a design finds it "
              "confirmed" % path)

    # EVERY record in the governing round, not just the one whose verdict was selected. Findings
    # were read off the selected record alone, so a second reviewer's unresolved CRITICAL shipped
    # unseen whenever the selected record said `ship` — the same shape as the duplicate-lens hole:
    # two reviewers per round is the design, and half of them were not being read.
    # Findings are read from the governing round. Carrying earlier rounds forward was tried in
    # 2.8.0 and cut: four CRITICALs in the only review it ever had, all in how it decided that a
    # finding had been resolved. Reasoning across rounds needs a model this validator does not
    # have — see #92. Until then a round says what it says, and the trail is what carries history.
    findings = []
    for _p, _doc in latest:
        _f = _doc.get("findings")
        if _f is None:
            _f = []
        if not isinstance(_f, list):
            _fail(out, "REVIEW_MALFORMED", "%s: findings must be a list" % _p)
            continue
        findings.extend((_p, i, item) for i, item in enumerate(_f))

    unresolved = []
    for fpath, i, f in findings:
        if not isinstance(f, dict):
            _fail(out, "REVIEW_MALFORMED", "%s: findings[%d] is not a mapping" % (fpath, i))
            continue
        sev = str(f.get("severity", "")).strip().upper()
        if sev not in SEVERITIES:
            _fail(out, "REVIEW_MALFORMED",
                  "%s: findings[%d] severity %r is not one of %s" % (fpath, i, f.get("severity"), ", ".join(SEVERITIES)))
            continue
        state = str(f.get("status", "open")).strip().lower()
        if state not in OPEN_STATES + RESOLVED_STATES:
            _fail(out, "REVIEW_MALFORMED",
                  "%s: findings[%d] status %r is not open/fixed/accepted" % (fpath, i, f.get("status")))
            continue
        if sev in BLOCKING and state in OPEN_STATES:
            unresolved.append("%s: %s" % (sev, str(f.get("claim", "?"))[:80]))

        if state == "accepted" and not str(f.get("accepted_by", "")).strip():
            _fail(out, "UNSIGNED_ACCEPTANCE",
                  "%s: findings[%d] is accepted with no accepted_by — accepting a finding is a "
                  "decision someone owns" % (fpath, i))

    for u in unresolved:
        _fail(out, "FINDING_OPEN", "%s — fix it, or accept it explicitly with accepted_by" % u)

    verdict = str(rec.get("verdict", "")).strip().lower()
    if verdict != "ship":
        _fail(out, "VERDICT_NOT_SHIP",
              "%s: verdict is %r — the reviewer did not clear this for release"
              % (path, rec.get("verdict")))

    # Not a block: a genuinely clean change exists. But one round that found nothing, on a large
    # diff, is more often a shallow review than a flawless one — so say so.
    if _round((path, rec)) <= 1 and not findings:  # findings across the whole round
        warnings.append(
            "[warn] SHALLOW_REVIEW: %s is round 1 with zero findings. That happens, but it is also "
            "what a review that did not really run looks like." % path)

    return out, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--change", default=".hitl/current-change.yaml")
    ap.add_argument("--reviews", default=".hitl/reviews")
    ap.add_argument("--sha", default=None, help="commit under review (default: HEAD)")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)

    try:
        blocks, warns = check(args.change, args.reviews, args.sha, args.root)
    except Exception as exc:  # never fail open on an unexpected error
        sys.stderr.write("[BLOCK] MALFORMED: unexpected error verifying the review gate: %s\n" % exc)
        return 2

    if args.sha:
        head = _head_sha(args.root)
        if head and not (head.startswith(args.sha) or args.sha.startswith(head)):
            print("[warn] TARGET_NOT_HEAD: checked %s, but HEAD is %s. This is NOT a verdict on "
                  "what would ship." % (args.sha[:12], head[:12]))
    for w in warns:
        print(w)
    for b in blocks:
        print(b)
    if blocks:
        print("\nRelease gate: BLOCKED. An adversarial review of the exact code being shipped is "
              "required before publishing.")
        return 2
    if any("REVIEW_WAIVED" in w for w in warns):
        print("Release gate: PASSED ON A WAIVER — no adversarial review was honoured.")
    else:
        print("Release gate: adversarial review present, fresh, and cleared.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

