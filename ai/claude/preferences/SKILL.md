---
description: Tune how HITL talks to you in this project — length, whether it narrates its process, how it opens a disagreement. Re-run any time to adjust. Also pauses it until you turn it back on, or removes it for good. Run it when HITL feels too verbose, too terse, or too cautious.
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

**Project scope is team scope, and they must be told.** `CLAUDE.md` is normally committed, so this
block reaches every teammate who opens the repo — people who never ran the command and cannot tell
whose settings are in force. Say so before writing, in the same breath as showing the block:

> One thing first: `CLAUDE.md` is committed, so this applies to anyone on the team who opens the
> repo, not just you. I'll put your name on it so they know whose it is and can change it. If you'd
> rather it stayed yours alone, keep it out of git and set it in your own `~/.claude/CLAUDE.md`
> instead — that one is yours and HITL will not touch it.

Not a warning to recite and move past. If they would rather not impose it on the team, that is the
end of it: write nothing here and tell them the machine-wide route. **Record who set it** in the
block's marker so a teammate reading it later knows who to ask.

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
if grep -q '^<!-- HITL:PREFS:BEGIN' CLAUDE.md 2>/dev/null; then
  sed -n '/^<!-- HITL:PREFS:BEGIN/,/^<!-- HITL:PREFS:END -->/p' CLAUDE.md
else
  echo "No HITL preferences set in this project."   # sed exits 0 on no match, so test first
fi
```

**Every marker test below anchors to the start of a line, and masks fenced regions first. Both are
load-bearing.** A real marker begins its own line, so counting unanchored strings makes ordinary
prose look like a block: the writer then edits the sentence describing the markers instead of
appending after it, and `off` refuses because it sees two of everything.

Anchoring alone is not enough. A marker inside a ``` fence *does* begin its line, so a team
documenting the block format in their own `CLAUDE.md` would have that example treated as the real
block: their text replaced, and the block written inside the fence where no session reads it.
Fences are blanked before any marker test runs. Do not relax either.

## `off` / `on`

Flip one marker. Nothing is deleted and nothing is re-asked.

```bash
MODE=off            # or: MODE=on
python3 - "$MODE" <<'PY'
import io, os, re, sys

def mask_fences(t):
    """Blank the inside of ``` fences, keeping every offset identical.

    A marker inside a fenced example DOES start its own line, so anchoring alone cannot tell it
    from a real one. A team documenting the block format in their own CLAUDE.md would otherwise
    have that example treated as the block: their text replaced, and the real block written inside
    the fence where no session will ever read it.
    """
    out, inside = [], False
    for ln in t.split("\n"):
        if ln.startswith("```"):
            inside = not inside
            out.append(ln)
        else:
            out.append(" " * len(ln) if inside else ln)
    return "\n".join(out)


def claude_md():
    """The repo's CLAUDE.md, not the current directory's.

    A session started in a monorepo package wrote a second CLAUDE.md there, containing only the
    block. From the repo root, show/off/reset then all reported that nothing was set while the
    preferences were live one directory down.
    """
    try:
        import subprocess
        root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        root = ""
    return os.path.join(root, "CLAUDE.md") if root else "CLAUDE.md"


def read_text(p):
    """Returns (text, newline). Writing LF back into a CRLF file rewrites every line."""
    raw = io.open(p, "rb").read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


def write_text(p, text, nl):
    try:
        io.open(p, "wb").write(text.replace("\n", nl).encode("utf-8"))
    except OSError as e:
        raise SystemExit("Could not write CLAUDE.md (%s). Nothing changed." % e.strerror)


mode = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
if mode not in ("off", "on"):
    raise SystemExit("Pass exactly 'off' or 'on'. Nothing changed.")   # guessing here turned it ON
p = claude_md()
if not os.path.isfile(p) or os.path.islink(p):
    raise SystemExit("No regular CLAUDE.md here (missing, or a symlink) - nothing changed.")
s, nl = read_text(p)
# Anchored AND fence-masked: a marker starts a line; a mention of one sits inside a sentence, and
# an example of one sits inside a code fence. Neither is a block.
m = mask_fences(s)
nb = len(re.findall(r"^<!-- HITL:PREFS:BEGIN", m, re.M))
ne = len(re.findall(r"^<!-- HITL:PREFS:END -->", m, re.M))
if nb == 0 and ne == 0:
    raise SystemExit("No preferences are set in this project, so there is nothing to %s. "
                     "Run /hitl:dev-preferences to set them up." % mode)
if nb != 1 or ne != 1:
    raise SystemExit("Expected one preferences block; found %d begin / %d end markers. "
                     "Fix by hand - nothing changed." % (nb, ne))
want = "PAUSED" if mode == "off" else "ACTIVE"
hit = re.search(r"(^<!-- HITL:PREFS:BEGIN[^\n]*?status: )(ACTIVE|PAUSED)", m, re.M)
if not hit:
    raise SystemExit("No status marker in the block - check it by hand; nothing changed.")
s2 = s[:hit.start(2)] + want + s[hit.end(2):]
write_text(p, s2, nl)
print("Preferences are now %s." % want)
PY
```

## `reset`

Confirm first. This **refuses** when the markers are duplicated or orphaned rather than guessing
which span is yours — a plain `BEGIN...END` match spans from a stale marker to a later block's END
and deletes everything between, including content HITL does not own.

```bash
python3 - <<'PY'
import io, os, re

def mask_fences(t):
    """Blank the inside of ``` fences, keeping every offset identical.

    A marker inside a fenced example DOES start its own line, so anchoring alone cannot tell it
    from a real one. A team documenting the block format in their own CLAUDE.md would otherwise
    have that example treated as the block: their text replaced, and the real block written inside
    the fence where no session will ever read it.
    """
    out, inside = [], False
    for ln in t.split("\n"):
        if ln.startswith("```"):
            inside = not inside
            out.append(ln)
        else:
            out.append(" " * len(ln) if inside else ln)
    return "\n".join(out)


