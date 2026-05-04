# Design Decisions — Consolidated Reference

**Parent:** [HLD Index](../hld/index.md)
**Purpose:** Catalog of every architectural decision, organized by category. Use this for quick lookup; use individual ADR files for full context and rationale.

---

## When to Use This vs. Individual ADRs

| This catalog | Individual ADR files |
|-------------|---------------------|
| Quick reference during development | Full context for a specific decision |
| "What did we decide about X?" | "Why did we decide X and what alternatives did we consider?" |
| Onboarding — scan all decisions in 30 min | Deep dive into one decision |
| Convention checker — derive rules from decisions | ROI tracking — 30/90 day verification |

**Maintenance rule:** Every accepted ADR gets a row in this catalog. Every row links back to its full ADR (if one exists). Small decisions that don't warrant a full ADR can live here alone.

---

## 1. [Category: Infrastructure & Cloud]

### D-1.1: [Decision Title]

| | |
|---|---|
| **Chosen** | [What was chosen] |
| **Rationale** | [One sentence — why this option] |
| **Alternatives** | [What was rejected and why, briefly] |
| **Constraints** | [What forced this decision — budget, timeline, team expertise] |
| **ADR** | [Link to full ADR if exists, or "—" if decision is small enough for this row only] |

### D-1.2: [Decision Title]

[Same structure]

---

## 2. [Category: Backend / API]

### D-2.1: [Decision Title]

[Same structure]

---

## 3. [Category: Data]

### D-3.1: [Decision Title]

[Same structure]

---

## 4. [Category: Frontend]

### D-4.1: [Decision Title]

[Same structure]

---

## 5. [Category: AI / Agents] (if applicable)

### D-5.1: [Decision Title]

[Same structure]

---

## 6. [Category: Security]

### D-6.1: [Decision Title]

[Same structure]

---

## 7. [Category: Observability]

### D-7.1: [Decision Title]

[Same structure]

---

<!-- 
NAMING CONVENTION: D-{category}.{number}
  Category 1 = Infrastructure
  Category 2 = Backend
  Category 3 = Data
  Category 4 = Frontend
  Category 5 = AI/Agents
  Category 6 = Security
  Category 7 = Observability
  Add more categories as needed.

WHEN TO ADD: After every ADR is accepted, add a row here.
WHEN TO UPDATE: If a decision is superseded, mark it as such and link the new decision.
-->
