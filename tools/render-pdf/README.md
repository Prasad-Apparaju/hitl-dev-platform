# PDF Renderer

Converts Markdown files to PDF with full Mermaid diagram rendering. Standard markdown-to-PDF tools leave Mermaid blocks as raw code — this tool renders them as actual diagrams.

## Usage

```bash
node tools/render-pdf/md-to-pdf.js <input.md> <output.pdf> tools/render-pdf/style.css
```

## Requirements

```bash
npm install marked puppeteer
```

A Chromium-compatible browser must be installed (Puppeteer downloads one automatically on first install).

## How It Works

1. Parses Markdown with `marked`, intercepting ` ```mermaid ` blocks
2. Replaces Mermaid blocks with `<div class="mermaid">` containers
3. Wraps output in HTML that loads `mermaid.js` from CDN
4. Launches headless Chrome via Puppeteer
5. Waits for all Mermaid diagrams to render
6. Prints to PDF

## Styling

Edit `style.css` to customize the PDF appearance (fonts, margins, code block styling, etc.).

## When to Use

- Generating PDFs of HLD/LLD documents for stakeholder review
- Creating printable versions of architecture diagrams
- Sharing design docs with people who don't use GitHub or Obsidian