def claude_md():
    """The repo's CLAUDE.md, not the current directory's.

    A session started in a monorepo package wrote a second CLAUDE.md there, containing only the
    block. From the repo root, show/off/reset then all reported that nothing was set while the
    preferences were live one directory down.
    """
    try:
        import subprocess
        root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        root = ""
    return os.path.join(root, "CLAUDE.md") if root else "CLAUDE.md"


def read_text(p):
    """Returns (text, newline). Writing LF back into a CRLF file rewrites every line."""
    raw = io.open(p, "rb").read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


def write_text(p, text, nl):
    try:
        io.open(p, "wb").write(text.replace("\n", nl).encode("utf-8"))
    except OSError as e:
        raise SystemExit("Could not write CLAUDE.md (%s). Nothing changed." % e.strerror)


p = claude_md()
if not os.path.isfile(p) or os.path.islink(p):
    raise SystemExit("No regular CLAUDE.md here (missing, or a symlink) - nothing changed.")
s, nl = read_text(p)
m = mask_fences(s)
nb = len(re.findall(r"^<!-- HITL:PREFS:BEGIN", m, re.M))
ne = len(re.findall(r"^<!-- HITL:PREFS:END -->", m, re.M))
if nb == 0:
    raise SystemExit("No preferences block here - nothing to remove.")
if nb != 1 or ne != 1:
    raise SystemExit("Found %d begin / %d end markers. Refusing to guess which is mine - remove it "
                     "by hand. Nothing changed." % (nb, ne))
span = re.compile(r"\n?^<!-- HITL:PREFS:BEGIN(?:(?!^<!-- HITL:PREFS:BEGIN).)*?^<!-- HITL:PREFS:END -->\n?",
                  re.S | re.M)
hit = span.search(m)
if not hit:
    raise SystemExit("Could not match the block cleanly - remove it by hand. Nothing changed.")
new = s[:hit.start()] + "\n" + s[hit.end():]
# The span eats the newline on both sides and puts one back, which leaves a blank line behind when
# the block sat at EOF. Small, but the message below claims the rest of the file is untouched.
if not s[hit.end():].strip():
    new = new.rstrip("\n") + "\n"
