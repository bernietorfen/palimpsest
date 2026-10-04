async (page) => {
  const check = (condition, message) => { if (!condition) throw new Error(message); };
  await page.goto('http://127.0.0.1:8083/atlas.html');
  await page.getByRole('button', {name:'Hear the question'}).waitFor({state:'visible'});
  await page.waitForFunction(() => !document.querySelector('#probe-play').disabled);
  const initial = await page.evaluate(() => ({
    audioSources:[...document.querySelectorAll('audio')].map(a=>a.getAttribute('src')),
    mediaRequests:performance.getEntriesByType('resource').filter(e=>e.name.endsWith('.m4a')).length,
    historyCount:document.querySelectorAll('.history-glyph').length,
    overflow:document.documentElement.scrollWidth-innerWidth
  }));
  check(initial.audioSources.every(x=>x===null) && initial.mediaRequests===0,'audio loaded before an explicit request');
  check(initial.historyCount===120 && initial.overflow===0,'initial atlas geometry or inventory failed');
  await page.getByRole('combobox',{name:'First history, gesture 1',exact:true}).selectOption('B');
  const swap = await page.evaluate(() => location.hash);
  check(swap==='#BACDE-EDCBA','changing a letter did not swap its previous position');
  await page.getByRole('button',{name:'The same last three gestures',exact:true}).click();
  const earlier = await page.evaluate(() => ({hash:location.hash,metric:document.querySelector('#pair-distance').textContent}));
  check(earlier.hash==='#BACDE-ABCDE','same-ending comparison changed the ending');
  await page.getByRole('button',{name:'The closest answer',exact:true}).click();
  const nearest = await page.evaluate(async () => {
    const data=await (await fetch('/assets/generated/histories.json')).json();
    const [a,b]=location.hash.slice(1).split('-');
    const i=data.cases.findIndex(x=>x.label===a),j=data.cases.findIndex(x=>x.label===b);
    return {pair:[a,b],distance:data.distances[i][j],minimum:Math.min(...data.distances[i].filter((_,k)=>k!==i))};
  });
  check(nearest.distance===nearest.minimum,'nearest answer does not match the recorded distance matrix');
  await page.getByRole('combobox',{name:'Ending in',exact:true}).selectOption('E');
  const filter = await page.locator('.history-glyph:not([hidden])').evaluateAll(elements=>elements.map(e=>e.dataset.history));
  check(filter.length===24 && filter.every(x=>x.endsWith('E')),'ending filter is incomplete or incorrect');
  const first=page.locator('.history-glyph:not([hidden])').first();
  await first.focus();
  await page.keyboard.press('ArrowRight');
  const keyboardTarget=await page.evaluate(()=>document.activeElement.dataset.history);
  await page.keyboard.press('Enter');
  const keyboardSelection=await page.evaluate(()=>location.hash.slice(1).split('-')[0]);
  check(keyboardTarget===filter[1] && keyboardSelection===filter[1],'keyboard atlas navigation failed');
  await page.getByRole('button',{name:'Hear the question'}).click();
  await page.waitForFunction(()=>document.querySelector('#probe-0').currentTime>.5);
  await page.getByRole('button',{name:'Hear second',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#probe-0').muted);
  const playback=await page.evaluate(()=>[...document.querySelectorAll('audio')].map(a=>({time:a.currentTime,paused:a.paused,muted:a.muted,volume:a.volume,ready:a.readyState})));
  check(playback.every(a=>!a.paused && a.ready>=2) && playback[0].muted && !playback[1].muted,'paired playback or switching failed');
  check(Math.abs(playback[0].time-playback[1].time)<.15,'paired audio drift exceeded the guard');
  await page.getByRole('button',{name:'Pause the question'}).click();
  const slider=page.getByRole('slider',{name:'Probe position, in seconds',exact:true});
  await slider.focus();
  await page.keyboard.press('End');
  await page.waitForFunction(()=>[...document.querySelectorAll('audio')].every(a=>!a.seeking && a.currentTime>13.85));
  const end=await page.evaluate(()=>[...document.querySelectorAll('audio')].map(a=>({time:a.currentTime,paused:a.paused})));
  await page.keyboard.press('Home');
  await page.waitForFunction(()=>[...document.querySelectorAll('audio')].every(a=>!a.seeking && a.currentTime<.01));
  const home=await page.evaluate(()=>[...document.querySelectorAll('audio')].map(a=>({time:a.currentTime,paused:a.paused})));
  check(end.every(a=>a.paused) && home.every(a=>a.paused),'paused seeking restarted playback');
  await page.getByRole('combobox',{name:'First history, gesture 3',exact:true}).selectOption('A');
  const cleanup=await page.evaluate(()=>[...document.querySelectorAll('audio')].map(a=>({src:a.getAttribute('src'),paused:a.paused})));
  check(cleanup.every(a=>a.src===null && a.paused),'changing a history retained the previous audio source');
  return {initial,swap,earlier,nearest,filtered:filter.length,keyboardTarget,playback,end,home,cleanup,
    browser:page.context().browser().browserType().name(),viewport:page.viewportSize(),
    scope:'Actual browser interactions and media state; no perceptual listening claim.'};
}
