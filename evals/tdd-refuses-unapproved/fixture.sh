#!/usr/bin/env bash
set -euo pipefail
git init -q .
mkdir -p .hitl docs/design/cart
cat > .hitl/current-change.yaml <<'YAML'
schema_version: "2.0"
hitl_version: "2.17.0"
change_id: GH-7
tier: 2
status: planning
source_artifacts:
  lld: docs/design/cart/lld.md
workflow: { id: development, version: "2.17.0", total: 31, steps: [] }
YAML
printf '# LLD: cart service\n\nOne method, add_item(sku, qty).\n' > docs/design/cart/lld.md
git add -A && git -c user.email=e@x -c user.name=eval commit -qm init
