# Releasing HITL

How a version of HITL gets from this repo to `claude plugin install hitl@hitl`. This is the
project's own runbook for the twelve-step `release` workflow described generically in
`ai/claude/dev-practices/workflow-steps.md`. Every command below was run for 2.10.0 on 2026-09-04.

## The shape

- **This repo is the source.** Skills, hooks, validators, templates and docs live under `ai/`,
  `ci/`, `tools/` and `docs/`.
- **`pappar/hitl-claude-plugin` is the built artifact.** `scripts/build.sh` there copies and
  renames the source into the plugin layout. Nothing is edited there by hand.
- **The channel is a branch, not a pin.** The marketplace entry `hitl` serves `release/2.x`;
  `hitl-1x` serves `release/1.x` (legacy, frozen). `claude plugin install` ignores the `commit`
  field in `marketplace.json`, so the branch is what customers get. The plugin repo's `main`
  serves nothing and lags; that is expected.
- **The gate is on the publishing script.** `scripts/release.sh` refuses to build unless the
  source repo has an active change on the `release` workflow that passes both
  `ci/adversarial/check_review.py` and `ci/first-pass/check_skips.py`. Everything else in HITL is
  advisory; this is the only check a release cannot walk past.

Prerequisites: the two repos checked out as siblings (`../hitl-claude-plugin`), the `claude` and
`gh` CLIs, Python 3.10+ with PyYAML and pytest.

## Steps

### 1. Scope

```bash
git log v<previous>..HEAD --oneline
```

Read it. The release note is written from this, not from memory.

### 2. Notes

Fixes land under `## [Unreleased]` in `CHANGELOG.md` as they are committed. Cutting the release
turns that header into `## [X.Y.Z] — YYYY-MM-DD`. Every claim in the section must match the tree;
the 2.9.0 notes shipped with four that did not.

### 3. Bump

Patch for fixes only, minor when behaviour changes (new steps in a plan, a new intake question, a
new gate code). Three places, all checked by tests:

```bash
# ai/claude/plugin/plugin.json  -> "version": "X.Y.Z"
sed -i '' 's/v<previous>/vX.Y.Z/' site/*.html        # a wiring test holds these to plugin.json
python3 tools/scripts/generate-catalog-page.py       # site/catalog.html is generated
```

### 4. Gates

```bash
python3 -m pytest ci/ tools/ -q
python3 ci/skill-lint/check_skills.py
(cd tools/workflow-catalog && python3 derive.py verify)
bash ci/breadcrumb/run_matrix.sh          # a bash harness outside pytest; it has caught what pytest could not
```

### 5. Verification review, or its waiver

Run `/hitl:dev-verification-review` against the exact commit being shipped. It writes the record
the gate reads under `.hitl/reviews/`.

The normal path: two lenses (`upgrade` and `correctness` at release), one clean-context reviewer
each with a checklist, one page back, records in the 2.0 shape at
`.hitl/reviews/<change-id>-round1-<lens>.yaml`. 2.11.0 shipped this way and the gate passed on the
records; GH-109's two records are the precedent to copy.

If the review is declined, the decision is recorded, not skipped. Add a waiver to
`.hitl/waivers.yaml` (owner, `accepted`, `revisit`, `covers`, the reason, what was done instead,
what is known to be open) and point the change file's skip record at it. The gate then prints
`REVIEW_WAIVED` with the name and reason at publish time. 2.9.0 through 2.10.1 shipped this way;
W-001 to W-003 are the precedents.

### 6. The release change file

`scripts/release.sh` reads `.hitl/current-change.yaml` in this repo and requires `workflow.id:
release`. The 2.10.0 file is the template: `change_id: GH-<issue>-release-X.Y.Z`, a tracker issue
under `source_artifacts.issue`, twelve steps, and, when the review is waived, one skip record:

```yaml
skips:
  - { step: adversarial_review, crit: floor, actor: "<name>", ack_by: "<name>",
      disposition: decline, waiver_ref: "W-NNN-release-X.Y.Z", resolved: false,
      ts: "<ISO-8601>", reason: "<why, and what ran instead>" }
```

Check it locally before the script does:

```bash
python3 ci/adversarial/check_review.py --root . --change .hitl/current-change.yaml --reviews .hitl/reviews
python3 ci/first-pass/check_skips.py .hitl/current-change.yaml
```

The review gate blocks on `UNCOMMITTED_CHANGES` until every edit above is committed. That is
deliberate: the build packages the working tree. Commit the release prep, run the gate again, push
`main`, and wait for CI to go green.

### 7 to 9. Build, publish, tag

```bash
cd ../hitl-claude-plugin
git checkout release/2.x && git pull --ff-only
bash scripts/release.sh ../hitl-dev-platform
git push origin release/2.x
git push origin hitl--vX.Y.Z
```

The script runs both validators against the source repo, builds, commits `chore(release): build
vX.Y.Z` and tags it `hitl--vX.Y.Z`. There is no marketplace pin: the `commit` field was dropped
after 2.10.0 because installs ignore it, and the branch head is what is served. Read the build
commit's file list before pushing; it should be exactly the files the release changed.

### 10. Install verify

```bash
export CLAUDE_CONFIG_DIR=$(mktemp -d)
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
find "$CLAUDE_CONFIG_DIR" -name plugin.json -path '*hitl*'
```

Two files come back. `plugins/cache/hitl/hitl/<version>/.claude-plugin/plugin.json` is what was
installed and must read `X.Y.Z`. `plugins/marketplaces/hitl/.claude-plugin/plugin.json` is the
clone of the plugin repo's `main` and shows whatever version `main` is at; it is not the install.
Then exercise something: open a project with `.hitl/` and check the breadcrumb renders.

### 11. Announce

```bash
git tag vX.Y.Z <release-prep commit> && git push origin vX.Y.Z
gh release create vX.Y.Z --title "HITL X.Y.Z — <what it means to a user>" --notes-file <notes>
gh release create hitl--vX.Y.Z -R pappar/hitl-claude-plugin --title "hitl X.Y.Z" --notes "<pointer>"
```

The notes lead with what changes for someone who uses HITL, then the changelog section. Close
the issues the release fixes with a comment naming the version. Longer user-facing announcements
go under `docs/announcements/`.

### 12. Retire

Mark the change file's steps done and remove it; a finished change left active blocks the next
intake. The waiver stays in `.hitl/waivers.yaml` until its `revisit` date is acted on.

## Things that have gone wrong

- **Publishing under a development change.** Every release before 2.6.4 shipped with no review
  because the gate bound to a change file the release never had. The script now refuses unless the
  active change is on the `release` workflow.
- **One validator said ship, the other said malformed.** 2.9.0 and 2.9.1 published on a skip record
  the ledger validator rejected, because the script asked only the review gate. It asks both now.
- **A shipped skill named a file the package did not contain.** 2.9.0's `dev-retro` failed for
  every installed user; `build.sh` now fails the build on an unresolved `shared/` reference.
- **Portal pages five versions behind the plugin.** A wiring test now holds `site/*.html` to
  `plugin.json`.
- **Commit pins that pinned nothing.** Fresh installs in July 2026 received a pre-release because
  the marketplace `commit` field is ignored. Channels are branches.
