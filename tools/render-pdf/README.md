# Rendering Markdown to PDF (with Mermaid)

This directory contains a custom script for rendering Markdown to PDF with Mermaid diagrams. **For most use cases, use the standard toolchain below instead.**

## Recommended approach: `mmdc` + `md-to-pdf`

```bash
# 1. Install tools
npm install -g @mermaid-js/mermaid-cli md-to-pdf

# 2. Pre-render Mermaid diagrams to SVG
mmdc -i input.md -o output-with-svgs.md

# 3. Convert to PDF
md-to-pdf output-with-svgs.md
```

This two-step pipeline uses maintained, community-supported tools. `mmdc` (Mermaid CLI) renders all ` ```mermaid ` blocks to inline SVGs, and `md-to-pdf` handles the Markdown-to-PDF conversion.

## When to use the custom script

The custom `md-to-pdf.js` in this directory exists for cases where the standard pipeline doesn't produce acceptable results (e.g., SVG sizing issues, custom page layout). It uses Puppeteer + Mermaid.js CDN directly.

```bash
# Install dependencies
npm install marked puppeteer

# Run
node tools/render-pdf/md-to-pdf.js <input.md> <output.pdf> tools/render-pdf/style.css
```

## Styling

Edit `style.css` to customize fonts, margins, and code block formatting for PDF output.
