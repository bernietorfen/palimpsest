async (page) => {
  const origin = 'https://site-inky-eight-42.vercel.app';
  await page.addInitScript(() => {
    window.pressureDetailedPolicy = [];
    document.addEventListener('securitypolicyviolation', (event) => window.pressureDetailedPolicy.push({
      directive: event.effectiveDirective, blocked: event.blockedURI, source: event.sourceFile,
      line: event.lineNumber, column: event.columnNumber, sample: event.sample,
    }));
  });
  await page.route('**/pressure.html?diagnose=hash', async (route) => {
    const response = await route.fetch();
    const headers = response.headers();
    headers['content-security-policy'] = headers['content-security-policy'].replace("style-src 'self';", "style-src 'self'; style-src-attr 'unsafe-hashes' 'sha256-3oFxofzq3N//6J8H86e9ul4WT2OkJrtonB66gn/TLJw=' 'report-sample';");
    await route.fulfill({ response, headers });
  });
  await page.goto(origin + '/pressure.html?diagnose=hash');
  await page.waitForFunction(() => document.body.dataset.pressureReady === 'true');
  const record = await page.evaluate(() => ({ violations: window.pressureDetailedPolicy,
    styleNodes: [...document.querySelectorAll('style,[style]')].map((node) => node.outerHTML.slice(0, 200)),
    appearance: getComputedStyle(document.querySelector('#written-order')).appearance,
    status: document.querySelector('#pressure-status').textContent }));
  record.unrelatedInlineStyle = await page.evaluate(() => {
    const node = document.createElement('span');
    node.textContent = 'Style check'; node.setAttribute('style', 'color:rgb(1,2,3)');
    document.body.append(node);
    const color = getComputedStyle(node).color;
    node.remove();
    return { color, blocked: color !== 'rgb(1, 2, 3)' };
  });
  await page.unroute('**/pressure.html?diagnose=hash');
  return record;
}
