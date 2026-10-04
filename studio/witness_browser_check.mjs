// RunPod only: actual audio, synchronized switching, seeking and small screens.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {chromium,webkit} from '../.tools/browser/node_modules/playwright/index.mjs';
import {screenshotEvidence} from './browser_screenshot.mjs';
const engine=process.argv[2]??'chromium',output=process.argv[3]??'output/playwright/witness-001',base=process.argv[4]??'http://127.0.0.1:8766';
if(fs.existsSync(output))throw new Error('Use a new evidence directory');fs.mkdirSync(output,{recursive:true});
const browser=await(engine==='webkit'?webkit:chromium).launch({headless:true,args:engine==='chromium'?['--no-sandbox']:[]});
const context=await browser.newContext({viewport:{width:1440,height:1080},deviceScaleFactor:1,reducedMotion:'reduce'});
await context.addInitScript(()=>{
 const Native=window.AudioContext||window.webkitAudioContext;
 window.AudioContext=class extends Native{constructor(...args){super(...args);window.testAudioContext=this;window.testAnalyser=this.createAnalyser();window.testAnalyser.fftSize=2048;const create=this.createGain.bind(this);this.createGain=()=>{const node=create(),connect=node.connect.bind(node);node.connect=(destination,...rest)=>{if(destination===this.destination)connect(window.testAnalyser);return connect(destination,...rest);};return node;};}};
});
const page=await context.newPage();page.setDefaultTimeout(30000);const errors=[],consoleErrors=[];page.on('pageerror',e=>errors.push(e.message));const evidence=screenshotEvidence(page,engine,consoleErrors),capture=evidence.capture;const result={engine,base,errors,consoleErrors,screenshotInstrumentationWarnings:evidence.warnings};
try{
 await page.goto(base+'/witness.html');await page.waitForFunction(()=>document.body.dataset.ready==='true');
 assert.equal(await page.locator('#difference').textContent(),'0.000 Hz');
 await capture(page,{path:output+'/entry.jpg',type:'jpeg',quality:80});
 await page.locator('#play-question').click();await page.waitForFunction(()=>document.body.dataset.playing==='true');await page.waitForFunction(()=>Number(document.body.dataset.position)>2);
 const sound=()=>page.evaluate(()=>{const values=new Float32Array(window.testAnalyser.fftSize);window.testAnalyser.getFloatTimeDomainData(values);return Math.max(...values.map(Math.abs));});
 result.Epeak=await sound();assert(result.Epeak>.00001);
 await page.locator('button[data-history="after"]').click();assert.equal(await page.locator('button[data-history="after"]').getAttribute('aria-pressed'),'true');assert.equal(await page.locator('#portrait-after').getAttribute('data-active'),'true');
 const eTime=Number(await page.locator('body').getAttribute('data-position'));await page.locator('[data-body="A"]').click();await page.waitForFunction(()=>document.body.dataset.listener==='A'&&document.body.dataset.playing==='true');
 const aTime=Number(await page.locator('body').getAttribute('data-position'));assert(aTime>=eTime-.1&&aTime<eTime+2);result.switchPreservesTime={before:eTime,after:aTime};
 assert.equal(await page.locator('#difference').textContent(),'3.411 Hz');assert.equal(await page.locator('#tuning-curves path').count(),12);
 await page.locator('#question-time').evaluate(input=>{input.value='31';input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));});
 await page.waitForFunction(()=>document.body.dataset.playing==='true'&&Number(document.body.dataset.position)>=31);await page.waitForFunction(()=>Number(document.body.dataset.position)>32);result.Apeak=await sound();assert(result.Apeak>.00001);
 await page.locator('#play-question').click();await page.waitForFunction(()=>document.body.dataset.playing==='false');const paused=Number(await page.locator('body').getAttribute('data-position'));await page.waitForTimeout(200);assert.equal(Number(await page.locator('body').getAttribute('data-position')),paused);result.pauseExact=true;
 await page.locator('[data-body="G"]').click();assert.equal(await page.locator('#difference').textContent(),'4.694 Hz');assert.equal(await page.locator('body').getAttribute('data-playing'),'false');assert.equal(Number(await page.locator('body').getAttribute('data-position')),paused);
 await page.locator('button[data-history="before"]').click();await page.locator('#question-time').evaluate(input=>{input.value='39.8';input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));});await page.locator('#play-question').click();await page.waitForFunction(()=>document.body.dataset.playing==='false'&&Number(document.body.dataset.position)===40);result.endsAt40=true;
 await page.locator('#play-question').click();await page.waitForFunction(()=>document.body.dataset.playing==='true'&&Number(document.body.dataset.position)<1);result.replayStartsAtZero=true;await page.locator('#play-question').click();
 result.decoded=await page.evaluate(async()=>{const names=['before','after-A','after-C','after-G'];const out=[];for(const name of names){const response=await fetch('/assets/generated/choir-witness/'+name+'.m4a'),buffer=await window.testAudioContext.decodeAudioData(await response.arrayBuffer());const values=buffer.getChannelData(0);let peak=0,power=0;for(const value of values){peak=Math.max(peak,Math.abs(value));power+=value*value;}out.push({name,duration:buffer.duration,channels:buffer.numberOfChannels,peak,rms:Math.sqrt(power/values.length)});}return out;});
 assert(result.decoded.every(r=>Math.abs(r.duration-40)<.08&&r.channels===1&&r.peak<.7&&r.rms>.001));
 await page.setViewportSize({width:393,height:852});await page.locator('#listening').scrollIntoViewIfNeeded();await capture(page,{path:output+'/mobile.jpg',type:'jpeg',quality:80});result.mobileOverflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);assert.equal(result.mobileOverflow,0);
 await page.evaluate(fs.readFileSync('.tools/browser/node_modules/axe-core/axe.min.js','utf8'));result.accessibility=await page.evaluate(async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return{violations:r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),incomplete:r.incomplete.map(v=>v.id)};});assert.deepEqual(result.accessibility.violations,[]);assert.deepEqual(errors,[]);assert.deepEqual(consoleErrors,[]);
 fs.writeFileSync(output+'/report.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
}catch(error){result.failure=error.message;await capture(page,{path:output+'/failure.jpg',type:'jpeg',quality:75}).catch(()=>{});fs.writeFileSync(output+'/failure.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));throw error;}finally{await browser.close();}
