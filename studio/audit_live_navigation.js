async(page)=>{
  await page.goto('http://127.0.0.1:8083/instrument.html');
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.time!==undefined);
  await page.getByRole('button',{name:'Begin silently',exact:true}).click();
  await page.keyboard.down('w');
  await page.waitForFunction(()=>Number(document.querySelector('#live-sculpture').dataset.time)>2);
  await page.keyboard.up('w');
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.materialRunning==='false');
  const before=await page.locator('#live-sculpture').evaluate(e=>({...e.dataset}));
  await page.waitForFunction(t=>document.querySelector('#recovery-note')?.dataset.time===t,before.time);
  await page.locator('.topline').getByRole('link',{name:'The film',exact:true}).click();
  await page.waitForURL('http://127.0.0.1:8083/');
  await page.goBack();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture')?.dataset.time!==undefined);
  await page.waitForFunction(()=>document.querySelector('#live-status').textContent.includes('recovered'));
  const after=await page.locator('#live-sculpture').evaluate(e=>({...e.dataset}));
  const preserved=before.time===after.time&&before.memory===after.memory&&before.wear===after.wear;
  if(!preserved)throw new Error('Back navigation did not recover the paused material');
  return{browser:page.context().browser().browserType().name(),before,after,preserved,
    navigation_type:await page.evaluate(()=>performance.getEntriesByType('navigation')[0]?.type)};
}
