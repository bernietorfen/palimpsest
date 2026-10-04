async (page) => {
  const check = (value, message) => { if (!value) throw new Error(message); };
  const origin = new URL(page.url()).origin;
  const errors = [];
  let phase = 'initial';
  page.on('pageerror', (error) => errors.push({ phase, message: error.message, stack: error.stack }));
  await page.goto(origin + `/pressure.html?audit=edges-${Date.now()}#10-EDCBA-8-corrected`);
  await page.waitForFunction(() => document.body.dataset.pressureReady === 'true');
  await page.getByRole('button', { name: 'Nearest ideal answer', exact: true }).click();
  await page.getByRole('button', { name: 'Allow for pressure', exact: true }).click();
  check(await page.locator('#pressure-map').getAttribute('aria-pressed') === null, 'The graphic received a button state');
  await page.addScriptTag({ path: '.tools/browser/node_modules/axe-core/axe.min.js' });
  const accessibility = await page.evaluate(async () => {
    const result = await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] } });
    return { violations: result.violations.map((item) => ({ id: item.id, impact: item.impact,
      nodes: item.nodes.map((node) => ({ target: node.target, summary: node.failureSummary })) })),
      incomplete: result.incomplete.map((item) => item.id) };
  });
  check(accessibility.violations.length === 0, 'The accessibility scan found a violation: ' + JSON.stringify(accessibility));
  phase = 'invalid-link';
  await page.goto(origin + '/pressure.html?audit=edges-invalid#10-AAAAA-9-unrecognized');
  await page.waitForFunction(() => document.body.dataset.pressureReady === 'true');
  check(page.url().endsWith('#10-ABCDE-3-nearest'), 'An invalid shared case was not replaced with the declared example');
  phase = 'injected-truncation';
  await page.route('**/pressure-glyphs-v1.bin', (route) => route.fulfill({ status: 200, contentType: 'application/octet-stream', body: 'short' }));
  await page.reload();
  await page.waitForFunction(() => document.body.dataset.pressureReady === 'error');
  check((await page.locator('#pressure-status').textContent()).includes('incomplete'), 'A truncated glyph record did not explain the failure');
  check(await page.locator('#export-pressure').isDisabled(), 'Export was enabled with incomplete measurements');
  check(await page.locator('.result-table-wrap table').isVisible(), 'The static results disappeared after a data failure');
  await page.unroute('**/pressure-glyphs-v1.bin');
  phase = 'recovered';
  await page.reload();
  await page.waitForFunction(() => document.body.dataset.pressureReady === 'true');
  check(await page.locator('#export-pressure').isEnabled(), 'Reload did not recover from a temporary data failure');
  check(errors.length === 0, 'An uncaught error occurred: ' + JSON.stringify(errors));
  return { browser: page.context().browser().browserType().name(), viewport: page.viewportSize(),
    accessibility, invalidSharedCaseRecovered: true, truncatedRecordRejected: true,
    staticResultsRemain: true, reloadRecovered: true, errors };
}
