---
description: Tune how HITL talks to you in this project — length, whether it narrates its process, how it opens a disagreement. Re-run any time to adjust. Also turns the tuning off for one session, or off for good. Run it when HITL feels too verbose, too terse, or too cautious.
argument-hint: "nothing to set up or adjust — or 'show', 'off', 'on', 'reset'"
disable-model-invocation: true
---

# Preferences

**Input:** $ARGUMENTS

HITL is wordy by default because it does not know you. This fixes that, and you can keep adjusting
it until it feels right.

**Scope: this project.** The settings go in a marked block in this repo's `CLAUDE.md`, alongside the
other HITL block. HITL manages projects; it does not reach into your machine-wide config. If you
want the same preferences everywhere, that is your `~/.claude/CLAUDE.md` and your decision — this
command only offers it if you ask for it by name.

---

## Modes

| Input | What happens |
|---|---|
| *(nothing)* | Set up, or adjust what is already there — the normal path |
| `show` | Print the current settings and stop |
| `off` | Stop applying them, keep them on file. Reversible with `on` |
| `on` | Start applying them again |
| `reset` | Delete the block entirely |

**Turning it off for one session only** needs no command — say *"default mode"* or *"ignore my
preferences"* and behave as HITL does out of the box for the rest of the session. Do not edit the
file for a temporary request. Mention this once when you first set the preferences up, so they know
the escape exists.

---

## `show`

```bash
sed -n '/<!-- HITL:PREFS:BEGIN/,/<!-- HITL:PREFS:END -->/p' CLAUDE.md 2>/dev/null \
  || echo "No HITL preferences set in this project."
```

## `off` / `on`

Flip one line in the block; do not delete anything.

```bash
python3 - "$1" <<'PY'
import io, os, re, sys
mode = sys.argv[1]                       # "off" or "on"
p = "CLAUDE.md"
if not os.path.isfile(p):
    raise SystemExit("No CLAUDE.md in this project.")
s = io.open(p, encoding="utf-8").read()
if "<!-- HITL:PREFS:BEGIN" not in s:
    raise SystemExit("No preferences block here — run /hitl:dev-preferences to set one up.")
want = "PAUSED" if mode == "off" else "ACTIVE"
s2 = re.sub(r"(<!-- HITL:PREFS:BEGIN[^\n]*?status: )(ACTIVE|PAUSED)", r"\g<1>" + want, s, count=1)
if s2 == s:
    raise SystemExit("Could not find the status marker — check the block by hand.")
io.open(p, "w", encoding="utf-8").write(s2)
print("Preferences are now %s." % want)
PY
```

When the marker reads `PAUSED`, ignore the block's contents entirely and behave as default HITL.

## `reset`

Confirm, then remove the block and leave the rest of `CLAUDE.md` untouched:

```bash
python3 - <<'PY'
import io, os, re
p = "CLAUDE.md"
if not os.path.isfile(p):
    raise SystemExit("No CLAUDE.md in this project.")
s = io.open(p, encoding="utf-8").read()
new, n = re.subn(r"\n?<!-- HITL:PREFS:BEGIN.*?<!-- HITL:PREFS:END -->\n?", "\n", s, flags=re.S)
if not n:
    raise SystemExit("No preferences block found — nothing removed.")
io.open(p, "w", encoding="utf-8").write(new)
print("Removed. The rest of CLAUDE.md is untouched.")
PY
```

---

## Setting up, and adjusting

**If a block already exists, this is an adjustment, not a fresh start.** Show them what is set,
then ask what to change — do not re-run the whole interview at someone who has already answered it.

> Right now: short, no workings, decision first, direct. What would you change?

**If there is nothing yet, ask all four at once.** A long interrogation about someone's preference
for brevity would be self-defeating.

> Four quick ones and I'll keep to them in this project:
>
> 1. **Length** — short (bullets, answer first) / standard / full?
> 2. **My workings** — what I did and how I got there: only when you ask / a line or two / all of it
> 3. **Open with** — the decision you need to make, the result, or the context?
> 4. **Disagreements** — straight, or eased in? *(I'll still disagree either way — this is only how it opens.)*
>
> Anything else? "no emoji", "tables over prose", "I know this domain, skip the primer".

Take partial answers; default the rest and say which you assumed. Then **show the block you are
about to write and ask before writing.**

Expect to iterate. Say so:

> Try it for a bit. Run `/hitl:dev-preferences` again to adjust, `off` to pause it, or just say
> "default mode" to drop it for this session.

---

## Writing it

```bash
python3 - <<'PY'
import io, os, re
BLOCK = """<!-- HITL:PREFS:BEGIN status: ACTIVE — /hitl:dev-preferences to adjust, 'off' to pause, 'reset' to remove -->
## How I like responses (this project)

- **Length:** short — lead with the answer, bullets over paragraphs
- **Your workings:** only when I ask
- **Open with:** the decision I need to make
- **Disagreements:** say it straight

Style only. Always tell me a risk, a cost, an uncertainty, or a decision that is mine — briefly if
that is the setting, but never left out. If brevity and completeness conflict, cut the reasoning and
keep the consequence. Ignore this block for one session if I say "default mode".
<!-- HITL:PREFS:END -->"""
p = "CLAUDE.md"
cur = io.open(p, encoding="utf-8").read() if os.path.isfile(p) else ""
if "<!-- HITL:PREFS:BEGIN" in cur:
    if "<!-- HITL:PREFS:END -->" not in cur:
        raise SystemExit("Your preferences block is truncated — fix or delete it by hand; nothing written.")
    out = re.sub(r"<!-- HITL:PREFS:BEGIN.*?<!-- HITL:PREFS:END -->", BLOCK, cur, flags=re.S)
else:
    out = (cur.rstrip("\n") + "\n\n" + BLOCK + "\n") if cur.strip() else BLOCK + "\n"
io.open(p, "w", encoding="utf-8").write(out)
print("Saved to CLAUDE.md in this project.")
PY
```

Replace the bullets with their actual answers. Keep the closing paragraph and the `status:` marker
**verbatim** — one is the floor, the other is how `off` works.

---

## The floor, and why it lives in the file

A preference governs **form, never substance**. Someone who wants three bullets still needs to know
that a migration can destroy their work, that a change is irreversible, that you are guessing, or
that something is theirs to decide.

That paragraph goes **into the block**, not just into this skill, because the block is what future
sessions read. A floor that lives only in the setup command stops existing the moment setup finishes.

---

## When to offer this

Do not advertise it. Offer once, when someone tells you something is wrong with how you are talking:

- "too long", "just give me the answer", "skip the detail"
- "you don't need to explain all that"
- they ask for more depth twice running

> Want me to keep to that? `/hitl:dev-preferences` — four questions, this project only, and you can
> pause or remove it whenever.

Once per session. If they decline, drop it and write nothing.

**Never write preferences from inference.** Two terse messages are not consent to a stored record of
how someone likes to be spoken to.

---

## If they ask for it everywhere

Only if they raise it: the same block in their own `~/.claude/CLAUDE.md` applies to every project
they work in, HITL or not. Tell them that is theirs to edit and HITL will not manage it — then let
them decide. Do not write there on HITL's initiative.

---

## Related

- `/hitl:dev-draft-for <person>` — a message written **to** someone else, using their profile.
  Different thing: that is your audience, this is you.
- `${CLAUDE_PLUGIN_ROOT}/shared/personas.md` — the rules both share.
