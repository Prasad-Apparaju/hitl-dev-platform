#!/usr/bin/env bash
set -euo pipefail
git init -q .
mkdir -p .hitl docs/01-product
printf 'change_id_prefix: SVC\nprefixes: { DOCS: acme/docs }\n' > .hitl/config.yaml
printf '# PRD\n\n## FR-1 Discount codes\nShoppers can enter a discount code at checkout.\n- AC-1: a valid code lowers the total\n' > docs/01-product/prd.md
git add -A && git -c user.email=e@x -c user.name=eval commit -qm init
