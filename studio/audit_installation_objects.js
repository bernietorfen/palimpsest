async (page) => {
  const origin = 'http://127.0.0.1:8088';
  const errors = [], external = [], models = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin === origin) {
      if (url.pathname.endsWith('.glb')) models.push(url.pathname);
      await route.continue();
    } else { external.push(url.href); await route.abort('internetdisconnected'); }
  });
  await page.setViewportSize({width:393, height:852});
  await page.goto(origin + '/');
  await page.waitForFunction(() => document.querySelectorAll('#download-list a').length === 12);
  await page.locator('#download-list').scrollIntoViewIfNeeded();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  if (overflow > 0) throw new Error('The portable catalog overflows its mobile viewport');
  for (const state of ['000','165','358']) {
    await page.locator(`[data-sculpture="${state}"]`).click();
    await page.waitForFunction(() => document.querySelector('#sculpture-status').textContent === '');
    await page.locator('#close-sculpture').click();
  }
  if (models.length !== 3 || errors.length || external.length) throw new Error(JSON.stringify({models, errors, external}));
  return {viewport:page.viewportSize(), overflow, models, errors, externalDependencies:external,
    scope:'All three actual local glTF sculptures opened through the extracted installation, with the portable catalog checked at a phone-sized viewport.'};
}
