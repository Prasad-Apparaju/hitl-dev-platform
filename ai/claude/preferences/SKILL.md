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

`off`, `on` and `reset` all edit a **committed** file, so they change things for the whole team, not
just for you — and the settings may be someone else's. Each one prints whose they are; pass that on
rather than swallowing it. If you only want them gone for yourself, right now, say *"default mode"*
instead and nothing is written at all.

**Turning it off for one session only** needs no command — say *"default mode"* or *"ignore my
preferences"* and behave as HITL does out of the box for the rest of the session. Do not edit the
file for a temporary request. Mention this once when you first set the preferences up, so they know
the escape exists.

---

## The script

One script, four modes: `show`, `off`, `on`, `reset`, `write`. It used to be three near-identical
copies, which is how the repo-root fix, the fence fix and the traceback fix each reached some
commands and not others. Every fix now lands once.

**Every marker test anchors to the start of a line and masks fenced regions first. Both are
load-bearing.** A real marker begins its own line, so counting unanchored strings makes ordinary
prose look like a block. And a marker inside a fence also begins its line, so a team documenting the
block format would have that example treated as the real block. Do not relax either.

```bash
MODE=show          # show | off | on | reset | write
python3 - "$MODE" <<'PY'
import io, os, re, subprocess, sys

# ONE script, four modes. These were three near-identical copies, and every copy was a place a fix
# could fail to reach: the repo-root fix, the fence fix and the traceback fix each landed in some
# copies and not others, and each gap was a separate reported defect. Shared logic lives here once.
MODE = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
if MODE not in ("show", "off", "on", "reset", "write"):
    raise SystemExit("Pass one of: show, off, on, reset, write. Nothing changed.")

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
    try:
        raw = io.open(p, "rb").read()
    except OSError as e:
        raise SystemExit("Could not read CLAUDE.md (%s). Nothing changed." % e.strerror)
    nl = "\r\n" if b"\r\n" in raw else "\n"
    try:
        return raw.decode("utf-8").replace("\r\n", "\n"), nl
    except UnicodeDecodeError:
        raise SystemExit("CLAUDE.md is not valid UTF-8, so I will not rewrite it. Nothing changed.")


def mask_fences(t):
    """Blank the inside of fenced blocks, keeping every offset identical.

    Returns (masked_text, unterminated). A marker inside a fenced example DOES start its own line,
    so anchoring alone cannot tell it from a real one.

    The first version just toggled on any line opening a fence, which broke two ways: an odd
    number of such lines inverted the whole file so the real block looked masked and a SECOND block
    got written, and tilde fences were not recognised at all. Match the opening fence character and
    length, close only on the same character at least as long, and report an unterminated fence
    rather than guessing what the rest of the file is.
    """
    out, fence = [], None
    unterminated = False
    for ln in t.split("\n"):
        m = re.match(r"^(`{3,}|~{3,})(.*)$", ln)
        if fence is None:
            if m:
                fence = m.group(1)
            out.append(ln)
        elif m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
                and not m.group(2).strip():
            fence = None
            out.append(ln)
        else:
            out.append(" " * len(ln))
    if fence is not None:
        unterminated = True
    return "\n".join(out), unterminated


def write_text(p, text, nl):
    try:
        io.open(p, "wb").write(text.replace("\n", nl).encode("utf-8"))
    except OSError as e:
        raise SystemExit("Could not write CLAUDE.md (%s). Nothing changed." % e.strerror)


p = claude_md()
if os.path.islink(p):
    raise SystemExit("CLAUDE.md is a symlink - writing through it would edit the target. "
                     "Nothing changed.")
if not os.path.isfile(p):
    if MODE == "show":
        print("No HITL preferences set in this project.")   # an answer, not an error
        raise SystemExit(0)
    if MODE != "write":
        raise SystemExit("No regular CLAUDE.md here - nothing changed.")

cur, nl = read_text(p) if os.path.isfile(p) else ("", "\n")
m, unterminated = mask_fences(cur)
if unterminated:
    raise SystemExit("CLAUDE.md has an unterminated code fence, so I cannot tell which lines "
                     "are real markers. Close the fence by hand; nothing changed.")

# Anchored AND fence-masked: a real marker starts a line; a mention of one sits inside a sentence,
# and an example of one sits inside a code fence. Neither is a block.
nb = len(re.findall(r"^<!-- HITL:PREFS:BEGIN", m, re.M))
ne = len(re.findall(r"^<!-- HITL:PREFS:END -->", m, re.M))
SPAN = re.compile(r"^<!-- HITL:PREFS:BEGIN(?:(?!^<!-- HITL:PREFS:BEGIN).)*?^<!-- HITL:PREFS:END -->",
                  re.S | re.M)


def owner_of(text):
    hit = re.search(r"^<!-- HITL:PREFS:BEGIN[^\n]*?set by (.*?) \u2014", text, re.M)
    return hit.group(1).strip() if hit else ""


if MODE == "show":
    hit = SPAN.search(m)
    if not hit:
        print("No HITL preferences set in this project.")
        raise SystemExit(0)
    print(cur[hit.start():hit.end()])
    raise SystemExit(0)

