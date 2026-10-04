// A delayed network answer must not strand playback when the listener seeks.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {chromium,webkit} from '../.tools/browser/node_modules/playwright/index.mjs';
const engine=process.argv[2]??'chromium',output=process.argv[3],base=process.argv[4]??'http://127.0.0.1:8766';
if(!output||fs.existsSync(output))throw new Error('Supply a new evidence directory');fs.mkdirSync(output,{recursive:true});
const browser=await(engine==='webkit'?webkit:chromium).launch({headless:true,args:engine==='chromium'?['--no-sandbox']:[]});
const context=await browser.newContext({viewport:{width:1000,height:800},reducedMotion:'reduce'}),page=await context.newPage();page.setDefaultTimeout(12000);const errors=[];page.on('pageerror',e=>errors.push(e.message));const result={engine,errors};
try{
 let release;const pending=new Promise(resolve=>release=resolve);let requested=false;
 await page.route('**/choir-witness/before.m4a',async route=>{requested=true;await pending;await route.continue();});
 await page.goto(base+'/witness.html');await page.waitForFunction(()=>document.body.dataset.ready==='true');await page.locator('#play-question').click();await page.waitForFunction(()=>document.querySelector('#listening').getAttribute('aria-busy')==='true');
 await page.locator('#question-time').evaluate(input=>{input.value='18';input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));});
 release();await page.waitForFunction(()=>document.body.dataset.playing==='true'&&Number(document.body.dataset.position)>18&&Number(document.body.dataset.position)<23&&!document.querySelector('#play-question').disabled);
 assert(requested);result.seekDuringLoading=true;result.position=Number(await page.locator('body').getAttribute('data-position'));result.busyCleared=await page.locator('#listening').getAttribute('aria-busy')===null;assert(result.busyCleared);await page.locator('#play-question').click();assert.equal(await page.locator('body').getAttribute('data-playing'),'false');assert.deepEqual(errors,[]);
 fs.writeFileSync(output+'/report.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}catch(error){result.failure=error.message;result.state=await page.locator('body').evaluate(b=>({...b.dataset}));result.playDisabled=await page.locator('#play-question').isDisabled();fs.writeFileSync(output+'/failure.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));throw error;}finally{await browser.close();}
