const puppeteer = require("puppeteer");
async function main() {
  const browser = await puppeteer.launch({
    executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: "new",
    args: ["--no-sandbox","--disable-dev-shm-usage","--disable-gpu",
           "--user-data-dir=/tmp/md2pdf-chrome-profile","--no-first-run","--no-default-browser-check"],
    timeout: 120000,
  });
  const page = await browser.newPage();
  await page.goto("file:///tmp/md2pdf-workspace/collaboration.html", { waitUntil: "networkidle0", timeout: 30000 });
  await page.pdf({
    path: "/tmp/hitl-team-collaboration.pdf",
    landscape: true, format: "A4", printBackground: true,
    preferCSSPageSize: true, margin: { top: 0, right: 0, bottom: 0, left: 0 },
  });
  console.log("Wrote /tmp/hitl-team-collaboration.pdf");
  await browser.close();
}
main().catch((err) => { console.error(err); process.exit(1); });
