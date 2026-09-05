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
> instead: that one is yours and HITL will not touch it.

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

One script, five modes: `show`, `off`, `on`, `reset`, `write`. It used to be three near-identical
copies, which is how the repo-root fix, the fence fix and the traceback fix each reached some
commands and not others. Every fix now lands once.

**Every marker test anchors to the start of a line and masks fenced regions first. Both are
load-bearing.** A real marker begins its own line, so counting unanchored strings makes ordinary
prose look like a block. And a marker inside a fence also begins its line, so a team documenting the
block format would have that example treated as the real block. Do not relax either.

```bash
MODE=show          # show | off | on | reset | write
# For `write`, pass the four answers as arguments. They are DATA: never paste them into the script.
# A backslash in an answer would otherwise be read as a Python escape and
# silently mangle the saved block -- the same defect the author's name had.
python3 - "$MODE" "$LENGTH" "$WORKINGS" "$OPEN_WITH" "$DISAGREEMENTS" "$TONE" <<'PY'
import io, os, re, subprocess, sys

# ONE script, five modes. These were three near-identical copies, and every copy was a place a fix
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
    """Returns (text, newline) with the text EXACTLY as on disk.

    It used to normalise CRLF to LF and convert the whole file back on write, so a single stray
    CRLF line turned every other line into CRLF -- a whole-file diff on a committed file, under
    a message saying the rest of it was untouched. Lines we do not edit are now never rewritten;
    `newline` is only the dominant ending, used for the block we insert.
    """
    try:
        raw = io.open(p, "rb").read()
    except OSError as e:
        raise SystemExit("Could not read CLAUDE.md (%s). Nothing changed." % e.strerror)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise SystemExit("CLAUDE.md is not valid UTF-8, so I will not rewrite it. Nothing changed.")
    if "\r" in text and "\n" not in text:
        raise SystemExit("CLAUDE.md uses classic-Mac (CR) line endings, which I cannot parse "
                         "safely. Convert it to LF or CRLF first; nothing changed.")
    crlf = text.count("\r\n")
    nl = "\r\n" if crlf and crlf * 2 >= text.count("\n") else "\n"
    return text, nl


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
        m = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", ln)
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
    # `text` already carries the file's own endings; nl was applied to the inserted block only.
    try:
        io.open(p, "wb").write(text.encode("utf-8"))
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
    # Blocks written before 2.12.0 delimit the name with an em dash; newer ones with a comma.
    hit = re.search(r"^<!-- HITL:PREFS:BEGIN[^\n]*?set by (.*?)(?: \u2014|,) /hitl:dev-preferences", text, re.M)
    return hit.group(1).strip() if hit else ""


if MODE == "show":
    if nb > 1 or ne > 1:
        print("CLAUDE.md has %d begin / %d end markers, so more than one preferences block. Showing "
              "the first; fix the file by hand, the other modes refuse to touch it." % (nb, ne))
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
    if not SPAN.search(m):
        raise SystemExit("The markers are present but not in order (END before BEGIN), so I cannot "
                         "tell where the block is. Fix it by hand; nothing changed.")
    want = "PAUSED" if MODE == "off" else "ACTIVE"
    hit = re.search(r"(^<!-- HITL:PREFS:BEGIN status: )(ACTIVE|PAUSED)", m, re.M)
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
    out = cur[:hit.start()] + (nl if cur[:hit.start()] and cur[hit.end():] else "") + cur[hit.end():]
    # The span eats the newline on both sides and puts one back, which leaves a blank line behind
    # when the block sat at EOF, while the message claims the rest of the file is untouched.
    if not cur[hit.end():].strip():
        out = out.rstrip("\r\n") + nl
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
    while "-->" in n or "<!--" in n:              # loop: one pass can CREATE what it removed
        n = n.replace("-->", "").replace("<!--", "")   # ('---->>' collapses to '-->')
    n = n.replace("\u2014", "-")                    # the marker delimits the name with em dashes
    return n[:60].strip()

WHO = _who()
if not WHO:
    raise SystemExit("git config user.name is not set, so I cannot record who set these "
                     "preferences. Ask them for a name, `git config user.name \"...\"`, and "
                     "re-run. Nothing written.")


BLOCK = """<!-- HITL:PREFS:BEGIN status: ACTIVE, set by %(who)s, /hitl:dev-preferences to adjust, 'off' to pause, 'reset' to remove -->
## Response preferences for this project, set by %(who)s

**If the marker above reads `status: PAUSED`, ignore this whole block and behave as default HITL.**

- **Length:** %(length)s
- **Your workings:** %(workings)s
- **Open with:** %(open_with)s
- **Disagreements:** %(disagreements)s%(tone)s

Style only. Always state a risk, a cost, an uncertainty, or a decision that is the reader's to make,
briefly if that is the setting, but never left out. An icon is never the only thing carrying a
warning: drop every glyph and the sentences must still say the same things. If brevity and
completeness conflict, cut the reasoning and keep the consequence. Drop this block for one session if anyone says "default mode".

**If the person in this session is not %(who)s, say so once, early, in your own words:** that you
are following %(who)s's preferences from this repo's `CLAUDE.md`, and that `/hitl:dev-preferences`
adjusts them, `off` pauses them, or "default mode" drops them for this session only. Say it once,
briefly, then get on with the work. Someone wondering why you are suddenly terse should not have to
open a file to find out.

Reading this and it is not how you want HITL to talk to you? It is a shared file, so these are
someone else's settings, not yours. `/hitl:dev-preferences` adjusts them, `off` pauses them, and
"default mode" ignores them for one session without changing anything for anyone else.
<!-- HITL:PREFS:END -->"""
ANS = {"who": WHO}
for i, k in enumerate(("length", "workings", "open_with", "disagreements"), start=2):
    v = " ".join((sys.argv[i] if len(sys.argv) > i else "").split())
    if not v:
        raise SystemExit("Missing the %s answer. Pass all four; nothing written." % k)
    ANS[k] = v.replace("-->", "").replace("<!--", "")
