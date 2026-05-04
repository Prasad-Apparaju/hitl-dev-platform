# [Project Name] — Best Practices

**Date:** YYYY-MM
**Status:** Living document — updated as practices evolve

This document captures all best practices, organized by category. Each practice is tagged with its origin so the team knows why it exists and whether it can be changed.

**Origin tags:**
- **(User)** — explicitly requested by a stakeholder (PM, architect, customer)
- **(Design)** — derived from architecture decisions (ADRs)
- **(Incident)** — added after a production incident (linked to incident registry)
- **(Convention)** — industry standard or framework best practice

---

## Table of Contents

1. [Category 1](#1-category-1)
2. [Category 2](#2-category-2)

<!-- Common categories (pick what applies to your project):
- API Design
- Authentication & Security
- Data Architecture
- Testing
- Infrastructure & Deployment
- Code Quality
- Configuration Management
- Observability & Monitoring
- Cost Management
- Development Process
- Agentic AI (if applicable)
- Agent Orchestration (if applicable)
- Frontend
-->

---

## 1. [Category Name]

### 1.1 [Practice Name] (Origin)

[One paragraph describing the practice — what to do and why.]

**Why:** [Rationale — what goes wrong without this practice. Link to ADR or incident if applicable.]

### 1.2 [Practice Name] (Origin)

[Same structure]

---

## 2. [Category Name]

### 2.1 [Practice Name] (Origin)

[Same structure]

---

## How to Use This Document

- **Before implementing:** Check if a relevant practice exists. Follow it unless you have a documented reason not to (which becomes a new ADR).
- **When adding a practice:** Tag the origin. If it came from an incident, link the incident registry entry. If from an ADR, link the ADR.
- **When changing a practice:** Update the origin tag if the reason changed. If removing a practice, document why (it might have been added after an incident).
- **Extracting to CLAUDE.md:** The most critical practices (ones that apply to ALL code) should also appear in `CLAUDE.md` under Cross-Cutting Conventions. CLAUDE.md is auto-loaded; this document is reference.

## Review Schedule

Review quarterly. For each practice, ask:
1. Is this still relevant? (Technology or architecture may have changed)
2. Is this being followed? (Check convention checker results)
3. Should this be promoted to a convention? (If it's critical enough for CI enforcement)
