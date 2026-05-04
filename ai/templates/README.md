# ai/templates/

**Document scaffolds used by AI skills** — skills read these and fill them in. Humans receive the completed output, not these raw files.

| Template | Used by |
|----------|---------|
| `prd-template.md` | `/pm:add-feature`, `/pm:design-feature` |
| `decision-packet-template.yaml` | `/apply-change`, `/architect:design-feature` |
| `incident-registry-template.yaml` | `/dev-practices`, `/impact-brief` |
| `test-registry-template.yaml` | `/tdd`, `/qa:plan-tests` |
| `test-strategy-template.md` | `/qa:plan-tests` |
| `deployment-manifest-template.yaml` | `/ops:deploy`, `/ops:apply-iac` |
| `system-manifest-template.yaml` | `tools/scripts/init-project.sh` (copied to new product repos) |
| `issue-template.md` | `/pm:report-bug`, `/pm:add-feature` |
| `pull-request-template.md` | `/conclude` |
| `*-template.md` (others) | `/generate-docs`, `/architect:*` |

HLD, LLD, ADR, and CLAUDE.md templates live in `ai/generate-docs/templates/` — co-located with the skill that uses them.
