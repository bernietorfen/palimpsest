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
  await page.keyboard.down('e');
  await page.waitForFunction(()=>Number(document.querySelector('#live-sculpture').dataset.time)>2.5);
  await page.keyboard.up('e');
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.materialRunning==='false');
  const snapshot=()=>page.evaluate(()=>new Promise(resolve=>{
    const worker=window.auditWorker;
    const receive=({data})=>{if(data.type==='snapshot'&&data.request===98765){worker.removeEventListener('message',receive);resolve(data.state);}};
    worker.addEventListener('message',receive);worker.postMessage({type:'snapshot',request:98765});
  }));
  const before=await snapshot();
  const invalid=structuredClone(before);invalid.u.fill(9999);
  await page.locator('#open-material').setInputFiles({name:'extreme-material.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(invalid))});
  await page.waitForFunction(()=>document.querySelector('#live-status').textContent.includes('operating range'));
  check(JSON.stringify(await snapshot())===JSON.stringify(before),'Rejected extreme import changed the valid material');
  const canvas=page.locator('#live-sculpture');
  await canvas.focus();await page.keyboard.press('ArrowRight');await page.keyboard.press('ArrowUp');
  const imageBefore=await canvas.screenshot();
  await canvas.evaluate(element=>{
    const extension=element.getContext('webgl2').getExtension('WEBGL_lose_context');
    if(!extension)throw new Error('Context-loss test extension is unavailable');
    window.auditContextExtension=extension;extension.loseContext();
  });
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.state==='context-lost');
  check(await page.getByRole('button',{name:'Resume',exact:true}).isDisabled(),'Resume stayed active during graphics loss');
  check(!await page.getByRole('button',{name:'Save material ↓',exact:true}).isDisabled(),'Graphics loss prevented saving intact material');
  await page.waitForTimeout(150);
  await page.evaluate(()=>window.auditContextExtension.restoreContext());
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.state==='ready');
  await page.waitForFunction(()=>document.querySelector('#live-status').textContent.startsWith('The sculpture is back'));
  const imageAfter=await canvas.screenshot();
  const exactState=JSON.stringify(await snapshot())===JSON.stringify(before);
  const exactPixels=imageBefore.equals(imageAfter);
  check(exactState&&exactPixels,'Graphics recovery changed material fields or the paused camera image');
  await page.getByRole('button',{name:'Resume',exact:true}).click();
  await page.waitForFunction(t=>Number(document.querySelector('#live-sculpture').dataset.time)>t+1,before.steps*before.config.dt);
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.materialRunning==='false');
  check(errors.length===0,'Recovery produced browser errors');
  return{browser:page.context().browser().browserType().name(),extreme_import_rejected_atomically:true,
    context_restored:true,complete_material_state_exact:exactState,paused_camera_pixels_exact:exactPixels,
    comparison_image_bytes:imageBefore.length,continuation:true,errors};
}
