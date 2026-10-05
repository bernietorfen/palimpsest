// Shared actual-media control checks. Run only on the authorized remote host.
// Successful decoding and transport are not perceptual listening evidence.
import assert from 'node:assert/strict';

async function filmState(page){
  return page.locator('#river-film').evaluate(video=>({time:video.currentTime,paused:video.paused,source:new URL(video.currentSrc).pathname,width:video.videoWidth,height:video.videoHeight,volume:video.volume,muted:video.muted,captions:video.textTracks[0]?.mode,stage:document.querySelector('.film-stage').dataset.videoState}));
}

export async function checkQualityPlayback(page,{finalDimensions=false}={}){
  await page.locator('#river-film').evaluate(video=>new Promise(resolve=>{
    video.pause();video.volume=.63;video.muted=true;video.textTracks[0].mode='showing';
    if(Math.abs(video.currentTime-104)<.001){resolve();return;}
    video.addEventListener('seeked',resolve,{once:true});video.currentTime=104;
  }));
  const initial=await filmState(page);
  await page.locator('[data-film-quality="compact"]').focus();await page.keyboard.press('Enter');
  await page.waitForFunction(()=>{const video=document.querySelector('#river-film');return video.currentSrc.endsWith('/river-compact.mp4')&&video.readyState>=2&&!video.seeking&&Math.abs(video.currentTime-104)<.06&&document.querySelector('.film-stage').dataset.videoState==='paused';});
  const paused=await filmState(page);
  assert.equal(paused.paused,true);assert.equal(paused.muted,true);assert.equal(paused.volume,initial.volume);assert.equal(paused.captions,'showing');
  if(finalDimensions){assert.equal(paused.width,1280);assert.equal(paused.height,720);}
  assert.equal(await page.locator('#film-separate').getAttribute('href'),'/assets/generated/river-compact.mp4');
  assert.equal(await page.locator('[data-film-quality="compact"]').getAttribute('aria-pressed'),'true');
  assert.equal(await page.locator('.work-links a[download]').first().getAttribute('href'),'/assets/generated/river-viewing.mp4');
  await page.locator('#river-film').evaluate(video=>{video.muted=false;video.play();});
  await page.waitForFunction(()=>document.querySelector('#river-film').currentTime>104.2);
  const before=await filmState(page);
  await page.locator('[data-film-quality="full"]').focus();await page.keyboard.press('Space');
  await page.waitForFunction(time=>{const video=document.querySelector('#river-film');return video.currentSrc.endsWith('/river-viewing.mp4')&&!video.paused&&!video.seeking&&video.currentTime>=time&&document.querySelector('.film-stage').dataset.videoState==='playing';},before.time);
  const resumed=await filmState(page);
  assert.ok(resumed.time<before.time+3,'Changing quality does not lose the held point');
  assert.equal(resumed.muted,false);assert.equal(resumed.volume,initial.volume);assert.equal(resumed.captions,'showing');
  if(finalDimensions){assert.equal(resumed.width,1920);assert.equal(resumed.height,1080);}
  await page.locator('#river-film').evaluate(video=>video.pause());
  const held=(await filmState(page)).time;
  await page.evaluate(()=>{document.querySelector('[data-film-quality="compact"]').click();document.querySelector('[data-film-quality="full"]').click();});
  await page.waitForFunction(time=>{const video=document.querySelector('#river-film');return video.currentSrc.endsWith('/river-viewing.mp4')&&video.readyState>=2&&!video.seeking&&video.paused&&Math.abs(video.currentTime-time)<.06&&document.querySelector('.film-stage').dataset.videoState==='paused';},held);
  return{pausedCompact:paused,playingFull:resumed,rapidLatestChoice:await filmState(page),scope:finalDimensions?'Actual final dimensions and manual switching checked':'Two media URLs mapped to a declared control draft; quality transport/state checked, not final encoding'};
}

export async function checkListeningPlayback(page){
  const media=await page.locator('.listening-excerpt audio').evaluateAll(nodes=>nodes.map(audio=>({id:audio.id,controls:audio.controls,preload:audio.preload,source:new URL(audio.src).pathname})));
  assert.equal(media.length,2);assert.ok(media.every(audio=>audio.controls&&audio.preload==='none'));
  await page.locator('#river-film').evaluate(video=>{video.play().catch(()=>{});});
  await page.waitForFunction(()=>!document.querySelector('#river-film').paused);
  await page.locator('#listen-opening').evaluate(audio=>{audio.play().catch(()=>{});});
  await page.waitForFunction(()=>document.querySelector('#listen-opening').currentTime>.25);
  assert.equal(await page.locator('#river-film').evaluate(video=>video.paused),true);
  const opening=await page.locator('#listen-opening').evaluate(audio=>({duration:audio.duration,time:audio.currentTime,readyState:audio.readyState}));
  assert.ok(Math.abs(opening.duration-12)<.05);
  await page.locator('#listen-return').evaluate(audio=>{audio.play().catch(()=>{});});
  await page.waitForFunction(()=>document.querySelector('#listen-return').currentTime>.25);
  assert.equal(await page.locator('#listen-opening').evaluate(audio=>audio.paused),true);
  const returned=await page.locator('#listen-return').evaluate(audio=>({duration:audio.duration,time:audio.currentTime,readyState:audio.readyState}));
  assert.ok(Math.abs(returned.duration-12)<.05);
  await page.locator('#river-film').evaluate(video=>{video.play().catch(()=>{});});
  await page.waitForFunction(()=>!document.querySelector('#river-film').paused);
  assert.ok((await page.locator('.listening-excerpt audio').evaluateAll(nodes=>nodes.map(audio=>audio.paused))).every(Boolean));
  await page.locator('#listen-return').evaluate(audio=>{audio.play().catch(()=>{});});
  await page.waitForFunction(()=>!document.querySelector('#listen-return').paused);
  await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));delete document.hidden;});
  assert.ok((await page.locator('#river-film,.listening-excerpt audio').evaluateAll(nodes=>nodes.map(media=>media.paused))).every(Boolean));
  await page.locator('#listen-return').evaluate(audio=>{audio.currentTime=11.8;audio.play();});
  await page.waitForFunction(()=>document.querySelector('#listen-return').ended);
  for(const item of media){
    const response=await page.request.head(new URL(item.source,page.url()).href);
    assert.equal(response.status(),200);assert.match(response.headers()['content-type'],/audio\/|video\/mp4/);
  }
  return{media,opening,returned,mutualPause:true,hiddenPagePause:true,nativeEnd:true,downloadsReachable:true,scope:'Actual approved AAC excerpts, native controls and programmatic media transport; synthetic visibility transition. No perceptual audition.'};
}
