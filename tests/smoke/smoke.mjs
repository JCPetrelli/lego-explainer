// Headless-Chrome smoke test for a built viewer page.
// Usage: node smoke.mjs <build.html> <screenshot-prefix> <piece-id>

import puppeteer from 'puppeteer-core';
const [,, file, shotPrefix, pieceId] = process.argv;
const browser = await puppeteer.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--window-size=1400,900'],
  defaultViewport: { width: 1400, height: 900 },
});
const page = await browser.newPage();
const problems = [];
page.on('console', m => { if (['error', 'warning'].includes(m.type())) problems.push(`${m.type()}: ${m.text()}`); });
page.on('pageerror', e => problems.push(`pageerror: ${e.message}`));
await page.goto('file://' + file);
await page.waitForFunction('window.__legoReady === true', { timeout: 15000 });
await new Promise(r => setTimeout(r, 1200));
// park the pointer off-model
await page.mouse.move(5, 5);

await page.screenshot({ path: `${shotPrefix}-1-assembled.png` });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const hoverAt = async (id) => {
  const p = await page.evaluate(i => window.__lego.screenPos(i), id);
  await page.mouse.move(p.x, p.y);
  await sleep(150);
  return p;
};
const p = await hoverAt(pieceId);
const label = await page.$eval('#hover-label', el => ({ hidden: el.hidden, text: el.textContent }));
const leader = await page.$eval('#leader', el => !el.hasAttribute('hidden'));
await page.screenshot({ path: `${shotPrefix}-2-hover.png` });
await page.mouse.click(p.x, p.y);
await sleep(150);
const popup = await page.$eval('#popup', el => ({ hidden: el.hidden, text: el.innerText }));
await page.screenshot({ path: `${shotPrefix}-3-popup.png` });
await page.keyboard.press('Escape');
await page.keyboard.press('e');
await sleep(1200);
const s2 = await page.evaluate(() => ({ state: window.__lego.state, finite: window.__lego.positionsFinite() }));
const labels = await page.$$eval('.group-label', els => els.filter(e => !e.hidden).length);
await page.screenshot({ path: `${shotPrefix}-4-exploded.png` });
const q = await hoverAt(pieceId);
await page.mouse.click(q.x, q.y);
await sleep(1200);
const s3 = await page.evaluate(() => ({ state: window.__lego.state, group: window.__lego.selectedGroup, finite: window.__lego.positionsFinite() }));
await page.screenshot({ path: `${shotPrefix}-5-group.png` });
await page.keyboard.press('Escape');
await sleep(800);
const back = await page.evaluate(() => window.__lego.state);
console.log(JSON.stringify({ label, leader, popup, s2, labels, s3, back, problems }, null, 1));
await browser.close();
