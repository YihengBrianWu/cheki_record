// Usage: NODE_PATH=/path/to/node_modules CHROME_PATH=/path/to/chrome node scripts/render-prototype.mjs
import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const target = path.join(root, 'docs/prototype/screens');
await mkdir(target, { recursive: true });
const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) });
const errors = [];
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  page.on('pageerror', e => errors.push(e.message));
  const base = pathToFileURL(path.join(root, 'docs/prototype/index.html')).href;
  const scenes = ['home', 'quick', 'batch', 'day', 'idol', 'stats', 'album', 'data'];
  for (const screen of scenes) {
    await page.goto(`${base}?screen=${screen}&capture=1`);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(target, `${screen}.png`) });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    if (overflow) errors.push(`${screen}: horizontal overflow`);
  }
  for (const [name, screen, mode] of [['quick-group','quick','group'],['quick-special','quick','special'],['group','idol','group'],['special','idol','special']]) {
    await page.goto(`${base}?screen=${screen}&capture=1`);
    await page.locator(`#app [data-${screen==='quick'?'draft':'profile'}-mode="${mode}"]`).click();
    if(screen==='quick') {
      if(mode==='special') {
        await page.locator('#app [data-select-target="b"]').click();
        await page.locator('#app [data-type-id="t3"]').click();
        await page.fill('#quick-amount', '120');
      } else await page.locator('#app [data-type-id="t6"]').click();
    }
    await page.screenshot({ path: path.join(target, `${name}.png`) });
  }
  await page.setViewportSize({ width: 320, height: 844 });
  for (const screen of scenes) {
    await page.goto(`${base}?screen=${screen}`);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    if (overflow) errors.push(`${screen}: horizontal overflow at 320px`);
  }
  if (errors.length) throw new Error(errors.join('\n'));
  console.log('Rendered 8 screens and 4 group / special variants. No page errors or horizontal overflow at 390px / 320px.');
} finally {
  await browser.close();
}
