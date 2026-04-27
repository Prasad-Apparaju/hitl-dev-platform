# Review LLD Adherence

Check that generated code strictly matches what the LLD specifies. Run this before opening any PR. It is a required step in the change workflow.

**Input:** $ARGUMENTS (optional — component name, file path, or PR description. If empty, uses current git diff.)

---

## Step 1 — Identify what was built

1. Read the diff: `git diff main...HEAD` or the staged changes
2. List every source file that was added or modified
3. For each file, look up its governing LLD via `docs/system-manifest.yaml`
4. If a modified file has no LLD entry → flag immediately: "⚠️ [file] has no LLD. Either add it to the manifest and create an LLD, or confirm with the architect that this file is exempt."

---

## Step 2 — Read the governing LLDs

For each domain touched by the diff:
1. Read the full LLD document
2. Extract every class, method, interface, and data structure the LLD specifies
3. Note any sections marked DRAFT, TODO, or TBD — these are ambiguous and need architect sign-off

---

## Step 3 — Check LLD → Code (nothing missing)

For each element specified in the LLD, verify it exists in the generated code:

| LLD Element | Expected | Found in Code | Status |
|---|---|---|---|
| `ClassName` | class with fields X, Y, Z | `src/foo.py:12` | ✅ |
| `method_name(args) -> ReturnType` | method signature | `src/foo.py:34` | ✅ |
| `field: Type` | attribute on class | — | ❌ MISSING |

Mark each as:
- ✅ **Present and matches** — implementation matches LLD spec
- ⚠️ **Present but diverged** — exists but signature, behavior, or naming differs from LLD
- ❌ **Missing** — LLD specifies it, code does not have it

---

## Step 4 — Check Code → LLD (nothing extra)

For each class, method, and public interface in the generated code, verify it appears in the LLD:

| Code Element | File | In LLD? | Status |
|---|---|---|---|
| `ExtraHelper` class | `src/foo.py:78` | No | ❌ NOT SPECIFIED |
| `_private_method` | `src/foo.py:90` | N/A (private) | ✅ EXEMPT |

Mark each as:
- ✅ **In LLD** — specified and expected
- ✅ **EXEMPT** — private/internal implementation detail not required to be in LLD
- ❌ **NOT SPECIFIED** — public interface added that the architect did not design

Private methods and internal helpers are exempt. Public classes, public methods, and any code that crosses a domain boundary must be in the LLD.

---

## Step 5 — Check cross-cutting conventions

Read the `cross_cutting` section of `docs/system-manifest.yaml`. Verify each convention is followed in the generated code. Flag any violation.

---

## Step 6 — Report

Present a structured report:

```
## LLD Adherence Report

**LLD reviewed:** [path]
**Files checked:** [list]
**Checked by:** Claude (model judgment — architect should review flagged items)

### ✅ Matching ([N] elements)
All LLD-specified elements found and matching.

### ⚠️ Diverged ([N] elements — architect decision required)
- [element]: LLD specifies [X], code implements [Y]. 
  Options: (a) update LLD to reflect better design, (b) fix code to match LLD.

### ❌ Missing ([N] elements — must fix before merge)
- [element]: specified in LLD at [section], not found in code.

### ❌ Not Specified ([N] elements — must fix before merge)
- [element] in [file:line]: public interface not in LLD. Either add to LLD (architect approval required) or remove from code.

### Convention Violations ([N] — must fix before merge)
- [file:line]: [convention name] violated. [what's wrong and how to fix]

### Verdict
[ ] PASS — all elements match, no violations. PR may proceed.
[ ] PASS WITH NOTES — diverged items logged, architect notified. PR may proceed after architect acknowledges.
[ ] BLOCK — missing elements or unspecified public interfaces. Fix before PR.
```

---

## Step 7 — Handle divergence

For each ⚠️ diverged item, present the choice explicitly:

> "The LLD specifies `method_name(user_id: str) -> User`. The implementation uses `method_name(user: UserDTO) -> UserResponse`. This is a design divergence. Options:
> (a) **Update the LLD** — if the implementation reflects a better design. Requires architect approval before merge.
> (b) **Fix the code** — if the implementation drifted unintentionally. Fix now.
> Which do you want to do?"

Do NOT silently normalize divergence. Every deviation is either an intentional design improvement (update the LLD) or a mistake (fix the code). There is no third option.

---

## Important Rules

- This skill uses model judgment to assess adherence. It will miss subtle behavioral divergence. It catches structural divergence (missing classes, wrong signatures, extra public interfaces).
- Flag every ❌ item as a merge blocker. The developer cannot mark the PR ready until all ❌ items are resolved or explicitly approved by the architect.
- ⚠️ items require architect acknowledgment but do not block merge on their own.
- If the LLD was written at a high level of abstraction (method names only, no signatures), say so and note which checks were skipped due to insufficient LLD detail. This is feedback to the architect to improve the LLD.
- Private implementation details are exempt. The LLD governs public contracts, not internal mechanics.
