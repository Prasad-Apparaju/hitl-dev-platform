# templates/

**Document templates** — copy these into your product repo and fill in the blanks.

Templates are the starting structure for HITL artifacts. Skills like `/generate-docs` and `/architect:design-feature` use them to produce project-specific documents.

| Template | What it produces |
|----------|-----------------|
| `CLAUDE.md.template` | Project AI rules — fill in your coding standards and conventions |
| `system-manifest-template.yaml` | Domain manifest — list your domains, files, and facade APIs |
| `decision-packet-template.yaml` | Per-change decision packet linking issue → design → tests |
| `prd-template.md` | Product requirements document with AI-friendly structure |
| `adr-template.md` | Architecture decision record |
| `issue-template.md` | GitHub issue with ROI and downstream impact sections |
| `test-registry-template.yaml` | Test case catalog by domain and risk level |
| `incident-registry-template.yaml` | Incident catalog with regression test links |
| `pull-request-template.md` | PR checklist with HITL traceability gates |
| `training-plan-template.md` | Capability training plan stub |
| `deployment-manifest-template.yaml` | Service inventory for deployment verification |
| `architect-playbook.md` | Role-specific process guide for architects |
| `developer-playbook.md` | Role-specific process guide for developers |
| others | Cost analysis, security audit, data model mapping, API contract mapping, best practices, performance optimization |
