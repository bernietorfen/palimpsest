async(page)=>{
  const check=(ok,message)=>{if(!ok)throw new Error(message);};
  const origin='https://site-inky-eight-42.vercel.app';
  const errors=[],failures=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('requestfailed',request=>failures.push({url:request.url(),error:request.failure()?.errorText}));
  await page.addInitScript(()=>{
    window.policyViolations=[];
    document.addEventListener('securitypolicyviolation',event=>window.policyViolations.push({directive:event.effectiveDirective,blocked:event.blockedURI}));
  });
  await page.goto(origin+'/');
  const feature=page.locator('.live-feature');
  check(await feature.count()===1,'The exhibition does not introduce the playable edition');
  await feature.scrollIntoViewIfNeeded();
  await feature.locator('img').evaluate(image=>image.decode());
  check(await feature.locator('img').evaluate(e=>e.complete&&e.naturalWidth>0),'Live material image failed to load');
  await page.locator('.topline nav').getByRole('link',{name:'Play',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture')?.dataset.time!==undefined);
  check(page.url()===origin+'/instrument.html','Play navigation did not reach the instrument');
  await page.getByRole('button',{name:'Begin with sound'}).click();
  await page.waitForFunction(()=>document.body.dataset.running==='true');
  await page.getByRole('button',{name:'Record a phrase'}).click();
  await page.waitForFunction(()=>document.body.dataset.phrase==='recording');
  const start=await page.locator('#live-sculpture').evaluate(e=>Number(e.dataset.time));
  await page.keyboard.down('q');
  await page.waitForFunction(t=>Number(document.querySelector('#live-sculpture').dataset.time)>t+1.5,start);
  await page.keyboard.up('q');
  await page.keyboard.down('e');
  await page.waitForFunction(t=>Number(document.querySelector('#live-sculpture').dataset.time)>t+3,start);
  await page.keyboard.up('e');
  await page.getByRole('button',{name:'Finish phrase'}).click();
  await page.waitForFunction(()=>document.body.dataset.phrase==='idle');
  await page.getByRole('button',{name:'Ask again'}).click();
  await page.waitForFunction(()=>document.body.dataset.phrase==='replaying');
  await page.waitForFunction(()=>document.body.dataset.phrase==='idle');
  await page.locator('#reply-comparison').waitFor({state:'visible'});
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.materialRunning==='false');
  const state=await page.locator('#live-sculpture').evaluate(e=>({...e.dataset}));
  const comparison=await page.locator('#reply-comparison').evaluate(e=>({rmsHz:Number(e.dataset.rmsHz),paths:e.querySelectorAll('path').length}));
  check(Number(state.memory)>.01&&Number(state.audioPeak)>.005,'Deployed writing or audio synthesis did not run');
  check(comparison.rmsHz>.001&&comparison.paths===8,'Deployed repeated phrase did not produce paired replies');
  const browser=page.context().browser().browserType().name();
  const saved=[];
  for(const [name,extension] of [['Save material ↓','json'],['Save the paired drawing ↓','svg'],['Save sculpture ↓','stl']]){
    const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name,exact:true}).click()]);
    const path=`output/playwright/public-live-${browser}.${extension}`;
    await download.saveAs(path);
    check(await download.failure()===null,`Failed ${extension} download`);
    saved.push({name:download.suggestedFilename(),path});
  }
  await page.locator('#open-material').setInputFiles(`output/playwright/public-live-${browser}.json`);
  await page.waitForFunction(()=>document.querySelector('#live-status').textContent.startsWith('Material opened'));
  const restored=await page.locator('#live-sculpture').evaluate(e=>({...e.dataset}));
  check(restored.time===state.time&&restored.memory===state.memory&&restored.wear===state.wear,'Deployed file import changed the saved state');
  const standalone=await page.locator('.portable-edition a').getAttribute('href');
  check(standalone==='https://github.com/bernietorfen/palimpsest/releases/download/v1.1.1/palimpsest-live-instrument.zip','Standalone download does not target the verified release');
  const policyViolations=await page.evaluate(()=>window.policyViolations);
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
  check(overflow===0&&errors.length===0&&policyViolations.length===0,'Browser, layout or content-security-policy failure');
  check(failures.length===0,'A deployment request failed');
  return{origin,browser,viewport:page.viewportSize(),state,comparison,restored,saved,standalone,overflow,errors,failures,policyViolations,
    scope:'Anonymous production: exhibition navigation, worker, actual gestures, AudioWorklet meter, phrase replay, paired SVG, JSON/STL downloads and JSON import. No perceptual listening claim.'};
}
