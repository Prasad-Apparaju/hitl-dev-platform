# [Product Name] — Product Requirements Document

**Product:** [Name]
**Version:** [Date]
**Status:** Draft | Approved
**Author:** [PM name]
**Last Updated:** [Date]

---

## 1. Executive Summary

[2-3 paragraphs: What is this product? Who is it for? What problem does it solve? What does success look like?]

---

## 2. Problem Statement

[What pain exists today? Who feels it? What happens if we don't solve it? Include data or quotes if available.]

---

## 3. Target Users and Personas

| Persona | Role | Key need | Success metric |
|---------|------|----------|---------------|
| [Name] | [Role/title] | [What they need from this product] | [How they measure success] |
| [Name] | [Role/title] | [What they need] | [How they measure] |

---

## 4. Solution Overview

[High-level description of the solution. What does the user experience look like? Include a diagram if helpful.]

---

## 5. Functional Requirements

### 5.1 [Feature/Module Name]

| ID | Requirement | Priority | Acceptance Criteria |
|----|------------|:--------:|---------------------|
| FR-1 | [What the system must do] | Must Have | [How to verify it works — specific, testable] |
| FR-2 | [What the system must do] | Should Have | [How to verify] |
| FR-3 | [What the system must do] | Nice to Have | [How to verify] |

### 5.2 [Feature/Module Name]

[Same table structure]

<!-- 
TIPS FOR WRITING REQUIREMENTS AI CAN USE:

1. Be specific — "Users can filter products by category" not "The system should be user-friendly"
2. Include acceptance criteria — these become test cases. AI generates tests from them.
3. Use "Must Have / Should Have / Nice to Have" — this determines build order.
4. Describe WHAT, not HOW — "Users can log in with email and password" not "Use JWT with bcrypt"
   (the HOW belongs in ADRs and LLDs, decided by the architect)
5. Include edge cases — "If the user enters an invalid email, show an error message"
   AI is good at the happy path but misses edge cases unless you specify them.
-->

---

## 6. Non-Functional Requirements

| ID | Category | Requirement | Target |
|----|----------|------------|--------|
| NFR-1 | Performance | [e.g., Page load time] | [e.g., < 2 seconds P95] |
| NFR-2 | Availability | [e.g., Uptime SLA] | [e.g., 99.9%] |
| NFR-3 | Security | [e.g., Data encryption] | [e.g., AES-256 at rest, TLS in transit] |
| NFR-4 | Scalability | [e.g., Concurrent users] | [e.g., 1000 concurrent users] |

---

## 7. Use Cases

### UC-1: [Use Case Name]

**Actor:** [Who initiates this]
**Precondition:** [What must be true before]
**Flow:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected outcome:** [What happens when it works]
**Error scenarios:** [What can go wrong and how the system responds]

### UC-2: [Use Case Name]

[Same structure]

---

## 8. Success Metrics / KPIs

| Metric | Current baseline | Target | Measurement method |
|--------|:----------------:|:------:|-------------------|
| [e.g., User activation rate] | [current %] | [target %] | [how measured] |
| [e.g., Time to first value] | [current] | [target] | [how measured] |

---

## 9. Out of Scope

[Explicitly list what this PRD does NOT cover. This prevents scope creep and helps AI stay focused.]

- [Feature X — deferred to Phase 2]
- [Integration Y — separate PRD]

---

## 10. Open Questions

| # | Question | Owner | Status |
|---|---------|-------|--------|
| 1 | [Unresolved question] | [Who should answer] | Open |

---

## How This Document Feeds the Development Process

1. **Architect reads this PRD** → creates HLDs (system architecture) and ADRs (design decisions)
2. **AI reads the HLDs** → generates LLDs (detailed component designs) for architect review
3. **AI reads the LLDs** → generates tests (TDD) and then code
4. **PM reviews the impact brief** → Section 4 (PM mental model update) tells you what changed
5. **PM reviews the demo** → accepts or requests changes based on the acceptance criteria in this PRD

The more specific your requirements and acceptance criteria, the better AI generates the right code the first time.