_t = " ".join((sys.argv[6] if len(sys.argv) > 6 else "").split())
ANS["tone"] = "\n- **Tone:** " + (_t.replace("-->", "").replace("<!--", "") if _t
                               else "plain English, short: no filler, no em dashes, numbers in a table (HITL's plain-english rule)")
for k, v in ANS.items():
    BLOCK = BLOCK.replace("%(" + k + ")s", v)   # substitution, never formatting

BLOCK = BLOCK.replace("\n", nl)   # the inserted text adopts the file's endings; the rest is untouched

if nb > 1 or ne > 1 or (nb == 1 and ne == 0) or (nb == 0 and ne == 1):
    # A stale marker above a real block makes BEGIN...END span the gap and delete what is between.
    # We cannot tell which span is ours, so refuse: a wrong guess destroys content HITL does not own.
    raise SystemExit("CLAUDE.md has %d begin / %d end preferences markers - expected one of each. "
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
    if re.search(r"^<!-- HITL:PREFS:BEGIN status: PAUSED", old, re.M):
        new = new.replace("status: ACTIVE", "status: PAUSED", 1)
        notes.append("Kept them PAUSED - run `/hitl:dev-preferences on` when you want them applied.")
    prev = owner_of(old)
    if prev and prev != WHO:
        notes.append("These were set by %s; the block now records you. Worth telling them." % prev)
    out = cur[:hit.start()] + new + cur[hit.end():]
else:
    out = (cur.rstrip("\r\n") + nl + nl + BLOCK + nl) if cur.strip() else BLOCK + nl
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
> 1. **Length**: short (bullets, answer first) / standard / full?
> 2. **My workings**: what I did and how I got there: only when you ask / a line or two / all of it
> 3. **Open with**: the decision you need to make, the result, or the context?
> 4. **Disagreements**: straight, or eased in? *(I'll still disagree either way: this is only how it opens.)*
>
> Anything else? "plain text, no icons", "tables over prose", "I know this domain, skip the primer".

HITL marks state with a small set of icons: 🔒 paused, 🧭 where you are, ⚠️ irreversible, ✅ done,
🔄 working, 📝 saved. *"Plain text"* tells **Claude** to drop them from what it writes. It does not
change the hooks: those six live as literal characters in shell scripts that read no configuration,
so a blocked edit still arrives with its 🔒. Either way the sentence carries the warning and the
icon only makes it findable, so nothing is lost by dropping them.

Take partial answers; default the rest and say which you assumed. Then **show the block you are
about to write and ask before writing.**

**Do not record an answer that would suppress substance.** The person running this command is often
running it *because* HITL felt too cautious, so answers like *"no caveats"*, *"skip the warnings"*,
*"no hedging"*, or *"assume I'm senior, don't warn me"* are entirely likely — and entirely
reasonable as a complaint about **tone**. Written into the block verbatim they would sit three lines
above a floor that contradicts them, and the contradiction is permanent.

Reflect it back, record the part that is style, and say what you kept:

> Taking that as: no hedging language, no "you may want to", no restating what you already know.
> I'll still tell you when something is risky or is yours to decide: just plainly, without the
> cushioning. Fair?

If they genuinely want risks suppressed, that is not a preference this command can store. Say so
once, plainly, and record nothing on that point.

Expect to iterate. Say so:

> Try it for a bit. Run `/hitl:dev-preferences` again to adjust, `off` to pause it, or just say
> "default mode" to drop it for this session.

---

## Writing it

**Nothing the person said gets pasted into the script. Not their answers, not their name.** Both are
passed in as arguments, because text substituted into Python source is read as Python: a `%` used to
crash the write, a Windows path used to save with its backslashes swallowed as escape codes, and a
`git config user.name` containing quotes or `"""` could break out of the marker entirely.

So: set `LENGTH`, `WORKINGS`, `OPEN_WITH`, `DISAGREEMENTS` and optionally `TONE` to what they told
you, then run the script with `write`. Quotes, `%`, backslashes and braces all survive verbatim that
way. **Do not edit the block literal to insert their answers** — that is the path all of the above
came back through.

Everything else in the block stays **verbatim**: the `status:` marker is how `off` works, and the
PAUSED sentence, the attribution and the two closing paragraphs are what make the block safe to
leave in a file other people read.

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

> Want me to keep to that? `/hitl:dev-preferences`: four questions, this project only, and you can
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