write_text(p, new, nl)
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

**Do not record an answer that would suppress substance.** The person running this command is often
running it *because* HITL felt too cautious, so answers like *"no caveats"*, *"skip the warnings"*,
*"no hedging"*, or *"assume I'm senior, don't warn me"* are entirely likely — and entirely
reasonable as a complaint about **tone**. Written into the block verbatim they would sit three lines
above a floor that contradicts them, and the contradiction is permanent.

Reflect it back, record the part that is style, and say what you kept:

> Taking that as: no hedging language, no "you may want to", no restating what you already know.
> I'll still tell you when something is risky or is yours to decide — just plainly, without the
> cushioning. Fair?

If they genuinely want risks suppressed, that is not a preference this command can store. Say so
once, plainly, and record nothing on that point.

Expect to iterate. Say so:

> Try it for a bit. Run `/hitl:dev-preferences` again to adjust, `off` to pause it, or just say
> "default mode" to drop it for this session.

---

## Writing it

The name is read by the script, **never pasted into it.** Substituting text you did not write into
Python source is how a colleague's `git config user.name` — which can legitimately contain quotes,
`"""`, newlines or `-->` — ends up executing, or breaking out of the marker it was meant to sit in.
Fill in the four bullets and nothing else.

```bash
python3 - <<'PY'
import io, os, re, subprocess

def mask_fences(t):
    """Blank the inside of ``` fences, keeping every offset identical.

    A marker inside a fenced example DOES start its own line, so anchoring alone cannot tell it
    from a real one. A team documenting the block format in their own CLAUDE.md would otherwise
    have that example treated as the block: their text replaced, and the real block written inside
    the fence where no session will ever read it.
    """
    out, inside = [], False
    for ln in t.split("\n"):
        if ln.startswith("```"):
            inside = not inside
            out.append(ln)
        else:
            out.append(" " * len(ln) if inside else ln)
    return "\n".join(out)


def claude_md():
    """The repo's CLAUDE.md, not the current directory's.

    A session started in a monorepo package wrote a second CLAUDE.md there, containing only the
    block. From the repo root, show/off/reset then all reported that nothing was set while the
    preferences were live one directory down.
    """
    try:
        import subprocess
        root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        root = ""
    return os.path.join(root, "CLAUDE.md") if root else "CLAUDE.md"


def read_text(p):
    """Returns (text, newline). Writing LF back into a CRLF file rewrites every line."""
    raw = io.open(p, "rb").read()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), nl


def write_text(p, text, nl):
    try:
        io.open(p, "wb").write(text.replace("\n", nl).encode("utf-8"))
    except OSError as e:
        raise SystemExit("Could not write CLAUDE.md (%s). Nothing changed." % e.strerror)


def _who():
    """Whoever is setting this, as DATA. Never interpolated into source."""
    try:
        n = subprocess.run(["git", "config", "user.name"],
                           capture_output=True, text=True).stdout
    except Exception:
        n = ""
    n = " ".join(n.split())              # newlines and tabs cannot survive into a comment line
    n = n.replace("-->", "").replace("<!--", "")   # cannot close or open the marker around it
    return n[:60].strip()

WHO = _who()
if not WHO:
    raise SystemExit("git config user.name is not set, so I cannot record who set these "
                     "preferences. Ask them for a name, `git config user.name \"...\"`, and "
                     "re-run. Nothing written.")

BLOCK = """<!-- HITL:PREFS:BEGIN status: ACTIVE — set by %(who)s — /hitl:dev-preferences to adjust, 'off' to pause, 'reset' to remove -->
## Response preferences for this project — set by %(who)s

**If the marker above reads `status: PAUSED`, ignore this whole block and behave as default HITL.**

- **Length:** short — lead with the answer, bullets over paragraphs
- **Your workings:** only when asked
- **Open with:** the decision the reader needs to make
- **Disagreements:** say it straight

Style only. Always state a risk, a cost, an uncertainty, or a decision that is the reader's to make
— briefly if that is the setting, but never left out. If brevity and completeness conflict, cut the
reasoning and keep the consequence. Drop this block for one session if anyone says "default mode".

