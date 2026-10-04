async (page) => {
  const check = (value, message) => { if (!value) throw new Error(message); };
  const origin = new URL(page.url()).origin;
  const errors = [], failures = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('requestfailed', (request) => failures.push({ url: request.url(), reason: request.failure()?.errorText }));
  await page.addInitScript(() => {
    window.pressurePolicyViolations = [];
    document.addEventListener('securitypolicyviolation', (event) => window.pressurePolicyViolations.push(event.effectiveDirective));
  });
  await page.goto(origin + `/pressure.html?audit=core-${Date.now()}`);
  await page.waitForFunction(() => document.body.dataset.pressureReady === 'true');
  const data = await (await page.request.get(origin + '/assets/generated/pressure-study-v1.json')).json();
  const browser = page.context().browser().browserType().name();
  const actual = () => page.evaluate(() => ({
    count: document.querySelector('#identified-count').textContent,
    correct: document.querySelector('#case-result').dataset.correct,
    written: document.querySelector('#written-order').value,
    chosen: document.querySelector('#chosen-label').textContent.replaceAll(' · ', ''),
    trial: Number(document.querySelector('[data-trial][aria-pressed=true]').dataset.trial),
    paths: [...document.querySelectorAll('#measured-glyph path')].map((node) => node.getAttribute('d')),
    hash: location.hash,
  }));
  const before = await actual();
  check(before.correct === 'false', 'The declared demonstration should be misread by the first rule');
  await page.getByRole('button', { name: 'Allow for pressure', exact: true }).click();
  const corrected = await actual();
  check(corrected.correct === 'true' && corrected.count === '881 / 960', 'The second rule did not recover the declared case');
  check(JSON.stringify(before.paths) === JSON.stringify(corrected.paths), 'Changing readers changed the measured reply');
  check(before.written === corrected.written && before.trial === corrected.trial, 'Changing readers changed the case');
  const levels = [];
  for (const index of [0, 1, 2]) {
    await page.locator(`[data-level="${index}"]`).click();
    const correctedCount = (await actual()).count;
    check(correctedCount === `${data.levels[index].corrected_correct} / 960`, 'Corrected count disagrees with measurements');
    await page.getByRole('button', { name: 'Nearest ideal answer', exact: true }).click();
    const nearestCount = (await actual()).count;
    check(nearestCount === `${data.levels[index].nearest_correct} / 960`, 'Nearest count disagrees with measurements');
    levels.push({ percent: data.levels[index].percent, nearestCount, correctedCount });
    await page.getByRole('button', { name: 'Allow for pressure', exact: true }).click();
  }
  const map = page.locator('#pressure-map');
  const bounds = await map.boundingBox();
  const [xmin, xmax, ymin, ymax] = data.extent;
  const scale = Math.min((bounds.width - 38) / (xmax - xmin), (bounds.height - 48) / (ymax - ymin));
  let outlier = 0;
  data.levels[2].points.forEach((point, index, points) => {
    if (point[0] ** 2 + point[1] ** 2 > points[outlier][0] ** 2 + points[outlier][1] ** 2) outlier = index;
  });
  const position = data.levels[2].points[outlier];
  await map.click({ position: { x: bounds.width / 2 + (position[0] - (xmin + xmax) / 2) * scale,
    y: bounds.height / 2 - (position[1] - (ymin + ymax) / 2) * scale - 7 } });
  check(await map.getAttribute('data-case') === String(outlier), 'Selecting a measured plot point did not open its case');
  await page.locator('#written-order').selectOption('EDCBA');
  await page.getByRole('button', { name: 'Pressure realization 8', exact: true }).click();
  const last = await actual();
  const expected = data.levels[2].points[959];
  check(last.written === 'EDCBA' && last.trial === 7 && last.chosen === data.histories[expected[3]], 'The last case was not selected exactly');
  await page.getByRole('button', { name: 'Find a misread history', exact: false }).click();
  check((await actual()).correct === 'false', 'Misread navigation selected a correct case');
  const selected = await actual();
  const [download] = await Promise.all([
    page.waitForEvent('download'), page.getByRole('button', { name: 'Keep this pair as SVG', exact: false }).click(),
  ]);
  const exportPath = `output/playwright/pressure-${browser}.svg`;
  await download.saveAs(exportPath);
  check(await download.failure() === null, 'SVG export failed');
  await page.reload();
  await page.waitForFunction(() => document.body.dataset.pressureReady === 'true');
  const restored = await actual();
  check(restored.hash === selected.hash && restored.chosen === selected.chosen && JSON.stringify(restored.paths) === JSON.stringify(selected.paths), 'The shared case did not survive reload');
  await page.locator('#written-order').focus();
  await page.keyboard.press('a');
  await page.keyboard.press('Enter');
  check(await page.locator('#written-order').evaluate((node) => node === document.activeElement), 'The native history selector lost keyboard focus');
  await page.keyboard.press('Escape');
  await page.keyboard.press('Tab');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  check(overflow === 0, 'The pressure study overflows horizontally');
  const policy = await page.evaluate(() => window.pressurePolicyViolations);
  check(policy.length === 0 && errors.length === 0 && failures.length === 0, 'A runtime, request or policy error occurred');
  await page.locator('#experiment').scrollIntoViewIfNeeded();
  await page.screenshot({ path: `output/playwright/pressure-${browser}.jpg`, type: 'jpeg', quality: 76 });
  const compact = ({ paths, ...state }) => ({ ...state, measuredRingCount: paths.length });
  return { origin, browser, viewport: page.viewportSize(), before: compact(before), corrected: compact(corrected), levels, last: compact(last),
    selected: compact(selected), restored: compact(restored), measuredReplyUnchangedAcrossReaders: true, exactSharedCaseRestoration: true,
    selectedPlotPoint: outlier, exportPath, suggestedFilename: download.suggestedFilename(), overflow,
    errors, failures, policy, scope: 'Real controls, unchanged measured reply across readers, actual cases/counts, final record, misread navigation, SVG download, shared URL reload, keyboard focus and responsive layout.' };
}
