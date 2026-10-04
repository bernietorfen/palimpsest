// Record the real worker command order around rapid cut, pause and motion reset.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {webkit} from '../.tools/browser/node_modules/playwright/index.mjs';
const output=process.argv[2],base=process.argv[3];if(!output||fs.existsSync(output))throw new Error('New evidence directory required');fs.mkdirSync(output,{recursive:true});
const browser=await webkit.launch();const cases=[];
try{
 for(let attempt=0;attempt<3;attempt++){
  const context=await browser.newContext({viewport:{width:1440,height:1080},reducedMotion:'reduce'});
  await context.addInitScript(()=>{
   window.workerTrace=[];const record=item=>{window.workerTrace.push({t:performance.now(),...item});if(window.workerTrace.length>160)window.workerTrace.shift();};
   const Native=window.Worker;window.Worker=class extends Native{constructor(...args){super(...args);let last='';this.addEventListener('message',e=>{const d=e.data;if(d.type==='frame'){const key=[d.running,d.phase].join('|');if(key!==last){last=key;record({event:'frame',running:d.running,phase:d.phase,time:d.diagnostics.time});}}else if(['error','fault'].includes(d.type))record({event:d.type,message:d.message});});const send=this.postMessage.bind(this);this.postMessage=(data,...rest)=>{if(data.type!=='recycle'&&data.type!=='snapshot')record({event:'send',type:data.type});return send(data,...rest);};}};
   addEventListener('visibilitychange',()=>record({event:'visibility',hidden:document.hidden}));addEventListener('click',e=>{if(e.target.id==='pause'||e.target.id==='settle')record({event:'click',id:e.target.id,running:document.body.dataset.running,materialRunning:document.body.dataset.materialRunning,text:e.target.textContent});},true);
  });
  const page=await context.newPage();page.setDefaultTimeout(20000);await page.goto(base+'/choir.html');await page.waitForFunction(()=>document.body.dataset.ready==='true'&&document.querySelector('#choir-clock').dataset.time!==undefined);await page.locator('#enter-sound').click();await page.waitForFunction(()=>document.body.dataset.running==='true');await page.locator('.choir-voice[data-body="1"]').click();await page.keyboard.down('Space');await page.waitForFunction(()=>Number(document.querySelector('#choir-clock').dataset.time)>4);await page.keyboard.up('Space');await page.locator('#connections').click();await page.waitForFunction(()=>document.querySelector('#connections').textContent==='Rejoin the circle');await page.locator('#pause').click();await page.waitForFunction(()=>document.body.dataset.running==='false');await page.locator('#settle').click();
  const good=await page.waitForFunction(()=>document.querySelector('#scene-caption').textContent==='Motion cleared; inscriptions remain'&&document.body.dataset.materialRunning==='false',{},{timeout:3000}).then(()=>true).catch(()=>false);
  const state=await page.evaluate(()=>({running:document.body.dataset.running,materialRunning:document.body.dataset.materialRunning,caption:document.querySelector('#scene-caption').textContent,status:document.querySelector('#status').textContent,trace:window.workerTrace}));cases.push({attempt,good,...state});await context.close();
 }
 fs.writeFileSync(output+'/report.json',JSON.stringify({base,cases},null,2)+'\n');console.log(JSON.stringify({base,cases},null,2));assert(cases.every(c=>c.good));
}finally{await browser.close();}
