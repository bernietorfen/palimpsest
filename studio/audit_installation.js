async (page) => {
  const check = (ok, message) => { if (!ok) throw new Error(message); };
  const origin = 'http://127.0.0.1:8088';
  const local = [], external = [], errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin === origin) { local.push(url.pathname); await route.continue(); }
    else { external.push(url.href); await route.abort('internetdisconnected'); }
  });
  await page.goto(origin + '/');
  await page.waitForFunction(() => document.querySelectorAll('#download-list a').length === 11);
  const book = await page.locator('#notebook .arrow-link').getAttribute('href');
  check(book === '/assets/generated/palimpsest-complete-notebook.pdf', 'The notebook still requires an external connection');
  const response = await page.request.head(origin + book);
  check(response.status() === 200 && Number(response.headers()['content-length']) === 10477076, 'The complete local notebook is missing');
  await page.locator('#enter-film').click();
  await page.waitForFunction(() => document.querySelector('#main-film').currentTime > 1);
  const film = await page.locator('#main-film').evaluate(video => {
    const state = {time:video.currentTime, duration:video.duration, width:video.videoWidth, height:video.videoHeight};
    video.pause(); return state;
  });
  check(film.width === 1920 && Math.abs(film.duration - 432) < .1, 'The full viewing film is not playable');
  await page.goto(origin + '/atlas.html');
  await page.waitForFunction(() => !document.querySelector('#probe-play').disabled);
  check(await page.locator('.history-glyph').count() === 120, 'The complete audible atlas is missing');
  await page.locator('#probe-play').click();
  await page.waitForFunction(() => document.querySelector('#probe-0').currentTime > 1);
  const atlas = await page.locator('#probe-0').evaluate(audio => ({time:audio.currentTime, duration:audio.duration, source:audio.currentSrc}));
  await page.locator('#probe-play').click();
  await page.goto(origin + '/pressure.html');
  await page.waitForFunction(() => document.body.dataset.pressureReady === 'true');
  await page.getByRole('button', {name:'Allow for pressure', exact:true}).click();
  check(await page.locator('#identified-count').textContent() === '881 / 960', 'The pressure record is incomplete');
  const [drawing] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', {name:'Keep this pair as SVG', exact:false}).click()]);
  await drawing.saveAs('output/playwright/installation-pressure.svg');
  check(await drawing.failure() === null, 'The portable drawing export failed');
  await page.goto(origin + '/instrument.html');
  await page.waitForFunction(() => document.querySelector('#live-sculpture').dataset.state === 'ready' && document.querySelector('#live-sculpture').dataset.time !== undefined);
  await page.locator('#begin-sound').click();
  await page.keyboard.down('q');
  await page.waitForFunction(() => Number(document.querySelector('#live-sculpture').dataset.time) > 4);
  await page.keyboard.up('q');
  const written = await page.locator('#live-sculpture').evaluate(canvas => ({...canvas.dataset}));
  check(Number(written.memory) > .1 && Number(written.audioPeak) > .005, 'The portable material did not write and synthesize');
  await page.locator('#pause-material').click();
  await page.waitForFunction(() => document.querySelector('#live-sculpture').dataset.materialRunning === 'false' && document.querySelector('#recovery-note').dataset.saved === 'true');
  const paused = await page.locator('#live-sculpture').evaluate(canvas => ({...canvas.dataset}));
  await page.reload();
  await page.waitForFunction(() => Number(document.querySelector('#live-sculpture').dataset.time) > 4);
  const recovered = await page.locator('#live-sculpture').evaluate(canvas => ({...canvas.dataset}));
  check(paused.time === recovered.time && paused.memory === recovered.memory && paused.wear === recovered.wear, 'The portable tab did not recover the retained material');
  check(errors.length === 0 && external.length === 0, 'An experience requested an external dependency or raised an error');
  await page.unroute('**/*');
  const blocked = await page.evaluate(async () => {
    try { await fetch('https://example.com/', {mode:'no-cors', signal:AbortSignal.timeout(3000)}); return false; }
    catch (error) { return error.name === 'TypeError'; }
  });
  check(blocked, 'The test browser retained an external connection');
  return {film, atlas, notebookStatus:response.status(), written, paused, recovered,
    localRequests:[...new Set(local)].sort(), externalDependencyRequests:external,
    externalConnectivityBlocked:blocked, errors,
    scope:'Extracted installation behind a dead external proxy. Film playback, recorded atlas audio, measured SVG export, live material synthesis and tab recovery. Signal/playback checks, no perceptual listening claim.'};
}
