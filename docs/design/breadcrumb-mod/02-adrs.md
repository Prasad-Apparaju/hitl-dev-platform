# Breadcrumb as a Mod: Decisions (ADRs)

> Status: **draft v1 (2026-10-05)**. Decisions for FR-37; context in [`01-design.md`](01-design.md).

## ADR-1. The mod draws a cache the shell renderer writes; it does not render

`_steps.sh` is the only renderer and the breadcrumb matrix locks it. A JavaScript re-rendering of
the ribbon would be a second implementation of the same rules with its own drift and its own
matrix. Instead the renderer writes its line to `.hitl/breadcrumb.txt` and the mod draws that text.
The cost is one small file that must be ignored by git, and a dependency on the hooks being wired,
which every onboarded repo already has. The alternative of running the shell renderer from the mod
with `$.process.run` was rejected: process spawning is the call the mods documentation singles out
as the one to look for before trusting a mod, and the band must not need it.

## ADR-2. The setting is a team key in `.hitl/config.yaml`, not `userConfig`

The breadcrumb is a team convention and the file already holds `scenario_review_gate` and
`change_id_prefix`. A plugin `userConfig` prompt is per person and per install, and would make the
band appear for one teammate and not the next. The hooks read the key with `hitl_scalar`, the same
reader they use for the change file, and the mod reads it with one regular expression.

## ADR-3. Three modes, default text

`text` is 2.17.0 unchanged. `band` is for a team wholly on terminals or the Desktop app and quiets
the transcript. `both` is for a mixed team and costs one transcript line per prompt. A two-value
switch would have forced either duplication for everyone who turns it on or silence for everyone on
a surface that cannot draw.

## ADR-4. The mod ships inside the HITL plugin, not as a second plugin

One install, one update path, one version. A separate plugin would let a person opt in per
install, but ADR-2 already rejected per-person opt-in, and the setting makes the mod inert by
default. Anyone who wants no mod code at all can disable mods for the plugin with `disableAllHooks`
or `--safe-mode`, which the docs for this feature say.

## ADR-5. Footprint is asserted by the validator's own output

`claude plugin validate` lists every event a module hooks and every mods API method it calls,
from static analysis, without running the code. A pytest under `ci/` assembles a plugin-shaped
directory from the source and asserts those two lists are exactly the allowed sets. That is a
stronger guard than a source grep, and it fails the moment anyone adds a handler. CI installs the
`claude` CLI to run it; locally the test skips with a reason when the CLI is absent.

## ADR-6. Band plus status line, never band instead of status line

The status line is where the context bar and the model live, and it is the one line a person sees
in every surface. The band adds the phase ribbon in full width; it does not replace anything that
works everywhere.

## ADR-7. The welcome hook quiets only the active-change ribbon

In `band` mode the intake directive for no active change still prints. It is a gate message, not a
breadcrumb, and the band has nothing to draw when there is no change.
