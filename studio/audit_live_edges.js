async(page)=>{
  const check=(ok,message)=>{if(!ok)throw new Error(message);};
  await page.goto('http://127.0.0.1:8083/instrument.html');
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.time!==undefined);
  await page.getByRole('button',{name:'Begin silently',exact:true}).click();
  await page.getByRole('button',{name:'Record a phrase'}).click();
  await page.waitForFunction(()=>document.body.dataset.phrase==='recording');
  await page.keyboard.down('r');
  await page.waitForFunction(()=>Number(document.querySelector('#live-sculpture').dataset.time)>1.5);
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.keyboard.up('r');
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.materialRunning==='false');
  const kept=await page.locator('#phrase-clock').textContent();
  check(kept.includes('seconds kept'),'Pausing discarded the captured gesture');
  const before=await page.locator('#live-sculpture').evaluate(e=>({...e.dataset}));
  await page.locator('#open-material').setInputFiles({name:'invalid-material.json',mimeType:'application/json',buffer:Buffer.from('{"format":"not-a-material"}')});
  await page.waitForFunction(()=>document.querySelector('#live-status').textContent.includes('not a PALIMPSEST'));
  const after=await page.locator('#live-sculpture').evaluate(e=>({...e.dataset}));
  check(before.time===after.time&&before.memory===after.memory&&before.wear===after.wear,'Rejected import changed the material');
  await page.getByRole('button',{name:'Resume',exact:true}).click();
  await page.waitForFunction(()=>document.body.dataset.running==='true');
  await page.getByRole('button',{name:'Ask again'}).click();
  await page.waitForFunction(()=>document.body.dataset.phrase==='replaying');
  await page.waitForFunction(()=>document.body.dataset.phrase==='idle');
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.materialRunning==='false');
  return{kept,rejected_import_preserved:{time:before.time,memory:before.memory,wear:before.wear},partial_phrase_replayed:true};
}
