#!/usr/bin/env bash
# Generates a HumAIn-branded release zip from this hitl-dev-platform repo.
# The zip contains all platform files with HITL references replaced by HumAIn,
# ready for companies to copy into their internal repos without external dependencies.
#
# Usage:  bash tools/scripts/make-release.sh <version>
# Example: bash tools/scripts/make-release.sh v1.0.0
#
# Output: humain-<version>.zip in the repo root
# Publish: git tag <version> && git push origin <version>
#          gh release create <version> humain-<version>.zip \
#            --title "HumAIn <version>" --notes "..."

set -euo pipefail

VERSION="${1:?Usage: $0 <version>  e.g. v1.0.0}"
RELEASE_DIR="humain-${VERSION}"
ZIPFILE="${RELEASE_DIR}.zip"
STAGING=$(mktemp -d)

cleanup() { rm -rf "$STAGING"; }
trap cleanup EXIT

# ── 1. Export tracked files only (no .git history) ──────────────────────────
echo "==> Staging ${RELEASE_DIR}..."
mkdir -p "$STAGING/$RELEASE_DIR"
git archive HEAD | tar -x -C "$STAGING/$RELEASE_DIR"

# ── 2. Remove dev-only content ───────────────────────────────────────────────
echo "==> Removing dev-only content..."
rm -rf "$STAGING/$RELEASE_DIR/.semgrep"
find "$STAGING/$RELEASE_DIR/tools/scripts" -name "test-*.sh" -delete 2>/dev/null || true
find "$STAGING/$RELEASE_DIR" \( -name "*.pdf" -o -name "*.pptx" \) -delete 2>/dev/null || true

# ── 2b. Derive installed Claude artifacts from the source tree ────────────────
# The active packaged skill reads the installed schema under .claude/…; it must be
# byte-identical to the source under ai/claude/… (a stale copy ships legacy fields).
echo "==> Deriving installed Claude schema from source..."
SRC_SCHEMA="$STAGING/$RELEASE_DIR/ai/claude/generate-docs/templates/system-manifest.schema.yaml"
INSTALLED_SCHEMA="$STAGING/$RELEASE_DIR/.claude/commands/skills/generate-docs/templates/system-manifest.schema.yaml"
if [[ -f "$SRC_SCHEMA" && -f "$INSTALLED_SCHEMA" ]]; then
    cp "$SRC_SCHEMA" "$INSTALLED_SCHEMA"
fi

# ── 3. Apply HumAIn branding (order matters) ─────────────────────────────────
# Process every text file regardless of extension (covers .gitignore, .toml,
# .html, .js, .template, extensionless git hooks, etc.)
echo "==> Applying HumAIn branding..."
find "$STAGING/$RELEASE_DIR" -type f | while IFS= read -r f; do
    # Skip binary files (grep -I treats them as having no matches)
    grep -qI '' "$f" 2>/dev/null || continue
    perl -i -pe '
        # Specific product name first (avoids partial overlap with later rules)
        s/hitl-dev-platform/humain/g;

        # Shell/env var names stay ALL-CAPS: HITL_ prefix and _HITL_ infix
        s/\bHITL_/HUMAIN_/g;
        s/_HITL_/_HUMAIN_/g;

        # Runtime paths
        s{/tmp/hitl-}{/tmp/humain-}g;
        s{\.hitl/}{\.humain/}g;

        # Display name (remaining ALL-CAPS uses)
        s/\bHITL\b/HumAIn/g;

        # Lowercase uses (paths, variable values, identifiers like hitl_segment)
        s/hitl/humain/g;
    ' "$f"
done

# ── 4. Rename files that contain "hitl" in their name ────────────────────────
echo "==> Renaming files..."
find "$STAGING/$RELEASE_DIR" -depth -name "*hitl*" | while IFS= read -r f; do
    newf="${f//hitl/humain}"
    [[ "$f" != "$newf" ]] && mv "$f" "$newf"
done

# ── 5. Verify no HITL references remain in text files ────────────────────────
echo "==> Verifying replacements..."
# Exclude the builder itself — its own replacement regexes (s/hitl/humain/) are not
# stray references and must not trip the check.
scan_remaining() {
    grep -rl --include="*.sh" --include="*.json" --include="*.yaml" \
        --include="*.yml" --include="*.md" --include="*.py" \
        -e "hitl" -e "HITL" \
        "$STAGING/$RELEASE_DIR" 2>/dev/null \
        | grep -v "tools/scripts/make-release.sh" || true
}
REMAINING=$(scan_remaining | wc -l | tr -d ' ')

if [[ "$REMAINING" -gt 0 ]]; then
    echo "    WARNING: ${REMAINING} file(s) still contain HITL references:"
    scan_remaining | sed "s|$STAGING/$RELEASE_DIR/||"
    echo "    These may need manual review."
else
    echo "    OK — no HITL references found in text files."
fi

# ── 6. Package ────────────────────────────────────────────────────────────────
echo "==> Packaging..."
(cd "$STAGING" && zip -qr "$OLDPWD/$ZIPFILE" "$RELEASE_DIR" \
    --exclude "*/.DS_Store" --exclude "*/__pycache__/*" --exclude "*/.pytest_cache/*")

SIZE=$(du -sh "$ZIPFILE" | cut -f1)
echo ""
echo "Created: $ZIPFILE  ($SIZE)"
echo ""
echo "Verify the zip contents:"
echo "  unzip -l $ZIPFILE | head -40"
echo ""
echo "To publish a GitHub Release:"
echo "  git tag $VERSION && git push origin $VERSION"
echo "  gh release create $VERSION $ZIPFILE \\"
echo "    --title \"HumAIn $VERSION\" \\"
echo "    --notes \"HumAIn AI-Driven Development platform $VERSION\""
