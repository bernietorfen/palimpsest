async(page)=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.addInitScript(()=>{
    Object.defineProperty(window,'sessionStorage',{get(){throw new DOMException('Test denies storage','SecurityError');}});
  });
  await page.goto('http://127.0.0.1:8083/instrument.html');
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.time!==undefined);
  await page.getByRole('button',{name:'Begin silently',exact:true}).click();
  await page.keyboard.down('q');
  await page.waitForFunction(()=>Number(document.querySelector('#live-sculpture').dataset.time)>1.5);
  await page.keyboard.up('q');
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.materialRunning==='false');
  await page.waitForFunction(()=>document.querySelector('#recovery-note').dataset.saved==='false');
  const state=await page.locator('#live-sculpture').evaluate(e=>({...e.dataset}));
  if(Number(state.memory)<.01||!await page.getByRole('button',{name:'Save material ↓',exact:true}).isEnabled()||errors.length)throw new Error('Storage denial prevented ordinary material use or file saving');
  return{storage:'SecurityError injected on sessionStorage access',state,
    note:await page.locator('#recovery-note').textContent(),file_save_available:true,errors};
}
