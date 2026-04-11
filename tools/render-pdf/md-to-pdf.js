#!/usr/bin/env node
/**
 * Custom markdown-to-PDF converter with mermaid support.
 *
 * md-to-pdf does not render mermaid diagrams natively; it leaves them as
 * code blocks. This script does the job md-to-pdf would do PLUS mermaid
 * rendering by:
 *
 *   1. Parsing markdown with `marked`, intercepting fenced ```mermaid
 *      blocks and replacing them with <div class="mermaid"> containers.
 *   2. Wrapping the output in a self-contained HTML shell that loads
 *      mermaid.js from CDN and calls mermaid.run() after DOMContentLoaded.
 *   3. The shell sets window.__mermaidDone = true when all diagrams have
 *      rendered, so the puppeteer side can wait for it reliably.
 *   4. Launching the system Chrome via puppeteer with an isolated profile
 *      dir so it doesn't attach to the user's running Chrome instance.
 *   5. Waiting for window.__mermaidDone, then printing to PDF.
 *
 * Usage: node convert.js <input.md> <output.pdf> <style.css>
 */

const fs = require("fs");
const path = require("path");
const { marked } = require("marked");
const puppeteer = require("puppeteer");

async function main() {
  const [, , inputPath, outputPath, stylePath] = process.argv;
  if (!inputPath || !outputPath || !stylePath) {
    console.error("Usage: convert.js <input.md> <output.pdf> <style.css>");
    process.exit(1);
  }

  // Read source files.
  const md = fs.readFileSync(inputPath, "utf8");
  const css = fs.readFileSync(stylePath, "utf8");

  // Configure marked to emit mermaid blocks as <div class="mermaid">
  // containers instead of <pre><code class="language-mermaid"> blocks.
  // Mermaid.run() scans for `.mermaid` and replaces their text content
  // with the rendered SVG in-place.
  const renderer = new marked.Renderer();
  const originalCode = renderer.code.bind(renderer);
  renderer.code = (code, infostring, escaped) => {
    // marked v9+ passes an object { text, lang, escaped }; earlier
    // versions pass (text, lang, escaped). Handle both.
    let text, lang;
    if (typeof code === "object" && code !== null) {
      text = code.text;
      lang = code.lang;
    } else {
      text = code;
      lang = infostring;
    }
    if ((lang || "").toLowerCase() === "mermaid") {
      // Mermaid expects the diagram source as plain text inside the div.
      // Escape HTML-sensitive chars but leave the mermaid syntax alone.
      const safe = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
      return `<div class="mermaid">${safe}</div>\n`;
    }
    return originalCode(code, infostring, escaped);
  };

  // Render the markdown. `gfm` gives us tables, task lists, strikethrough.
  // `breaks: false` keeps single newlines from becoming <br> — important
  // so prose paragraphs wrap cleanly.
  marked.setOptions({
    renderer,
    gfm: true,
    breaks: false,
    headerIds: false,
    mangle: false,
  });
  const contentHtml = marked.parse(md);

  // Assemble a self-contained HTML page. Mermaid is loaded from the CDN
  // because bundling it would pull in too much code; the laptop is online
  // while this script runs. window.__mermaidDone is the signal puppeteer
  // waits on before calling page.pdf().
  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>AI-Native Development Process</title>
<style>
${css}

/* Fix code block overflow — wrap long lines so they don't get clipped at
 * the right page margin. This is applied only for print; on-screen the
 * wrap is still fine. */
.markdown-body pre,
.markdown-body pre code {
  white-space: pre-wrap !important;
  word-break: break-word;
  overflow-wrap: anywhere;
}

/* Mermaid container: keep diagrams from being clipped by the page and
 * center them neatly. mermaid.js injects its SVG as a child here. */
.markdown-body div.mermaid {
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 12pt auto;
  /* The content area on A4 with 16mm side margins is ~178mm ≈ 672px
   * at 96dpi. Cap at 640px so there's a bit of breathing room. */
  max-width: 640px;
  page-break-inside: avoid;
}

/* Force SVG to scale with its container regardless of the inline
 * width/height attributes mermaid emits. The width/height attributes
 * are also stripped in JS post-render — belt and suspenders. */
.markdown-body div.mermaid svg {
  max-width: 100% !important;
  max-height: 620px !important;
  width: auto !important;
  height: auto !important;
  display: block;
}
</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11.4.0/dist/mermaid.min.js"></script>
</head>
<body>
<article class="markdown-body">
${contentHtml}
</article>
<script>
// Wait for DOMContentLoaded + mermaid to finish rendering all diagrams.
// Set window.__mermaidDone so puppeteer can poll for it.
window.__mermaidDone = false;
(async () => {
  try {
    mermaid.initialize({
      startOnLoad: false,
      theme: "default",
      themeVariables: {
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif',
        fontSize: "12px",
      },
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: "basis",
        nodeSpacing: 30,
        rankSpacing: 40,
      },
      sequence: { useMaxWidth: true },
    });
    // Run mermaid across every .mermaid div on the page.
    await mermaid.run({ querySelector: ".mermaid" });

    // Strip explicit width/height attributes from every mermaid SVG so
    // CSS max-width + aspect-ratio (from the viewBox) can scale them to
    // fit the page. Without this, SVGs render at their natural pixel
    // size and a 7-subgraph diagram takes up multiple pages.
    for (const svg of document.querySelectorAll(".mermaid svg")) {
      svg.removeAttribute("width");
      svg.removeAttribute("height");
      // Make sure the viewBox is present so the intrinsic aspect ratio
      // survives. mermaid always sets it, but defensive removal of the
      // inline style attribute catches any max-width: N px the lib
      // may have set.
      const style = svg.getAttribute("style") || "";
      svg.setAttribute(
        "style",
        style
          .replace(/max-width\s*:\s*[^;]+;?/gi, "")
          .replace(/width\s*:\s*[^;]+;?/gi, "")
          .replace(/height\s*:\s*[^;]+;?/gi, ""),
      );
    }
  } catch (err) {
    console.error("mermaid.run error:", err);
    // Still mark as done so puppeteer doesn't hang; the failing diagram
    // will just be rendered as plain text, which is better than no PDF.
  } finally {
    window.__mermaidDone = true;
  }
})();
</script>
</body>
</html>`;

  // Write the intermediate HTML next to the workspace for inspection on failure.
  const tmpHtmlPath = path.join(path.dirname(outputPath), ".md2pdf-intermediate.html");
  fs.writeFileSync(tmpHtmlPath, html, "utf8");

  // Launch Chrome via puppeteer. Use the system Chrome app to avoid downloading
  // a separate Chromium build. `--user-data-dir` is the critical flag: without
  // it, Chrome attaches to any running user instance and the debugging
  // WebSocket never comes up, causing a 30s launch timeout.
  const browser = await puppeteer.launch({
    executablePath:
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: "new",
    args: [
      "--no-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu",
      "--user-data-dir=/tmp/md2pdf-chrome-profile",
      "--no-first-run",
      "--no-default-browser-check",
    ],
    timeout: 120000,
  });

  try {
    const page = await browser.newPage();

    // Navigate to the file via file:// URL so mermaid-from-CDN loads over https.
    await page.goto("file://" + tmpHtmlPath, {
      waitUntil: "networkidle0",
      timeout: 90000,
    });

    // Wait for mermaid to flip the done flag. 60s budget is generous for
    // ~10 diagrams on a warm CDN cache.
    await page.waitForFunction(() => window.__mermaidDone === true, {
      timeout: 60000,
    });

    // Give the layout a tick to settle after svg injection so page breaks
    // land correctly.
    await new Promise((r) => setTimeout(r, 500));

    // Print. preferCSSPageSize honors the @page rule in our stylesheet so
    // A4/margins stay in one place.
    await page.pdf({
      path: outputPath,
      format: "A4",
      printBackground: true,
      preferCSSPageSize: true,
      margin: {
        top: "18mm",
        right: "16mm",
        bottom: "22mm",
        left: "16mm",
      },
      displayHeaderFooter: true,
      headerTemplate: "<div></div>",
      footerTemplate:
        '<div style="font-size:9px;color:#888;width:100%;text-align:center;padding:4px 0;">' +
        '<span class="pageNumber"></span> / <span class="totalPages"></span>' +
        "</div>",
    });

    console.log("Wrote " + outputPath);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