if MODE in ("off", "on"):
    if nb == 0 and ne == 0:
        raise SystemExit("No preferences are set in this project, so there is nothing to %s. "
                         "Run /hitl:dev-preferences to set them up." % MODE)
    if nb != 1 or ne != 1:
        raise SystemExit("Expected one preferences block; found %d begin / %d end markers. "
                         "Fix by hand - nothing changed." % (nb, ne))
    want = "PAUSED" if MODE == "off" else "ACTIVE"
    hit = re.search(r"(^<!-- HITL:PREFS:BEGIN[^\n]*?status: )(ACTIVE|PAUSED)", m, re.M)
    if not hit:
        raise SystemExit("No status marker in the block - check it by hand; nothing changed.")
    write_text(p, cur[:hit.start(2)] + want + cur[hit.end(2):], nl)
    print("Preferences are now %s." % want)
    who = owner_of(m)
    if who:
        print("These are %s's settings, and CLAUDE.md is committed - this changes them for the "
              "whole team. To drop them just for yourself, say \"default mode\" instead." % who)
    raise SystemExit(0)

if MODE == "reset":
    if nb == 0:
        raise SystemExit("No preferences block here - nothing to remove.")
    if nb != 1 or ne != 1:
        raise SystemExit("Found %d begin / %d end markers. Refusing to guess which is mine - "
                         "remove it by hand. Nothing changed." % (nb, ne))
    hit = re.search(r"\n?" + SPAN.pattern + r"\n?", m, re.S | re.M)
    if not hit:
        raise SystemExit("Could not match the block cleanly - remove it by hand. Nothing changed.")
    who = owner_of(m)
    out = cur[:hit.start()] + "\n" + cur[hit.end():]
    # The span eats the newline on both sides and puts one back, which leaves a blank line behind
    # when the block sat at EOF, while the message claims the rest of the file is untouched.
    if not cur[hit.end():].strip():
        out = out.rstrip("\n") + "\n"
    write_text(p, out, nl)
    print("Removed. The rest of CLAUDE.md is untouched.")
    if who:
        print("Those were %s's settings and CLAUDE.md is committed, so they are gone for everyone. "
              "Worth telling them." % who)
    raise SystemExit(0)

# MODE == "write"
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

**If the person in this session is not %(who)s, say so once, early, in your own words:** that you
are following %(who)s's preferences from this repo's `CLAUDE.md`, and that `/hitl:dev-preferences`
adjusts them, `off` pauses them, or "default mode" drops them for this session only. Say it once,
briefly, then get on with the work. Someone wondering why you are suddenly terse should not have to
open a file to find out.

Reading this and it is not how you want HITL to talk to you? It is a shared file, so these are
someone else's settings, not yours. `/hitl:dev-preferences` adjusts them, `off` pauses them, and
"default mode" ignores them for one session without changing anything for anyone else.
<!-- HITL:PREFS:END -->""".replace("%(who)s", WHO)

if nb > 1 or ne > 1 or (nb == 1 and ne == 0) or (nb == 0 and ne == 1):
    # A stale marker above a real block makes BEGIN...END span the gap and delete what is between.
    # We cannot tell which span is ours, so refuse: a wrong guess destroys content HITL does not own.
    raise SystemExit("CLAUDE.md has %d begin / %d preferences markers - expected one of each. "
                     "Fix them by hand; nothing written." % (nb, ne))
notes = []
if nb == 1:
    hit = SPAN.search(m)
    if not hit:
        raise SystemExit("Could not match the block cleanly - fix by hand; nothing written.")
    old, new = cur[hit.start():hit.end()], BLOCK
    # Editing your bullets is not un-pausing. Anchored to the MARKER: the block's own body explains
    # what `status: PAUSED` means, so an unanchored test matched that sentence and paused a block
    # nobody had paused, on the ordinary adjust path this skill tells people to use.
    if re.search(r"^<!-- HITL:PREFS:BEGIN[^\n]*?status: PAUSED", old, re.M):
        new = new.replace("status: ACTIVE", "status: PAUSED", 1)
        notes.append("Kept them PAUSED - run `/hitl:dev-preferences on` when you want them applied.")
    prev = owner_of(old)
    if prev and prev != WHO:
        notes.append("These were set by %s; the block now records you. Worth telling them." % prev)
    out = cur[:hit.start()] + new + cur[hit.end():]
else:
    out = (cur.rstrip("\n") + "\n\n" + BLOCK + "\n") if cur.strip() else BLOCK + "\n"
write_text(p, out, nl)
print("Saved to CLAUDE.md in this project.")
for n in notes:
    print(n)
PY
```

## `show`

Run it with `show`. Prints the block and nothing else, or says none is set.

## `off` / `on`

Run it with `off` or `on`. Flips one marker; nothing is deleted and nothing is re-asked. It names
whose settings they are, because the file is committed and they may not be yours.

## `reset`

Confirm first, then run it with `reset`. It **refuses** when the markers are duplicated or orphaned
rather than guessing which span is yours: a plain BEGIN...END match spans from a stale marker to a
later block's END and deletes everything between, including content HITL does not own.

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


Run the script with `write`.


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
