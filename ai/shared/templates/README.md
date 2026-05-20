# ai/shared/templates/

**Document scaffolds used by AI skills** — skills read these and fill them in. Humans receive the completed output, not these raw files.

| Template | Used by |
|----------|---------|
| `prd-template.md` | `/hitl:pm:add-feature`, `/hitl:pm:design-feature` |
| `decision-packet-template.yaml` | `/hitl:dev:apply-change`, `/hitl:architect:design-feature` |
| `incident-registry-template.yaml` | `/hitl:dev:practices`, `/hitl:dev:impact-brief` |
| `test-registry-template.yaml` | `/hitl:dev:tdd`, `/hitl:qa:plan-tests` |
| `test-strategy-template.md` | `/hitl:qa:plan-tests` |
| `deployment-manifest-template.yaml` | `/hitl:ops:deploy`, `/hitl:ops:apply-iac` |
| `system-manifest-template.yaml` | `tools/scripts/init-project.sh` (copied to new product repos) |
| `issue-template.md` | `/hitl:pm:report-bug`, `/hitl:pm:add-feature` |
| `pull-request-template.md` | `/hitl:dev:conclude` |
| `*-template.md` (others) | `/hitl:dev:generate-docs`, `/architect:*` |

HLD, LLD, ADR, and CLAUDE.md templates live in `ai/claude/generate-docs/templates/` — co-located with the skill that uses them.
