// The rendered exhibition: all new sculptures, keyboard orbit, recovery and film.
import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {chromium,webkit} from '../.tools/browser/node_modules/playwright/index.mjs';
const engine=process.argv[2]??'chromium',output=process.argv[3]??'output/playwright/second-act-001',base=process.argv[4]??'http://127.0.0.1:8766',scope=process.argv[5]??'full';
if(fs.existsSync(output))throw new Error('Use a new evidence directory');fs.mkdirSync(output,{recursive:true});
const browser=await(engine==='webkit'?webkit:chromium).launch({headless:true,args:engine==='chromium'?['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']:[]});
const context=await browser.newContext({viewport:{width:1440,height:1080},deviceScaleFactor:1,reducedMotion:'reduce'}),page=await context.newPage();page.setDefaultTimeout(45000);const errors=[],consoleErrors=[],failed=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')consoleErrors.push(m.text());});page.on('requestfailed',r=>{if(r.failure()?.errorText!=='net::ERR_ABORTED')failed.push({path:new URL(r.url()).pathname,error:r.failure()?.errorText});});const result={engine,base,scope,errors,consoleErrors,failed,sculptures:[]};
const hash=buffer=>crypto.createHash('sha256').update(buffer).digest('hex');
try{
 await page.goto(base+'/');await page.evaluate(()=>document.fonts.ready);await page.waitForFunction(()=>document.querySelector('#ensemble-film').poster&&document.querySelector('#choir-downloads a').textContent.includes('Film master'));assert.equal(await page.locator('#ensemble-film').getAttribute('src'),null);
 await page.screenshot({path:output+'/entry.jpg',type:'jpeg',quality:84});
 for(const state of ['encounter','after','source']){
  await page.locator(`[data-choir-sculpture="${state}"]`).click();await page.waitForFunction(()=>document.querySelector('#choir-sculpture-canvas').dataset.state==='ready');
  const canvas=page.locator('#choir-sculpture-canvas'),before=hash(await canvas.screenshot());await canvas.press('ArrowLeft');await canvas.press('ArrowUp');await page.waitForTimeout(80);const after=hash(await canvas.screenshot());assert.notEqual(before,after,'Keyboard orbit did not alter the rendered sculpture');
  result.sculptures.push({state,triangles:Number(await canvas.getAttribute('data-triangles')),keyboardChangesImage:true});
  await page.screenshot({path:output+`/sculpture-${state}.jpg`,type:'jpeg',quality:79});
  if(state==='after'){
   const lost=await canvas.evaluate(element=>{const ext=element.getContext('webgl2').getExtension('WEBGL_lose_context');if(!ext)return false;element.addEventListener('webglcontextlost',()=>element.dataset.observedLoss='true',{once:true});element.addEventListener('webglcontextrestored',()=>element.dataset.observedRestore='true',{once:true});ext.loseContext();setTimeout(()=>ext.restoreContext(),300);return true;});
   if(lost){await page.waitForFunction(()=>{const c=document.querySelector('#choir-sculpture-canvas');return c.dataset.observedLoss==='true'&&c.dataset.observedRestore==='true'&&c.dataset.state==='ready';});await canvas.press('ArrowRight');result.graphicsRestoration=true;}
  }
  await page.keyboard.press('Escape');assert.equal(await page.locator('#choir-sculpture-dialog').evaluate(d=>d.open),false);assert.equal(await page.locator('body').evaluate(b=>b.style.overflow),'');
 }
 assert.deepEqual(result.sculptures.map(s=>s.triangles),[197868,144888,30328]);
 if(scope==='full'){
  await page.locator('[data-choir-seek="248"]').click();await page.waitForFunction(()=>{const v=document.querySelector('#ensemble-film');return v.currentTime>249&&!v.paused&&!v.seeking&&v.videoWidth===1920;});
  result.film=await page.locator('#ensemble-film').evaluate(v=>({duration:v.duration,time:v.currentTime,width:v.videoWidth,height:v.videoHeight,tracks:v.textTracks.length}));assert.equal(result.film.duration,288);assert.equal(result.film.height,1080);assert.equal(result.film.tracks,1);await page.locator('#ensemble-film').evaluate(v=>v.pause());
 }
 await page.setViewportSize({width:393,height:852});await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:output+'/mobile.jpg',type:'jpeg',quality:83});result.overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);assert.equal(result.overflow,0);
 await page.locator('[data-choir-sculpture="encounter"]').click();await page.waitForFunction(()=>document.querySelector('#choir-sculpture-canvas').dataset.state==='ready');await page.screenshot({path:output+'/mobile-sculpture.jpg',type:'jpeg',quality:84});result.mobileSculpture=await page.locator('#choir-sculpture-dialog').evaluate(d=>({width:d.clientWidth,scrollWidth:d.scrollWidth,height:d.clientHeight,scrollHeight:d.scrollHeight}));assert.equal(result.mobileSculpture.width,result.mobileSculpture.scrollWidth);await page.keyboard.press('Escape');
 await page.locator('#received').scrollIntoViewIfNeeded();await page.locator('#received img').evaluate(i=>i.decode());await page.locator('#received').screenshot({path:output+'/received-section.jpg',type:'jpeg',quality:84});
 for(const image of await page.locator('img').all()){await image.scrollIntoViewIfNeeded();await image.evaluate(i=>i.decode());}result.images=await page.locator('img').evaluateAll(images=>images.map(image=>({src:new URL(image.src).pathname,loaded:image.complete&&image.naturalWidth>0})));
 await page.evaluate(fs.readFileSync('.tools/browser/node_modules/axe-core/axe.min.js','utf8'));result.accessibility=await page.evaluate(async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return{violations:r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),incomplete:r.incomplete.map(v=>v.id)};});assert.deepEqual(result.accessibility.violations,[]);assert.deepEqual(errors,[]);assert.deepEqual(consoleErrors,[]);assert.deepEqual(failed,[]);
 fs.writeFileSync(output+'/report.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
}catch(error){result.failure=error.message;result.viewerStatus=await page.locator('#choir-sculpture-status').textContent().catch(()=>null);await page.screenshot({path:output+'/failure.jpg',type:'jpeg',quality:76}).catch(()=>{});fs.writeFileSync(output+'/failure.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));throw error;}finally{await browser.close();}
