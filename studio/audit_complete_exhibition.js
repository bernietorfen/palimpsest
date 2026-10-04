async (page) => {
  const errors = [], failures = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('requestfailed', request => failures.push({url:request.url(), error:request.failure()?.errorText}));
  await page.addInitScript(() => {
    window.__completePolicy = [];
    document.addEventListener('securitypolicyviolation', event => window.__completePolicy.push({directive:event.violatedDirective, uri:event.blockedURI}));
  });
  const base = new URL(page.url()).origin;
  await page.goto(`${base}/?edition-proof=${Date.now()}`, {waitUntil:'domcontentloaded'});
  await page.waitForFunction(() => document.querySelectorAll('#download-list a').length === 12);
  const notebook = page.locator('#notebook');
  await notebook.scrollIntoViewIfNeeded();
  await notebook.locator('img').evaluate(image => image.decode());
  const heading = await notebook.locator('.arrow-link').innerText();
  const href = await notebook.locator('.arrow-link').getAttribute('href');
  if (!heading.includes('24 pages') || !href.endsWith('/v1.3.0/palimpsest-complete-notebook.pdf')) throw new Error('The complete notebook is not offered');
  const entries = await page.locator('#download-list a').evaluateAll(links => links.map(link => ({label:link.textContent, url:link.href})));
  const verified = await Promise.all(entries.map(async entry => {
    const response = await page.request.head(entry.url, {timeout:60000});
    if (response.status() !== 200) throw new Error(`Catalog link failed: ${entry.label} / ${response.status()}`);
    return {...entry, status:response.status(), contentType:response.headers()['content-type']};
  }));
  await page.locator('#download-list').scrollIntoViewIfNeeded();
  const state = await page.evaluate(() => ({width:innerWidth, scrollWidth:document.documentElement.scrollWidth, policy:window.__completePolicy}));
  if (state.scrollWidth > state.width || errors.length || failures.length || state.policy.length) throw new Error(JSON.stringify({errors, failures, state}));
  return {notebook:heading, catalog:verified, errors, failures, ...state};
}
