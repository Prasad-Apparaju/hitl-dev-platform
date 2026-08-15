---
description: Set up how HITL talks to you — length, whether it narrates its process, how it opens a disagreement. Asks a few questions and writes the answers into your own user-level CLAUDE.md, so they apply in every project, not just this one. Run it when HITL feels too verbose, too terse, or too cautious.
argument-hint: "optional — 'show' to see current settings, 'reset' to remove them"
disable-model-invocation: true
---

# Preferences

**Input:** $ARGUMENTS

HITL is wordy by default because it does not know you. This fixes that in about a minute.

Your answers go into **your own** `~/.claude/CLAUDE.md`, not into this repo. That file already
applies to every project you work in, so the settings follow you — and they are yours to edit or
delete by hand at any time. HITL is doing the setup, not owning the result.

---

## `show` — what is set now

```bash
sed -n '/<!-- HITL:PREFS:BEGIN/,/<!-- HITL:PREFS:END -->/p' ~/.claude/CLAUDE.md 2>/dev/null \
  || echo "No HITL preferences set."
```

Print it and stop.

## `reset` — remove them

Confirm first, then strip the marked block and leave the rest of the file untouched:

```bash
python3 - <<'PY'
import io, os, re
p = os.path.expanduser("~/.claude/CLAUDE.md")
if not os.path.isfile(p):
    raise SystemExit("No ~/.claude/CLAUDE.md — nothing to reset.")
s = io.open(p, encoding="utf-8").read()
new, n = re.subn(r"\n?<!-- HITL:PREFS:BEGIN.*?<!-- HITL:PREFS:END -->\n?", "\n", s, flags=re.S)
if not n:
    raise SystemExit("No HITL preferences block found — nothing removed.")
io.open(p, "w", encoding="utf-8").write(new)
print("Removed. The rest of your CLAUDE.md is untouched.")
PY
```

---

## The interview

**Four questions. Ask them in one message, not one at a time** — it would be absurd to run a long
interrogation about someone's preference for brevity. Offer the options, let them answer in any
form, and accept "whatever" for any of them.

> A few quick ones, and I'll remember the answers for every project:
>
> 1. **Length** — short (bullets, answer first) / standard / full?
> 2. **My workings** — do you want what I did and how I got there? Only when you ask / a line or two / all of it
> 3. **Opening line** — the decision you need to make, the result, or the context first?
> 4. **Disagreements** — say it straight, or lead in gently? *(I'll still disagree either way — this is only how it opens.)*
>
> Anything else? e.g. "no emoji", "tables over prose", "I know this domain, skip the primer".

If they answer only some, use the defaults for the rest and say which you assumed.

**Then show them what you are about to write and ask before writing.** This edits a file in their
home directory that governs every project — never do it silently, even though it is small.

---

## Writing it

Build the block from their answers and write it with the same upsert HITL uses for project
`CLAUDE.md` files — it creates, appends, or refreshes in place, and never disturbs anything else in
the file:

```bash
BLOCK=$(mktemp)
cat > "$BLOCK" <<'EOF'
<!-- HITL:PREFS:BEGIN — written by /hitl:dev-preferences. Edit freely; re-running rewrites this block. -->
## How I like responses

- **Length:** short — lead with the answer, bullets over paragraphs
- **Your workings:** only when I ask
- **Open with:** the decision I need to make
- **Disagreements:** say it straight

Style only. Always tell me a risk, a cost, an uncertainty, or a decision that is mine — briefly if
that is the setting, but never omitted. If brevity and completeness conflict, cut the reasoning and
keep the consequence.
<!-- HITL:PREFS:END -->
EOF

SCRIPT="${CLAUDE_PLUGIN_ROOT}/shared/tools/hitl-onboarding/ensure_claude_block.py"
python3 - "$SCRIPT" "$BLOCK" <<'PY'
import io, os, re, subprocess, sys
script, block = sys.argv[1], sys.argv[2]
dest = os.path.expanduser("~/.claude/CLAUDE.md")
body = io.open(block, encoding="utf-8").read()
# Same marker-delimited upsert, different marker pair so it never collides with the project block.
cur = io.open(dest, encoding="utf-8").read() if os.path.isfile(dest) else ""
if "<!-- HITL:PREFS:BEGIN" in cur:
    if "<!-- HITL:PREFS:END -->" not in cur:
        raise SystemExit("Your preferences block is truncated — fix or delete it by hand; nothing written.")
    out = re.sub(r"<!-- HITL:PREFS:BEGIN.*?<!-- HITL:PREFS:END -->", body.rstrip("\n"), cur, flags=re.S)
else:
    out = (cur.rstrip("\n") + "\n\n" + body) if cur.strip() else body
io.open(dest, "w", encoding="utf-8").write(out)
print("Saved to ~/.claude/CLAUDE.md")
PY
rm -f "$BLOCK"
```

Adjust the bullets to match their actual answers. Keep the closing paragraph **verbatim** — it is
the floor, and it is the reason this is safe to set and forget.

---

## The floor, and why it is in the file rather than here

A preference governs **form, never substance**. Someone who wants three bullets still needs to know
that a migration can destroy their work, that a change is irreversible, that you are guessing, or
that something is theirs to decide.

That paragraph goes **into their CLAUDE.md**, not just into this skill, because the file is what
future sessions read. A floor that lives only in the setup command is a floor that stops existing
the moment setup finishes.

---

## When to offer this

Do not advertise it. Offer once, when someone tells you something is wrong with how you are talking:

- "too long", "just give me the answer", "skip the detail"
- "you don't need to explain all that"
- they ask for more depth twice in a row

> Want me to remember that? `/hitl:dev-preferences` — four questions, applies everywhere, and you
> can undo it with `reset`.

Once per session. If they say no, drop it and store nothing.

**Never write preferences from inference.** Two terse messages are not consent to a stored profile
of how someone likes to be spoken to.

---

## Related

- `/hitl:dev-draft-for <person>` — writing a message **to** someone else, using their profile.
  Different thing: that is about your audience, this is about you.
- `${CLAUDE_PLUGIN_ROOT}/shared/personas.md` — the rules both share.
