// RunPod only. Keyboard controls, real touch input, corrupt import and demo undo.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {chromium} from '../.tools/browser/node_modules/playwright/index.mjs';
const output=process.argv[2]??'output/playwright/choir-interaction-001';if(fs.existsSync(output))throw new Error('Use a new evidence directory');fs.mkdirSync(output,{recursive:true});
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const context=await browser.newContext({viewport:{width:393,height:852},deviceScaleFactor:1,isMobile:true,hasTouch:true,reducedMotion:'reduce',acceptDownloads:true});
await context.addInitScript(()=>{const original=Storage.prototype.setItem;Storage.prototype.setItem=function(key,value){if(key==='palimpsest-choir-recovery-v1')throw new DOMException('Storage unavailable','QuotaExceededError');return original.call(this,key,value);};});
const page=await context.newPage();page.setDefaultTimeout(45000);const errors=[];page.on('pageerror',e=>errors.push(e.message));const result={engine:'chromium',realTouch:true,errors};
const download=async name=>{const [d]=await Promise.all([page.waitForEvent('download'),page.locator('#save').click()]);const path=output+'/'+name+'.json';await d.saveAs(path);return JSON.parse(fs.readFileSync(path,'utf8'));};
try{
 await page.goto('http://127.0.0.1:8766/choir.html');await page.waitForFunction(()=>document.body.dataset.ready==='true'&&document.querySelector('#choir-clock').dataset.time!==undefined);await page.locator('#enter-silent').click();await page.waitForFunction(()=>document.body.dataset.materialRunning==='true');
 await page.locator('#pause').focus();await page.keyboard.press('Space');await page.waitForFunction(()=>document.body.dataset.materialRunning==='false');result.spaceActivatesPause=true;
 await page.keyboard.press('Space');await page.waitForFunction(()=>document.body.dataset.materialRunning==='true');
 await page.locator('#choir-canvas').scrollIntoViewIfNeeded();const cdp=await context.newCDPSession(page);const label=await page.locator('.body-label').nth(5).boundingBox();let hit=null;
 for(const [dx,dy]of [[0,28],[18,32],[-18,32],[0,44]]){
  const point={x:label.x+label.width/2+dx,y:label.y+label.height/2+dy,radiusX:3,radiusY:3,force:1,id:1};await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[point]});await page.waitForTimeout(100);
  if(await page.locator('.choir-voice[data-body="5"]').getAttribute('aria-pressed')==='true'){hit={dx,dy};break;}await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
 }
 assert(hit,'The touch did not reach vessel F');const start=Number(await page.locator('#choir-clock').getAttribute('data-time'));await page.waitForFunction(t=>Number(document.querySelector('#choir-clock').dataset.time)>t+5,start);await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});result.touch={hit,memory:Number(await page.locator('.choir-voice[data-body="5"]').getAttribute('data-memory'))};assert(result.touch.memory>.01);
 await page.locator('#pause').click();await page.waitForFunction(()=>document.body.dataset.materialRunning==='false');await page.waitForFunction(()=>document.querySelector('#recovery').dataset.saved==='false');assert((await page.locator('#recovery').textContent()).includes('Save a file'));result.storageFailureExplained=true;
 const saved=await download('prior'),corrupt=structuredClone(saved);corrupt.bodies[6].p[0]=9;fs.writeFileSync(output+'/invalid.json',JSON.stringify(corrupt));await page.locator('#open').setInputFiles(output+'/invalid.json');await page.waitForFunction(()=>document.querySelector('#status').textContent==='The retained fields exceed material bounds');
 assert.deepEqual(await download('after-invalid'),saved);result.corruptImportAtomic=true;
 await page.locator('#demonstration').click();await page.waitForFunction(()=>document.querySelector('#demonstration').textContent==='Leave the demonstration');
 await page.waitForFunction(()=>document.querySelector('#scene-caption').textContent==='Your turn',null,{timeout:130000});await page.locator('#pause').click();await page.waitForFunction(()=>document.body.dataset.materialRunning==='false');const demonstration=await download('demonstration');assert(demonstration.gates.every(x=>x===0));assert(demonstration.bodies.some(b=>b.p.some(x=>Math.abs(x)>.01)));result.demonstrationEndsSeparated=true;
 await page.locator('#undo').click();await page.waitForFunction(()=>document.querySelector('#scene-caption').textContent==='The previous encounter');const restored=await download('undo');
 assert.deepEqual(restored,saved);result.undoRestoresPriorEncounterExactly=true;
 result.overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);assert.equal(result.overflow,0);assert.deepEqual(errors,[]);fs.writeFileSync(output+'/report.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
}catch(error){result.failure=error.message;result.status=await page.locator('#status').textContent().catch(()=>null);await page.screenshot({path:output+'/failure.jpg',type:'jpeg',quality:76}).catch(()=>{});fs.writeFileSync(output+'/failure.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));throw error;}finally{await browser.close();}
