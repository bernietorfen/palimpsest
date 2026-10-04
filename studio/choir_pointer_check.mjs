// Pointer picking, small-screen layout and graphics recovery.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {chromium,webkit} from '../.tools/browser/node_modules/playwright/index.mjs';
const engine=process.argv[2]??'chromium',output=process.argv[3]??'output/playwright/choir-pointer-001',base=process.argv[4]??'http://127.0.0.1:8765';
if(fs.existsSync(output))throw new Error('Use a new evidence directory');fs.mkdirSync(output,{recursive:true});
const browser=await (engine==='webkit'?webkit:chromium).launch({headless:true,args:engine==='chromium'?['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']:[]});
const context=await browser.newContext({viewport:{width:1440,height:1080},deviceScaleFactor:1,reducedMotion:'reduce',acceptDownloads:true});
const page=await context.newPage();page.setDefaultTimeout(45000);const errors=[];page.on('pageerror',e=>errors.push(e.message));const result={engine,errors};
try{
 await page.goto(base+'/choir.html');await page.waitForFunction(()=>document.body.dataset.ready==='true'&&document.querySelector('#choir-clock').dataset.time!==undefined);
 await page.locator('#enter-silent').click();await page.waitForFunction(()=>document.body.dataset.running==='true');
 const label=await page.locator('.body-label').nth(5).boundingBox();let found=false,hit=null;
 for(const [dx,dy]of [[0,55],[35,70],[-35,70],[50,110],[-50,110]]){
   await page.mouse.move(label.x+label.width/2+dx,label.y+label.height/2+dy);await page.mouse.down();await page.waitForTimeout(120);
   if(await page.locator('.choir-voice[data-body="5"]').getAttribute('aria-pressed')==='true'){found=true;hit={dx,dy};break;}await page.mouse.up();
 }
 assert(found,'Pointer did not pick the visible vessel F');const start=Number(await page.locator('#choir-clock').getAttribute('data-time'));
 await page.waitForFunction(t=>Number(document.querySelector('#choir-clock').dataset.time)>t+5,start);await page.mouse.up();
 result.pointer={hit,memory:Number(await page.locator('.choir-voice[data-body="5"]').getAttribute('data-memory'))};assert(result.pointer.memory>.01);
 await page.locator('#pause').click();await page.waitForFunction(()=>document.body.dataset.materialRunning==='false');
 const before=await page.locator('#choir-clock').getAttribute('data-time');
 await page.locator('#mode-turn').click();const box=await page.locator('#choir-canvas').boundingBox();await page.mouse.move(box.x+box.width*.5,box.y+box.height*.5);await page.mouse.down();await page.mouse.move(box.x+box.width*.58,box.y+box.height*.44,{steps:8});await page.mouse.up();
 result.orbitKeptTime=(await page.locator('#choir-clock').getAttribute('data-time'))===before;assert(result.orbitKeptTime);
 const lost=await page.evaluate(()=>{const gl=document.querySelector('#choir-canvas').getContext('webgl2'),ext=gl.getExtension('WEBGL_lose_context');if(!ext)return false;ext.loseContext();setTimeout(()=>ext.restoreContext(),300);return true;});
 if(lost){await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('The drawing is back'));assert.equal(await page.locator('#choir-clock').getAttribute('data-time'),before);result.graphicsRecovery=true;}
 await page.setViewportSize({width:393,height:852});await page.locator('#view-home').click();await page.locator('#choir').scrollIntoViewIfNeeded();await page.waitForTimeout(150);await page.screenshot({caret:'initial',path:output+'/mobile.jpg',type:'jpeg',quality:79});
 result.mobileOverflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);assert.equal(result.mobileOverflow,0);
 await page.evaluate(fs.readFileSync('.tools/browser/node_modules/axe-core/axe.min.js','utf8'));result.accessibility=await page.evaluate(async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return {violations:r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),incomplete:r.incomplete.map(v=>v.id)};});
 assert.deepEqual(result.accessibility.violations,[]);assert.deepEqual(errors,[]);fs.writeFileSync(output+'/report.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
}catch(error){result.failure=error.message;console.log(JSON.stringify(result,null,2));await page.screenshot({caret:'initial',path:output+'/failure.jpg',type:'jpeg',quality:72}).catch(()=>{});throw error;}finally{await browser.close();}
