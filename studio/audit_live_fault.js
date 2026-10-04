async(page)=>{
  const check=(ok,message)=>{if(!ok)throw new Error(message);};
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.addInitScript(()=>{
    const NativeWorker=window.Worker;
    window.faultAudit={frames:0,faults:0,pauses:0};
    window.Worker=class extends NativeWorker{
      constructor(url,options){
        const base=location.origin;
        const script=`import {LiveMaterial} from '${base}/live-material.js';
          const original=LiveMaterial.prototype.step;let injected=false;
          LiveMaterial.prototype.step=function(...args){const result=original.apply(this,args);if(!injected&&this.steps===42){injected=true;this.u[0]=NaN;}return result;};
          await import('${base}/live-worker.js');`;
        const blob=URL.createObjectURL(new Blob([script],{type:'text/javascript'}));
        super(blob,options);setTimeout(()=>URL.revokeObjectURL(blob),1000);
        this.addEventListener('message',({data})=>{if(data.type==='frame')window.faultAudit.frames++;if(data.type==='fault')window.faultAudit.faults++;});
      }
      postMessage(...args){if(args[0]?.type==='pause')window.faultAudit.pauses++;return super.postMessage(...args);}
    };
  });
  await page.goto('http://127.0.0.1:8083/instrument.html');
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.time!==undefined);
  await page.getByRole('button',{name:'Begin silently',exact:true}).click();
  await page.waitForFunction(()=>window.faultAudit.faults===1);
  await page.waitForFunction(()=>document.body.dataset.running==='false');
  const stopped=await page.evaluate(()=>({...window.faultAudit}));
  await page.waitForTimeout(500);
  const after=await page.evaluate(()=>({...window.faultAudit}));
  check(JSON.stringify(stopped)===JSON.stringify(after),'The stopped worker kept publishing frames or fault messages');
  check(after.faults===1&&after.pauses===1,'The fault did not stop once');
  check(await page.getByRole('button',{name:'Resume',exact:true}).isDisabled(),'An invalid material could resume');
  check(await page.getByRole('button',{name:'Save material ↓',exact:true}).isDisabled(),'An invalid material could be saved');
  check(await page.getByRole('button',{name:'Save sculpture ↓',exact:true}).isDisabled(),'An invalid material could be exported');
  await page.getByRole('button',{name:'New material',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.time==='0.00000');
  check(await page.locator('#undo-material').isHidden(),'Reset retained the invalid material as an undo state');
  await page.getByRole('button',{name:'Resume',exact:true}).click();
  await page.keyboard.down('q');
  await page.waitForFunction(()=>Number(document.querySelector('#live-sculpture').dataset.time)>1.5);
  await page.keyboard.up('q');
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.materialRunning==='false');
  const recovered=await page.locator('#live-sculpture').evaluate(e=>({...e.dataset}));
  check(Number(recovered.memory)>.01&&errors.length===0,'A new material did not recover after a stopped worker');
  await page.waitForFunction(t=>document.querySelector('#recovery-note').dataset.time===t,recovered.time);
  await page.reload();
  await page.waitForFunction(()=>document.querySelector('#live-status').textContent.includes('has been recovered'));
  const reloaded=await page.locator('#live-sculpture').evaluate(e=>({...e.dataset}));
  check(reloaded.time===recovered.time&&reloaded.memory===recovered.memory,'A numerical fault left recovery copies stalled or invalid');
  return{injected:'One NaN displacement at material step 42, by a test-only worker wrapper',stopped,after,
    no_frame_or_message_loop:true,recovered,reloaded,recovery_copy_continued:true,errors};
}
