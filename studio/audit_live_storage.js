async(page)=>{
  const check=(ok,message)=>{if(!ok)throw new Error(message);};
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.addInitScript(()=>{
    const NativeWorker=window.Worker;
    window.Worker=class extends NativeWorker{constructor(...args){super(...args);window.auditWorker=this;}};
  });
  await page.goto('http://127.0.0.1:8083/instrument.html');
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.time!==undefined);
  await page.getByRole('button',{name:'Begin silently',exact:true}).click();
  await page.getByRole('button',{name:'Record a phrase'}).click();
  const start=await page.locator('#live-sculpture').evaluate(e=>Number(e.dataset.time));
  await page.keyboard.down('t');
  await page.waitForFunction(t=>Number(document.querySelector('#live-sculpture').dataset.time)>t+2,start);
  await page.keyboard.up('t');
  await page.getByRole('button',{name:'Finish phrase'}).click();
  await page.waitForFunction(()=>document.body.dataset.phrase==='idle');
  await page.getByRole('button',{name:'Ask again'}).click();
  await page.waitForFunction(()=>document.body.dataset.phrase==='replaying');
  await page.waitForFunction(()=>document.body.dataset.phrase==='idle');
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.materialRunning==='false');
  const paused=await page.locator('#live-sculpture').evaluate(e=>({...e.dataset}));
  await page.waitForFunction(t=>document.querySelector('#recovery-note').dataset.time===t,paused.time);
  const snapshot=()=>page.evaluate(()=>new Promise(resolve=>{
    const worker=window.auditWorker;
    const receive=({data})=>{if(data.type==='snapshot'&&data.request===98765){worker.removeEventListener('message',receive);resolve(data.state);}};
    worker.addEventListener('message',receive);worker.postMessage({type:'snapshot',request:98765});
  }));
  const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value;
  const before=await snapshot();
  const comparison=await page.locator('#reply-comparison').getAttribute('data-rms-hz');
  check(before.replies.filter(Boolean).length===2&&Number(comparison)>0,'The fixture lacks two completed replies');
  await page.reload();
  await page.waitForFunction(()=>document.querySelector('#live-status').textContent.includes('has been recovered'));
  const after=await snapshot();
  const exact=JSON.stringify(canonical(before))===JSON.stringify(canonical(after));
  check(exact,'Reload changed the complete material, kept phrase or completed replies');
  check(await page.locator('#reply-comparison').isVisible()&&await page.locator('#reply-comparison').getAttribute('data-rms-hz')===comparison,'Reload did not restore the paired drawing');
  check(await page.getByRole('button',{name:'Save the paired drawing ↓',exact:true}).isEnabled(),'Recovered drawing cannot be exported');
  const stored=await page.evaluate(()=>{
    const keys=Object.keys(sessionStorage).filter(k=>k.startsWith('palimpsest-live-recovery'));
    return {keys,characters:sessionStorage.getItem(keys[0])?.length};
  });
  check(stored.keys.length===1&&stored.characters<1_500_000,'Recovery storage is not bounded to one entry');
  const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Save material ↓',exact:true}).click()]);
  const path=`output/playwright/live-recovered-with-replies-${page.context().browser().browserType().name()}.json`;
  await download.saveAs(path);
  await page.evaluate(()=>sessionStorage.removeItem('palimpsest-live-recovery-v1'));
  await page.reload();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.time==='0.00000');
  check(await page.locator('#reply-comparison').isHidden(),'Empty session retained an old paired drawing');
  await page.locator('#open-material').setInputFiles(path);
  await page.waitForFunction(()=>document.querySelector('#live-status').textContent.startsWith('Material opened'));
  check(JSON.stringify(canonical(await snapshot()))===JSON.stringify(canonical(before)),'Downloaded file did not restore the complete material and replies');
  check(await page.locator('#reply-comparison').isVisible()&&await page.locator('#reply-comparison').getAttribute('data-rms-hz')===comparison,'Downloaded file did not restore its paired drawing');
  await page.getByRole('button',{name:'New material',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.time==='0.00000');
  await page.waitForFunction(()=>document.querySelector('#recovery-note').dataset.time==='0.00000');
  await page.reload();
  await page.waitForFunction(()=>document.querySelector('#live-status').textContent.includes('has been recovered'));
  const reset=await page.locator('#live-sculpture').evaluate(e=>({...e.dataset}));
  check(Number(reset.time)===0&&Number(reset.memory)===0,'Reload resurrected the material discarded by New material');
  check(errors.length===0,'Recovery raised browser errors');
  return{browser:page.context().browser().browserType().name(),complete_state_phrase_and_replies_exact:exact,
    recovered_reply_rms_hz:Number(comparison),stored,downloaded_file_replies_exact:true,file:path,
    new_material_replaced_copy:true,reset,errors};
}
