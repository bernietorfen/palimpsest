async (page) => {
  const check = (ok, message) => { if (!ok) throw new Error(message); };
  const origin = 'http://127.0.0.1:8087';
  const local = [], external = [], errors = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.origin === origin) { local.push(url.pathname); await route.continue(); }
    else { external.push(url.href); await route.abort('internetdisconnected'); }
  });
  await page.goto(origin + '/');
  await page.waitForFunction(() => document.body.dataset.pressureReady === 'true');
  check(await page.locator('#identified-count').textContent() === '374 / 960', 'The portable study opened the wrong record');
  await page.getByRole('button', { name: 'Allow for pressure', exact: true }).click();
  check(await page.locator('#identified-count').textContent() === '881 / 960', 'The portable second reader failed');
  await page.locator('#written-order').selectOption('EDCBA');
  await page.getByRole('button', { name: 'Pressure realization 8', exact: true }).click();
  await page.getByRole('button', { name: 'Up to 1%', exact: true }).click();
  check(await page.locator('#identified-count').textContent() === '960 / 960', 'The portable severity control failed');
  const [download] = await Promise.all([
    page.waitForEvent('download'), page.getByRole('button', { name: 'Keep this pair as SVG', exact: false }).click(),
  ]);
  await download.saveAs('output/playwright/pressure-portable.svg');
  check(await download.failure() === null, 'The portable vector export failed');
  const hash = new URL(page.url()).hash;
  await page.reload();
  await page.waitForFunction(() => document.body.dataset.pressureReady === 'true');
  check(new URL(page.url()).hash === hash && await page.locator('#written-order').inputValue() === 'EDCBA', 'The portable exact case did not survive reload');
  check(external.length === 0 && errors.length === 0, 'The portable explorer required an external dependency or raised an error');
  await page.unroute('**/*');
  const blocked = await page.evaluate(async () => {
    try { await fetch('https://example.com/', { mode: 'no-cors', signal: AbortSignal.timeout(3000) }); return false; }
    catch (error) { return error.name === 'TypeError'; }
  });
  check(blocked, 'The browser was not demonstrably disconnected from the external network');
  return { origin, localRequests: [...new Set(local)].sort(), externalDependencyRequests: external,
    externalConnectivityBlocked: blocked, errors, restoredHash: hash,
    downloaded: download.suggestedFilename(), scope: 'Actual extracted portable ZIP behind a disabled external proxy. Case selection, reading rules, SVG export and reload work entirely from the local archive.' };
}
