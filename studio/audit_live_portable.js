async(page)=>{
  const check=(ok,message)=>{if(!ok)throw new Error(message);};
  const requests=[],external=[],errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(url.origin==='http://127.0.0.1:8085'){requests.push(url.pathname);await route.continue();}
    else{external.push(url.origin);await route.abort('internetdisconnected');}
  });
  await page.goto('http://127.0.0.1:8085/');
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.time!==undefined);
  await page.getByRole('button',{name:'Begin with sound'}).click();
  await page.waitForFunction(()=>document.body.dataset.running==='true');
  await page.keyboard.down('q');
  await page.waitForFunction(()=>Number(document.querySelector('#live-sculpture').dataset.time)>2.5);
  await page.keyboard.up('q');
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.materialRunning==='false');
  const freshPlayed=await page.locator('#live-sculpture').evaluate(e=>({...e.dataset}));
  check(Number(freshPlayed.memory)>.01&&Number(freshPlayed.audioPeak)>.005,'Portable material or synthesis did not run');
  await page.locator('#open-material').setInputFiles('artwork/live-proof-001/portable/examples/first-dialogue/material.json');
  await page.waitForFunction(()=>document.querySelector('#live-status').textContent.startsWith('Material opened'));
  const imported=await page.locator('#live-sculpture').evaluate(e=>({...e.dataset}));
  await page.getByRole('button',{name:'Resume',exact:true}).click();
  await page.waitForFunction(()=>document.body.dataset.running==='true');
  await page.getByRole('button',{name:'Ask again'}).click();
  await page.waitForFunction(()=>document.body.dataset.phrase==='replaying');
  await page.waitForFunction(()=>document.body.dataset.phrase==='idle');
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  check(external.length===0&&errors.length===0,'Portable edition requested an external dependency or raised an error');
  await page.unroute('**/*');
  return{origin:'http://127.0.0.1:8085',freshPlayed,imported,local_requests:[...new Set(requests)].sort(),external_requests:external,errors,
    scope:'Actual standalone bundle with external network requests blocked. Live sound, writing, included material import and kept-phrase replay passed.'};
}
