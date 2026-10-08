# Seed the registries (brownfield Step 8)

The full procedure for Step 8 of `/hitl:dev-start-brownfield`. Read this file and perform every part of it, then return to `SKILL.md` Step 9. `$PLUGIN_ROOT` is whatever the Step 3 fence resolved; if it is empty, resolve it again the same way before the copy.

The 31-step workflow queries these two registries at multiple points. They must exist before `/hitl:dev-practices` is run for the first time.

**Test registry** (`docs/03-engineering/testing/test-registry.yaml`):
- Ask: "Do you have existing tests? If so, I'll create a registry stub from your test files."
- If yes: scan `tests/`, `spec/`, or equivalent; generate one entry per test file with `domain` and `path`. Leave `risk` and `covers` as DRAFT.
- If no: create an empty stub.

**Incident registry** (`docs/04-operations/incident-registry.yaml`):
- Ask: "What broke in production in the last 6 months? Describe each incident in one sentence."
- For each answer, add one entry with `description`, `domain` (best guess), and `date`.
- If they have nothing: create an empty stub and say: "You can add entries later: after each production incident, run `/hitl:ops-incident`."

**Product baseline** (`docs/01-product/prd.md`): the PM and QA skills read the PRD for personas and requirements, so a brownfield project with no PRD leaves them nowhere to land. Initialize the PRD *shell*, not a retroactive spec of existing behaviour (that lives in the reverse-engineered technical docs), only personas and format so the next requirement has a home. If `docs/01-product/prd.md` is missing and `$PLUGIN_ROOT` (Step 3) is set, run `mkdir -p docs/01-product && cp "$PLUGIN_ROOT/shared/templates/prd-template.md" docs/01-product/prd.md`. Then ask "Who are the primary users of this system, and what does each need?" and fill §3 (Target Users and Personas); leave §5 (Functional Requirements) empty, noted "No requirements yet: added via `/hitl:pm-add-feature`." Say: "Product baseline initialized; PM and QA skills are now active."
