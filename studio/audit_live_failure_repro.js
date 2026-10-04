async(page)=>{
  await page.addInitScript(()=>{
    const NativeWorker=window.Worker;
    window.failureProbe={pauses:0,frames:0,terminated:false};
    window.Worker=class extends NativeWorker{
      constructor(...args){super(...args);this.addEventListener('message',({data})=>{if(data.type==='frame')window.failureProbe.frames++;});}
      postMessage(...args){
        if(args[0]?.type==='pause'&&++window.failureProbe.pauses>=8){this.terminate();window.failureProbe.terminated=true;return;}
        return super.postMessage(...args);
      }
    };
  });
  await page.goto('http://127.0.0.1:8083/instrument.html');
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.time!==undefined);
  const fixture=await page.evaluate(async()=>{
    const {LiveMaterial}=await import('/live-material.js');
    const state=new LiveMaterial().snapshot();state.u.fill(9999);
    return JSON.stringify(state);
  });
  await page.locator('#open-material').setInputFiles({name:'unstable-material.json',mimeType:'application/json',buffer:Buffer.from(fixture)});
  await page.waitForFunction(()=>document.querySelector('#live-status').textContent.startsWith('Material opened'));
  await page.getByRole('button',{name:'Resume',exact:true}).click();
  await page.waitForFunction(()=>window.failureProbe.terminated);
  return await page.evaluate(()=>({probe:window.failureProbe,status:document.querySelector('#live-status').textContent,
    scope:'A finite but extreme imported field is accepted, then repeatedly re-enters the non-finite pause handler. The harness terminates its worker after eight pause requests.'}));
}