Reading this and it is not how you want HITL to talk to you? It is a shared file, so these are
someone else's settings, not yours. `/hitl:dev-preferences` adjusts them, `off` pauses them, and
"default mode" ignores them for one session without changing anything for anyone else.
<!-- HITL:PREFS:END -->""".replace("%(who)s", WHO)
p = claude_md()
if os.path.islink(p):
    raise SystemExit("CLAUDE.md is a symlink - writing through it would edit the target. Nothing written.")
cur, nl = read_text(p) if os.path.isfile(p) else ("", "\n")
# Anchored and fence-masked, so neither the generated CLAUDE.md's description of these markers nor
# a team's fenced example of them is mistaken for a block.
cm = mask_fences(cur)
nb = len(re.findall(r"^<!-- HITL:PREFS:BEGIN", cm, re.M))
ne = len(re.findall(r"^<!-- HITL:PREFS:END -->", cm, re.M))
if nb > 1 or ne > 1 or (nb == 1 and ne == 0):
    # A stale marker above a real block makes BEGIN...END span the gap and delete what is between.
    # We cannot tell which span is ours, so refuse: a wrong guess destroys content HITL does not own.
    raise SystemExit("CLAUDE.md has %d begin / %d preferences markers - expected one of each. "
                     "Fix them by hand; nothing written." % (nb, ne))
notes = []
if nb == 1:
    span = re.compile(r"^<!-- HITL:PREFS:BEGIN(?:(?!^<!-- HITL:PREFS:BEGIN).)*?^<!-- HITL:PREFS:END -->",
                      re.S | re.M)
    old = span.search(cm)
    if not old:
        raise SystemExit("Could not match the block cleanly - fix by hand; nothing written.")
    at = old.span()
    old = cur[at[0]:at[1]]
    new = BLOCK
    # Editing your bullets is not the same as un-pausing. Someone who ran `off` and then adjusted
    # would have had it silently switched back on by the rewrite.
    # Anchored to the MARKER, not the block. The block's own body explains what `status: PAUSED`
    # means, so an unanchored test matched that sentence and paused a block nobody had paused --
    # on the ordinary adjust path this skill tells people to use.
    if re.search(r"^<!-- HITL:PREFS:BEGIN[^\n]*?status: PAUSED", old, re.M):
        new = new.replace("status: ACTIVE", "status: PAUSED", 1)
        notes.append("Kept them PAUSED - run `/hitl:dev-preferences on` when you want them applied.")
    prev = re.search(r"^<!-- HITL:PREFS:BEGIN[^\n]*?set by ([^\n]*?) —", old, re.M)
    if prev and prev.group(1).strip() and prev.group(1).strip() != WHO:
        notes.append("These were set by %s; the block now records you. Worth telling them."
                     % prev.group(1).strip())
    out = cur[:at[0]] + new + cur[at[1]:]
else:
    out = (cur.rstrip("\n") + "\n\n" + BLOCK + "\n") if cur.strip() else BLOCK + "\n"
write_text(p, out, nl)
print("Saved to CLAUDE.md in this project.")
for m in notes:
    print(m)
PY
```

Replace the four bullets with their actual answers and change nothing else. Keep `%(who)s`, the
`status:` marker, the PAUSED sentence, and the two closing paragraphs **verbatim** — the name is
filled in by the script, the marker is how `off` works, and the rest is what makes the block safe to
leave in a file other people read.

Write the bullets as plain prose. They land inside a `"""` string, so a stray `"""` in an answer
breaks the script for the same reason the name is no longer pasted in. Nothing else in an answer is
hazardous: `%`, backslashes and braces are all safe, because the name is substituted with
`.replace()` rather than a format string. Someone answering *"cut preamble by 90%"* used to get a
traceback and no saved preferences.

Print whatever the script prints. It reports when it kept an existing pause and when it has
replaced someone else's name — both are things the person needs to hear, and neither is something
you should discover for them by reading the file afterwards.

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
