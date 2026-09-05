# Personas — writing to someone else

**How HITL helps you write to someone else.** A PR comment for your CEO reads differently from the
same update to the engineer who will implement it.

Profiles live in `.hitl/people/<slug>.yaml`.

**This is not about how HITL talks to you.** That is `/hitl:dev-preferences`, which writes a block
in this project's own `CLAUDE.md`. HITL manages projects; it does not write to anyone's machine-wide
config on its own initiative.

---

## The floor — read this before anything else

**A persona shapes form. It never changes substance.**

Style is negotiable: length, ordering, bullets versus prose, how much of the reasoning you show.
These are not:

- **A risk, a cost, or a consequence.** "Prefers short" never becomes "omit the part where this
  deletes their files." The shortest true version still contains the warning.
- **A disagreement.** If the plan is wrong, say so. A profile that reads "doesn't like pushback"
  describes someone who needs it delivered well, not withheld — see `challenge-stance.md`.
- **An uncertainty.** "Confident tone" is not licence to state a guess as fact.
- **Anything they must decide.** A decision that is theirs gets surfaced whatever the preferred
  format.

When brevity and completeness conflict, completeness wins and you compress the *rest*. There is
always a short way to say something important; there is no acceptable way to leave it out.

**Outbound has one more rule.** Writing for an audience is not managing an audience. Shaping a
message so it lands is good practice; shaping it so someone approves something they would not
approve fully informed is not, and a persona file makes that easy enough to do by accident that it
has to be said. If you find yourself choosing an emphasis because of how the reader will *react*
rather than what they need to *know*, stop.

---

## Offering it

Never advertise it, and never build one in the background. Offer once, at the moment it would
obviously have helped:

- You just drafted something for a named person and there was no profile — ask *after* the draft,
  not before, so they are agreeing to something they have seen.
- They react to a draft: *"too long for him"*, *"he'll want the numbers"*. That is the profile,
  said out loud.

> Want me to save that for Kishor? Next time I'd draft it that way without asking.

If they agree, **read `${CLAUDE_PLUGIN_ROOT}/shared/templates/persona.yaml` and fill it in** — do
not invent a file. The field set, the slug convention, and the wording discipline all live there,
and a profile written from memory gets none of them. Set `authored_by` to whoever is actually
saving it; it is `self` only when the subject wrote or approved it.

Once. If they decline, drop it and store nothing.

**Never infer a profile silently.** A stored description of how a colleague thinks, written from a
couple of offhand remarks and never seen by them, is the thing to avoid here.

## Where they live, and who can undo them

**Local by default — check it, do not assume it.** A description of how a colleague thinks does not
belong in a PR diff, in code review, or in git history where deleting the file later does not
remove it. Onboarding adds the ignore rule, but a project that upgraded rather than onboarded may
not have it, someone may have removed it, and this may not be a HITL project at all.

So **before writing a profile, confirm it is actually ignored** — and check the result rather than
assuming it. `.gitignore` has no effect on a file git already tracks, and outside a repo
`git check-ignore` fails in a way that looks like "not ignored", so appending a rule and announcing
success is exactly the false assurance this section exists to prevent.

```bash
# Resolve to the repo, not the current directory: a session started in a subdirectory otherwise
# gets its own .hitl/people/, invisible from the root, and draft-for offers to create a second one.
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
mkdir -p .hitl/people
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "NOT A GIT REPO: nothing here can make this file local. Say so before writing it."
else
  git check-ignore -q .hitl/people/ 2>/dev/null || \
    printf '\n# HITL persona profiles — descriptions of people. Local unless your team decides otherwise.\n.hitl/people/\n' >> .gitignore
  # Re-check. This is the line that turns a claim into a fact.
  if git check-ignore -q .hitl/people/ 2>/dev/null; then
    echo "OK: .hitl/people/ is ignored; a profile written here stays local."
  else
    echo "COULD NOT make .hitl/people/ ignored. Do not tell them it is local."
  fi
  TRACKED=$(git ls-files '.hitl/people/' 2>/dev/null)
  [ -n "$TRACKED" ] && {
    echo "ALREADY TRACKED: the ignore rule does not cover these, and they are in git history:"
    echo "$TRACKED" | sed 's/^/  /'
  }
fi
```

Report what it actually printed. If it says NOT A GIT REPO, COULD NOT, or ALREADY TRACKED, **stop
and tell the person before writing anything** — those are the cases where the promise of locality
is false, and they are the cases most likely to matter.

Telling someone a file is local when it is about to be committed is worse than not having said
anything, because they will not check. If you cannot make it ignored — no `.gitignore`, not a git
repo, the rule refused — **say so before you write, and let them decide whether to write it at
all.**

Sharing one with the team is a deliberate act: remove the ignore line, and tell the person whose
profile it is.

**The subject's file is on someone else's machine, and that is the whole problem.** Be honest about
what this is: a profile is local, so the person it describes cannot list it, read it, or delete it.
Everything below runs in the *sender's* session. So these are not rights the subject holds — they
are obligations on whoever is holding the file, and they are only worth anything if that person
acts on them. Say yes immediately when asked:

```bash
ls .hitl/people/                      # what profiles exist
cat .hitl/people/<name>.yaml          # read one
rm .hitl/people/<name>.yaml           # remove it
```

If someone asks what HITL knows about them, show them the file. If they want it changed or gone,
do it without argument and without asking why — it is a description of them.

**Tell them it exists.** When you save a profile about someone who was not in the session, say so
to the person saving it and suggest they mention it. A stored account of how a colleague thinks that
the colleague does not know about is the failure mode here, and "it was only meant to help" does not
undo it.

## Whose profile is it

Self-authored by default. The subject should be able to read their own file and recognise it as
something they would have said.

Write preferences, not assessments:

| Write this | Not this |
|---|---|
| "Wants the decision first, detail on request" | "Doesn't read long text" |
| "Fluent in supply chain — skip the domain primer" | "Only knows supply chain" |
| "Prefers to be asked before you start" | "Micromanages" |

Both columns carry the same operational information. Only one is a characterization of a colleague
sitting in version control where they can find it.

A profile for someone who did not write it sets `authored_by:` to whoever did. When you use it
outbound, say so — *"drafted using the profile for Kishor, written by you"* — so the person driving
knows what it is based on.

---

## Outbound

Any drafting task can name an audience:

```
/hitl:dev-draft-for kishor  "PR comment for the migration fix"
```

Read that person's profile and write to it: their length, their format, their level of domain
detail, and what they are being asked to *do*. Then say which profile you used, so the sender can
check it before posting.

Two things stay true regardless of audience:

- **The floor above.** Every risk, cost, and open decision survives the reformatting.
- **It is a draft.** HITL does not send anything. The person whose name goes on it reads it first.

If no profile exists for the named person, say so and ask what they need — do not invent one from
a name, a title, or a guess about their seniority.
