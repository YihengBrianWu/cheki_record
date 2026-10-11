// Regression checks for history navigation and controls falling below short viewports.
// Uses the same Playwright / CHROME_PATH setup as render-prototype.mjs.
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const base = pathToFileURL(path.join(root, 'docs/prototype/index.html')).href;
const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) });
try {
  const page = await browser.newPage({ viewport: { width: 667, height: 805 } });
  page.setDefaultTimeout(5000);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  const open = screen => page.goto(`${base}?screen=${screen}`);
  const at = async screen => {
    await page.waitForURL(url => url.searchParams.get('screen') === screen && !url.hash);
    await page.locator(`#app.view-${screen}`).waitFor();
  };
  const homeControlsVisible = async () => {
    await at('home');
    for (const selector of ['.home-floating-actions', '.bottom-nav']) {
      const rect = await page.locator(selector).boundingBox();
      const height = page.viewportSize().height;
      assert.ok(rect && rect.y >= 0 && rect.y + rect.height <= height + 1, `${selector} outside ${height}px viewport: ${JSON.stringify(rect)}`);
    }
    assert.equal(await page.locator('.home-floating-actions').count(), 1);
    assert.equal(await page.locator('.bottom-nav').count(), 1);
  };
  const enter = screen => page.locator(`.home-floating-actions [data-go="${screen}"]`).click();
  const back = () => page.getByRole('button', { name: '返回上一页', exact: true }).click();

  // Both browser controls and the in-page back button restore a usable homepage.
  await open('home');
  for (const screen of ['quick', 'batch']) {
    await enter(screen); await at(screen);
    await page.goBack(); await homeControlsVisible();
    await page.goForward(); await at(screen);
    await back(); await homeControlsVisible();
  }

  // Reload must keep the current route instead of falling back to an old ?screen.
  await enter('batch'); await at('batch'); await page.reload(); await at('batch');
  assert.equal(await page.locator('#app h2').innerText(), '批量记录');
  await back(); await homeControlsVisible();

  // Direct links have no internal history: the in-page back action safely returns home.
  for (const screen of ['quick', 'batch', 'day', 'data']) {
    await open(screen); await at(screen); await back(); await homeControlsVisible();
  }
  // Previously shared query/hash links remain usable and become canonical.
  await page.goto(`${base}?screen=quick#home`); await homeControlsVisible();
  await page.goto(`${base}?screen=home#batch`); await at('batch'); await back(); await homeControlsVisible();

  // Return to the selected group, and to the exact day from which entry began.
  await page.locator('.bottom-nav [data-go="idol"]').click();
  await page.locator('[data-profile-mode="group"]').click();
  await page.locator('[data-target="g2"]').click();
  await page.locator('[data-quick-target="g2"]').click(); await at('quick');
  await back(); await at('idol');
  assert.equal(await page.locator('.idol-profile h3').innerText(), '晴空放送');
  await page.locator('.bottom-nav [data-go="home"]').click();
  await page.locator('[data-date="2026-10-05"]').click(); await at('day');
  await page.locator('.form-footer [data-go="quick"]').click(); await at('quick');
  assert.equal(await page.inputValue('#quick-date'), '2026-10-05');
  await back(); await at('day');
  assert.match(await page.locator('.day-hero h3').innerText(), /10月5日/);

  // A saved record stays in the in-memory database through backward/forward traversal.
  await open('home'); await enter('quick');
  await page.fill('#quick-qty', '2'); await page.fill('#quick-amount', '60');
  await page.locator('[data-action="save-quick"]').click(); await at('day');
  await page.goBack(); await at('quick'); await page.goBack(); await homeControlsVisible();
  assert.equal(await page.locator('.metrics .metric strong').first().innerText(), '19');

  // Reproduce short desktop and in-app windows as well as narrow mobile layouts.
  for (const [width, height] of [[1280,720], [900,650], [667,805], [390,667], [320,568]]) {
    await page.setViewportSize({ width, height }); await open('home'); await homeControlsVisible();
    const before = await page.locator('.home-floating-actions').boundingBox();
    await page.locator('#app>.body').evaluate(el => { el.scrollTop = el.scrollHeight; });
    const after = await page.locator('.home-floating-actions').boundingBox();
    const last = await page.locator('.date-card').last().boundingBox();
    assert.equal(after.y, before.y);
    assert.ok(last.y + last.height < after.y, 'Last record cannot scroll clear of floating controls');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await enter('quick'); await at('quick');
    const footer = await page.locator('.form-footer').boundingBox();
    assert.ok(footer.y + footer.height <= height + 1, 'Save button is below the viewport');
    await back(); await homeControlsVisible();
  }
  assert.deepEqual(errors, []);
  console.log('PASS: browser back/forward, in-page back, direct links, legacy hashes, reload, group/day context, saved records, and visible bottom controls in 5 viewport sizes.');
} finally {
  await browser.close();
}
