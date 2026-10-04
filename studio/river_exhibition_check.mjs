// Run only on the authorized remote machine. A media fixture can test controls,
// never the quality or completeness of the final film. No fixture enters site/.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import {chromium,webkit} from '../.tools/browser/node_modules/playwright/index.mjs';
import {screenshotEvidence} from './browser_screenshot.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const args=process.argv.slice(2);
function argument(name,fallback){const i=args.indexOf(name);return i<0?fallback:args[i+1];}
let base=argument('--base','http://127.0.0.1:8772');
const routePath=argument('--route','/');
const out=path.resolve(argument('--out',path.join(root,'artwork/river-exhibition-001')));
const mediaFixture=argument('--media-fixture',null);
const draftDirectory=argument('--draft-dir',null);
const structureOnly=args.includes('--structure-only');
const engines=argument('--engines','chromium,webkit').split(',');
const captureBaseline=args.includes('--baseline');
assert.ok(routePath.startsWith('/')&&!routePath.startsWith('//'),'Use a same-origin route path');
assert.ok(!(structureOnly&&(mediaFixture||draftDirectory)),'Structural checks do not need a media mapping');
assert.ok(!(mediaFixture&&draftDirectory),'Choose a control fixture or an actual draft');
const report={route:routePath,base,media:structureOnly?'Actual film playback pending; this run checks structure and navigation':draftDirectory?'Actual audiovisual draft, isolated browser mapping; not the final master':mediaFixture?'Explicit test-only media fixture; actual film not evaluated':'Actual route media',checks:[],engines:{},screenshots:[],pending:structureOnly?['Actual new-film playback, seek, captions, fullscreen, end state and media recovery','Published release redirect and public source links','Final companion PDF and poster delivery']:draftDirectory?['Final master and typography/captions revision','Published release redirect and public source links','Final companion PDF and poster delivery']:[]};
const source=JSON.parse(await fs.readFile(path.join(root,'site/assets/data/relational-clock.json'),'utf8'));
const reference=source.models.thirtyTwo.references.find(value=>value.time===2*Math.PI);
const configuration=JSON.parse(await fs.readFile(path.join(root,'site/vercel.json'),'utf8'));
const csp=configuration.headers.flatMap(rule=>rule.headers).find(header=>header.key==='Content-Security-Policy').value;
await fs.mkdir(out,{recursive:true});
const bytes=mediaFixture?await fs.readFile(mediaFixture):null;
if(draftDirectory){
  const delivery=JSON.parse(await fs.readFile(path.join(draftDirectory,'delivery.json'),'utf8'));
  assert.equal(delivery.edition,'draft');
  for(const name of ['river-viewing.mp4','river-poster.jpg','river-notes.vtt']){
    const file=path.join(draftDirectory,name),hash=createHash('sha256');
    assert.equal((await fs.stat(file)).size,delivery.files[name].bytes);
    for await(const chunk of createReadStream(file))hash.update(chunk);
    assert.equal(hash.digest('hex'),delivery.files[name].sha256);
  }
  report.draft={directory:path.relative(root,path.resolve(draftDirectory)),edition:delivery.edition,viewing:delivery.editions['river-viewing.mp4'],sha256:delivery.files['river-viewing.mp4'].sha256,captionsSha256:delivery.files['river-notes.vtt'].sha256,scope:'Actual draft bytes verified against their delivery receipt and served through an isolated loopback mapping with normal byte ranges. The mapped files never enter the production site inventory.'};
}
const fixtureCaptions='WEBVTT\n\n00:00:00.000 --> 00:00:04.000\n[Media-control test fixture; not the film]\n';
function check(name,detail={}){report.checks.push({name,...detail});}
function near(actual,expected,tolerance=1e-12){assert.ok(Math.abs(actual-expected)<=tolerance,`${actual} differs from ${expected}`);}

async function routes(context){
  // The loopback server is range-aware; install the deployed CSP in the test
  // document response so this preview receives the real policy too.
  await context.route(url=>url.origin===new URL(base).origin&&url.pathname===routePath,async route=>{
    const response=await route.fetch();
    await route.fulfill({response,headers:{...response.headers(),'Content-Security-Policy':csp}});
  });
  if(bytes){
    await context.route('**/assets/generated/river-viewing.mp4',route=>{
      const range=route.request().headers().range;
      const match=/bytes=(\d+)-(\d*)/.exec(range||'');
      if(match){const start=Number(match[1]),end=Math.min(bytes.length-1,match[2]?Number(match[2]):bytes.length-1);return route.fulfill({status:206,contentType:'video/mp4',body:bytes.subarray(start,end+1),headers:{'Accept-Ranges':'bytes','Content-Range':`bytes ${start}-${end}/${bytes.length}`}});}
      return route.fulfill({status:200,contentType:'video/mp4',body:bytes,headers:{'Accept-Ranges':'bytes'}});
    });
    await context.route('**/assets/generated/river-notes.vtt',route=>route.fulfill({status:200,contentType:'text/vtt',body:fixtureCaptions}));
  }
}

async function ready(page){
  await page.goto(`${base}${routePath}`,{waitUntil:'networkidle'});
  await page.waitForFunction(()=>document.querySelector('#clock-work').dataset.ready==='true');
  await page.evaluate(()=>document.fonts.ready);
}
async function state(page){return page.locator('#clock-work').evaluate(node=>({...node.dataset,state:document.querySelector('#clock-state-record').textContent,paths:[...document.querySelectorAll('#clock-current path')].map(path=>({edge:path.dataset.edge,d:path.getAttribute('d'),reading:path.dataset.reading}))}));}
async function overflow(page){return page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth}));}
async function capture(evidence,page,name,options={}){const target=path.join(out,name);await evidence.capture(page,{path:target,type:'jpeg',quality:84,...options});report.screenshots.push(target);}

async function integration(page,evidence,engine){
  const paths=['/','/river.html','/movements.html','/first-act.html','/instrument.html','/atlas.html','/pressure.html','/choir.html','/witness.html','/observer.html','/credits.html'];
  const documents={};
  for(const pathname of paths){
    const response=await page.request.get(`${base}${pathname}`);
    assert.equal(response.status(),200,`${pathname} remains available`);
    documents[pathname]=await response.text();
  }
  assert.equal(documents['/'],documents['/river.html'],'The promoted homepage and retained film route agree');
  const archive=documents['/movements.html'];
  assert.ok(archive.includes('id="ensemble-film"')&&archive.includes('src="/second-act.js"'));
  for(const target of ['/first-act.html','/choir.html','/witness.html','/observer.html'])assert.ok(archive.includes(`href="${target}"`),`Archive reaches ${target}`);
  const sourceLinks=await page.locator('.science-body a').evaluateAll(nodes=>nodes.map(node=>node.href));
  assert.deepEqual(sourceLinks,[
    'https://github.com/bernietorfen/palimpsest/blob/main/research/RELATIONAL-CLOCK-RESULTS.md',
    'https://github.com/bernietorfen/palimpsest/blob/main/research/TIME-AMBIGUITY-RESULTS.md',
    'https://github.com/bernietorfen/palimpsest/blob/main/research/OPERATIONAL-TIME-RESULTS.md'
  ]);
  const continuation=await page.locator('.work-links a').evaluateAll(nodes=>nodes.map(node=>node.getAttribute('href')));
  assert.deepEqual(continuation,['/assets/generated/river-viewing.mp4','https://github.com/bernietorfen/palimpsest/releases/download/a-river-twice-1/river-screening.mp4','/assets/generated/river-companion.pdf','https://github.com/bernietorfen/palimpsest','/movements.html','/credits.html']);
  assert.ok(documents['/first-act.html'].includes('href="/movements.html">The second act'));
  for(const target of ['/instrument.html','/atlas.html'])assert.ok(documents[target].includes('href="/first-act.html#film">The film'));
  for(const target of ['/choir.html','/witness.html','/observer.html'])assert.ok(documents[target].includes('href="/movements.html">The second act'));
  assert.ok(documents['/credits.html'].includes('href="/assets/generated/river-companion.pdf"'));
  const filmRedirect=configuration.redirects.find(value=>value.source==='/assets/generated/river-viewing.mp4');
  assert.deepEqual(filmRedirect,{source:'/assets/generated/river-viewing.mp4',destination:'https://github.com/bernietorfen/palimpsest/releases/download/a-river-twice-1/river-viewing.mp4',permanent:true});
  assert.match(csp,/media-src 'self' https:\/\/github\.com https:\/\/release-assets\.githubusercontent\.com;/);
  assert.ok(!configuration.redirects.some(value=>value.source==='/assets/generated/river-companion.pdf'),'The new companion remains a direct small asset');
  check(`${engine}: homepage promotion, preserved routes, exact science links, companion and release configuration`,{routes:paths,publicLinks:'Targets checked; public availability remains a release gate'});
  await page.locator('.work-links a[href="/movements.html"]').click();
  await page.waitForURL(`${base}/movements.html`);
  assert.equal(await page.locator('#ensemble-film').count(),1);
  assert.equal(await page.locator('#ensemble-film').getAttribute('src'),null);
  await page.setViewportSize({width:393,height:852});
  assert.deepEqual(await overflow(page),{viewport:393,width:393});
  const home=page.locator('.second-header nav a[href="/"]');
  assert.equal(await home.isVisible(),true);
  await capture(evidence,page,`${engine}-mobile-movements.jpg`);
  await home.click();
  await page.waitForURL(`${base}/`);
  await page.waitForFunction(()=>document.querySelector('#clock-work').dataset.ready==='true');
  assert.equal(await page.locator('#river-film').getAttribute('src'),null);
  check(`${engine}: viewer can enter earlier movements and return to the new film on mobile without autoplay`);
}

let browser,draftServer,draftServerErrors='',activePage,activeEngine;
try{
  if(draftDirectory){
    // Stream actual media over loopback HTTP. Large inline route.fulfill bodies
    // unnecessarily stress the automation protocol and do not test byte ranges.
    const serverCode=`from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import json,sys
from studio.serve_site import Handler
site=Path(sys.argv[1]);draft=Path(sys.argv[2])
mapping={"/assets/generated/"+name:draft/name for name in ("river-viewing.mp4","river-poster.jpg","river-notes.vtt")}
class DraftHandler(Handler):
 def translate_path(self,path):
  selected=mapping.get(urlsplit(path).path)
  return str(selected) if selected else super().translate_path(path)
with ThreadingHTTPServer(("127.0.0.1",0),partial(DraftHandler,directory=str(site))) as server:
 print(json.dumps({"port":server.server_address[1]}),flush=True)
 server.serve_forever()
`;
    draftServer=spawn('python3',['-u','-c',serverCode,path.join(root,'site'),path.resolve(draftDirectory)],{cwd:root,stdio:['ignore','pipe','pipe']});
    draftServer.stderr.on('data',chunk=>{draftServerErrors=(draftServerErrors+chunk.toString()).slice(-8192);});
    const port=await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(new Error(`Draft server did not start: ${draftServerErrors}`)),10000);
      draftServer.once('error',error=>{clearTimeout(timer);reject(error);});
      draftServer.once('exit',code=>{clearTimeout(timer);reject(new Error(`Draft server exited early (${code}): ${draftServerErrors}`));});
      draftServer.stdout.once('data',chunk=>{clearTimeout(timer);try{resolve(JSON.parse(chunk.toString()).port);}catch(error){reject(error);}});
    });
    base=`http://127.0.0.1:${port}`;report.base=base;
  }
  for(const engine of engines){
    assert.ok(['chromium','webkit'].includes(engine),'Supported engines: chromium, webkit');
    browser=await({chromium,webkit}[engine]).launch({headless:true});
    const context=await browser.newContext({viewport:{width:1440,height:1080},reducedMotion:'reduce'});
    await routes(context);
    const page=await context.newPage(),errors=[],pageErrors=[],failedResources=[];
    activePage=page;activeEngine=engine;
    const evidence=screenshotEvidence(page,engine,errors);
    page.on('pageerror',error=>pageErrors.push(error.message));
    page.on('response',response=>{if(response.status()>=400)failedResources.push({url:response.url(),status:response.status()});});
    const mediaRequests=[];
    page.on('request',request=>{if(request.url().includes('river-viewing.mp4'))mediaRequests.push(request.url());});
    await ready(page);
    assert.equal(mediaRequests.length,0,'No video request before explicit consent');
    assert.equal(await page.locator('#river-film').getAttribute('src'),null);
    assert.equal(await page.locator('#river-film').evaluate(video=>video.paused),true);
    assert.equal(await page.locator('#reveal-connections').isDisabled(),true);
    assert.equal(await page.locator('#clock-current path').count(),28);
    near(Number((await state(page)).distance),0);
    assert.equal(await page.evaluate(()=>getComputedStyle(document.documentElement).scrollBehavior),'auto');
    assert.deepEqual(await overflow(page),{viewport:1440,width:1440});
    await capture(evidence,page,`${engine}-entry.jpg`);
    check(`${engine}: explicit media consent, stable initial clock, reduced motion, desktop width`);
    await page.setViewportSize({width:1366,height:768});
    const playBounds=await page.locator('#watch-film').boundingBox();
    assert.ok(playBounds.y>=0&&playBounds.y+playBounds.height<=768,'Watch control remains in the first laptop viewport');
    await capture(evidence,page,`${engine}-laptop-entry.jpg`);
    await page.setViewportSize({width:1440,height:1080});
    check(`${engine}: primary Watch action visible at 1366 × 768`);

    await page.locator('#return-fragment').focus();
    await page.keyboard.press('Enter');
    const fragment=await state(page);
    assert.equal(Number(fragment.time),2*Math.PI);
    assert.equal(fragment.withinReturned,'28');
    assert.ok(Number(fragment.discrepancy)<1e-24);
    near(Number(fragment.distance),Math.sqrt(reference.distanceSquared));
    const references=await page.locator('#clock-reference path').evaluateAll(nodes=>nodes.map(node=>node.getAttribute('d')));
    assert.deepEqual(fragment.paths.map(node=>node.d),references,'All limited curves visibly overlay their initial reference');
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(()=>document.activeElement.id),'reveal-connections');
    await page.keyboard.press('Space');
    const connected=await state(page);
    assert.equal(connected.observer,'connected');
    assert.equal(connected.paths.length,31);
    assert.equal(connected.changedBridges,'3');
    assert.equal(connected.state,fragment.state,'Observer switch preserves byte-identical serialized state');
    assert.equal(connected.time,fragment.time);
    assert.equal(connected.stateRevision,fragment.stateRevision,'Observer switch never creates a new state');
    assert.equal(connected.distance,fragment.distance);
    near(Number(connected.discrepancy),reference.R.connected);
    assert.deepEqual(connected.paths.filter(node=>node.reading==='within'),fragment.paths);
    const changedBridgePaths=await page.locator('#clock-current [data-reading="bridge"]').evaluateAll(nodes=>nodes.every(node=>node.getAttribute('d')!==document.querySelector(`#clock-reference [data-edge="${node.dataset.edge}"]`).getAttribute('d')));
    assert.equal(changedBridgePaths,true);
    await page.locator('#clock-work').scrollIntoViewIfNeeded();
    await capture(evidence,page,`${engine}-connections.jpg`);
    await page.keyboard.press('Space');
    assert.equal((await state(page)).state,fragment.state);
    assert.equal(await page.locator('#clock-current path').count(),28);
    check(`${engine}: keyboard return and observer switch`,{localR:Number(fragment.discrepancy),globalD:Number(fragment.distance),connectedR:Number(connected.discrepancy),stateByteIdentical:true,withinGeometryIdentical:true});

    await page.locator('#clock-time').focus();
    await page.keyboard.press('End');
    near(Number((await state(page)).time),4*Math.PI);
    assert.equal((await state(page)).withinReturned,'28');
    await page.keyboard.press('Home');
    assert.equal(Number((await state(page)).time),0);
    await page.keyboard.press('ArrowRight');
    near(Number((await state(page)).time),.5*2*Math.PI/104);
    await page.locator('#clock-reset').click();
    assert.equal(Number((await state(page)).time),0);
    assert.equal(await page.locator('#reveal-connections').isDisabled(),true);
    check(`${engine}: range keyboard access, second local return, deterministic reset`);
    const zeroPath=(await state(page)).paths[0].d;
    async function setFilmMoment(seconds){await page.locator('#clock-time').evaluate((input,value)=>{input.value=String(value);input.dispatchEvent(new Event('input',{bubbles:true}));},seconds);return(await state(page)).paths[0].d;}
    const realOpposite=await setFilmMoment(52),positiveImaginary=await setFilmMoment(26),negativeImaginary=await setFilmMoment(78);
    assert.notEqual(realOpposite,zeroPath,'Changing real coherence with zero imaginary part changes the curve');
    assert.notEqual(positiveImaginary,negativeImaginary,'Opposite imaginary coherences with the same real part produce distinct curves');
    await page.locator('#clock-reset').click();
    check(`${engine}: both coherence quadratures affect visible curves despite constant coherence magnitude`);

    if(!structureOnly){
    await page.locator('#river-film').evaluate(video=>{
      window.__riverMediaTrace=[];
      for(const event of ['loadstart','loadedmetadata','play','playing','pause','ended','seeking','seeked','waiting','stalled','error','timeupdate'])video.addEventListener(event,()=>{
        const trace=window.__riverMediaTrace;
        trace.push({event,wallSeconds:performance.now()/1000,time:video.currentTime,readyState:video.readyState,paused:video.paused,ended:video.ended,hidden:document.hidden});
        if(trace.length>600)trace.shift();
      });
    });
    await page.locator('#watch-film').focus();
    await page.keyboard.press('Enter');
    await page.waitForFunction(()=>!document.querySelector('#river-film').paused&&document.querySelector('#river-film').readyState>=2);
    const playing=await page.locator('#river-film').evaluate(video=>({duration:video.duration,width:video.videoWidth,height:video.videoHeight,muted:video.muted,controls:video.controls,playsinline:video.playsInline,tracks:video.textTracks.length}));
    near(playing.duration,240,.06);
    if(draftDirectory){assert.equal(playing.width,report.draft.viewing.video.width);assert.equal(playing.height,report.draft.viewing.video.height);}
    assert.equal(playing.muted,false);assert.equal(playing.controls,true);assert.equal(playing.playsinline,true);assert.equal(playing.tracks,1);
    assert.ok(mediaRequests.length>0);
    assert.equal(await page.locator('#film-fullscreen').isDisabled(),false);
    await page.locator('#river-film').evaluate(video=>{video.textTracks[0].mode='showing';});
    await page.waitForFunction(()=>document.querySelector('#river-film').textTracks[0].cues?.length>0);
    const cueCount=await page.locator('#river-film').evaluate(video=>video.textTracks[0].cues.length);
    await page.locator('#film-fullscreen').click();
    await page.waitForFunction(()=>document.fullscreenElement===document.querySelector('#river-film')||document.querySelector('#river-film').webkitDisplayingFullscreen||/Full screen is unavailable|Use the video’s full-screen control/.test(document.querySelector('#film-status').textContent));
    const fullscreen=await page.evaluate(()=>document.fullscreenElement?'native document fullscreen':document.querySelector('#river-film').webkitDisplayingFullscreen?'native media fullscreen':'visible platform fallback');
    await page.evaluate(async()=>{if(document.fullscreenElement)await document.exitFullscreen();else if(document.querySelector('#river-film').webkitDisplayingFullscreen)document.querySelector('#river-film').webkitExitFullscreen();});
    check(`${engine}: native captions and fullscreen path`,{cueCount,fullscreen,source:report.media});
    if(draftDirectory){
      const seeks=[];
      for(const moment of [104,120.9,123.25,208]){
        await page.locator('#river-film').evaluate((video,time)=>new Promise((resolve,reject)=>{
          const timeout=setTimeout(()=>reject(new Error(`Seek to ${time} did not complete`)),15000);
          video.addEventListener('seeked',()=>{clearTimeout(timeout);requestAnimationFrame(()=>requestAnimationFrame(resolve));},{once:true});
          video.pause();video.currentTime=time;
        }),moment);
        const frame=await page.locator('#river-film').evaluate(video=>{
          const canvas=document.createElement('canvas');canvas.width=32;canvas.height=18;
          const context=canvas.getContext('2d',{willReadFrequently:true});context.drawImage(video,0,0,32,18);
          const rgba=context.getImageData(0,0,32,18).data;let maximum=0,total=0;
          for(let i=0;i<rgba.length;i+=4)for(let channel=0;channel<3;channel++){maximum=Math.max(maximum,rgba[i+channel]);total+=rgba[i+channel];}
          return {time:video.currentTime,readyState:video.readyState,maximumRgb:maximum,meanRgb:total/(32*18*3),activeCaptions:[...video.textTracks[0].activeCues||[]].map(cue=>cue.text)};
        });
        near(frame.time,moment,.06);assert.ok(frame.readyState>=2);
        if(moment===120.9)assert.ok(frame.maximumRgb<=2,'The actual decoded draft is black inside the composed silence');
        else assert.ok(frame.meanRgb>1,'The actual decoded image is visible at return and after silence');
        if(moment!==123.25)await capture(evidence,page.locator('#river-film'),`${engine}-draft-${String(moment).replace('.','-')}.jpg`);
        seeks.push(frame);
      }
      check(`${engine}: actual draft seeks at both returns, central blackout and reappearance`,{seeks,scope:'Browser frame decoding and active captions; no listening claim'});
    }
    await page.locator('#river-film').evaluate(video=>video.pause());
    await page.waitForFunction(()=>document.querySelector('.film-stage').dataset.videoState==='paused');
    assert.equal(await page.locator('.film-stage').getAttribute('data-video-state'),'paused');
    check(`${engine}: keyboard sound consent and native media`,{...playing,source:report.media});

    // Deterministically exercise the visibility handler. Headless tabs do not
    // consistently emit the OS-driven visibility transition across engines.
    const resume=await page.locator('#river-film').evaluate(async video=>{
      const sample=()=>{const canvas=document.createElement('canvas');canvas.width=64;canvas.height=36;const context=canvas.getContext('2d',{willReadFrequently:true});context.drawImage(video,0,0,64,36);return context.getImageData(0,0,64,36).data;};
      const before=sample(),timeBefore=video.currentTime,framesBefore=video.getVideoPlaybackQuality?.().totalVideoFrames??null;
      window.__riverResumePromise='pending';video.play().then(()=>window.__riverResumePromise='resolved').catch(error=>window.__riverResumePromise=error.name);
      await new Promise(resolve=>setTimeout(resolve,800));
      const after=sample();let difference=0;
      for(let i=0;i<before.length;i+=4)for(let channel=0;channel<3;channel++)difference+=Math.abs(after[i+channel]-before[i+channel]);
      return {timeBefore,timeAfter:video.currentTime,meanPixelDifference:difference/(64*36*3),framesBefore,framesAfter:video.getVideoPlaybackQuality?.().totalVideoFrames??null,playPromise:window.__riverResumePromise,readyState:video.readyState,paused:video.paused,ended:video.ended,stage:document.querySelector('.film-stage').dataset.videoState,presentedFrameCallback:typeof video.requestVideoFrameCallback==='function'};
    });
    check(`${engine}: native resume progresses without relying on play-promise timing`,resume);
    assert.ok(resume.timeAfter>resume.timeBefore+.2&&!resume.paused&&!resume.ended);
    if(draftDirectory)assert.ok(resume.meanPixelDifference>1,'Actual moving draft frames continue after a paused seek');
    assert.equal(resume.stage,'playing','Moving video must not retain a stale buffering overlay');
    await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));delete document.hidden;});
    assert.equal(await page.locator('#river-film').evaluate(video=>video.paused),true);
    assert.match(await page.locator('#film-status').textContent(),/Paused while this page was away/);
    check(`${engine}: visibility-pause handler`,{event:'Synthetic document visibility transition; native tab switching not asserted'});

    await page.locator('#river-film').evaluate(video=>{video.currentTime=239.9;video.play();});
    await page.waitForFunction(()=>document.querySelector('#river-film').ended,null,{timeout:15000});
    // The media property can change before its queued `ended` DOM event.
    await page.locator('#film-next').waitFor({state:'visible',timeout:5000});
    assert.equal(await page.locator('#film-next').isVisible(),true);
    check(`${engine}: film completion invites the observer experiment`);
    report.mediaLifecycle??={};report.mediaLifecycle[engine]=await page.evaluate(()=>window.__riverMediaTrace);
    }
    assert.deepEqual(pageErrors,[]);
    assert.deepEqual(errors,[]);
    report.engines[engine]={applicationConsoleErrors:[...errors],pageErrors:[...pageErrors],screenshotWarnings:evidence.warnings};

    const mobile=await context.newPage(),mobileErrors=[];
    const mobileEvidence=screenshotEvidence(mobile,engine,mobileErrors);
    await mobile.setViewportSize({width:393,height:852});
    await ready(mobile);
    assert.deepEqual(await overflow(mobile),{viewport:393,width:393});
    const heights=await mobile.locator('#watch-film,#return-fragment,#reveal-connections,#clock-time,#clock-reset,.river-header nav a:not(:last-child)').evaluateAll(nodes=>nodes.map(node=>({id:node.id||node.textContent,height:node.getBoundingClientRect().height})));
    assert.ok(heights.every(item=>item.height>=44),JSON.stringify(heights));
    await capture(mobileEvidence,mobile,`${engine}-mobile-entry.jpg`);
    await mobile.locator('#return-fragment').click();await mobile.locator('#reveal-connections').click();
    await mobile.locator('#observation').scrollIntoViewIfNeeded();
    await capture(mobileEvidence,mobile,`${engine}-mobile-observer.jpg`);
    assert.deepEqual(mobileErrors,[]);
    report.engines[engine].mobileScreenshotWarnings=mobileEvidence.warnings;
    check(`${engine}: 393 px responsive layout and touch targets`,{heights});
    await mobile.close();

    const dataPage=await context.newPage();
    let brokenData=true;
    await dataPage.route('**/assets/data/relational-clock.json',route=>brokenData?route.fulfill({status:200,contentType:'application/json',body:'{"format":"broken"}'}):route.continue());
    await dataPage.goto(`${base}${routePath}`,{waitUntil:'networkidle'});
    assert.equal(await dataPage.locator('#clock-retry').isVisible(),true);
    assert.equal(await dataPage.locator('#watch-film').isEnabled(),true);
    assert.equal(await dataPage.locator('#return-fragment').isDisabled(),true);
    brokenData=false;
    await dataPage.locator('#clock-retry').click();
    await dataPage.waitForFunction(()=>document.querySelector('#clock-work').dataset.ready==='true');
    assert.equal(await dataPage.locator('#return-fragment').isEnabled(),true);
    check(`${engine}: malformed clock recovery leaves film usable`);
    await dataPage.close();

    if(!structureOnly){
    const mediaPage=await context.newPage();
    let brokenMedia=true;
    await mediaPage.route('**/assets/generated/river-viewing.mp4',route=>brokenMedia?route.fulfill({status:404,body:'Not available'}):route.fallback());
    await ready(mediaPage);
    await mediaPage.locator('#watch-film').click();
    await mediaPage.waitForFunction(()=>document.querySelector('.film-stage').dataset.videoState==='error');
    assert.equal(await mediaPage.locator('#film-retry').isVisible(),true);
    assert.equal(await mediaPage.locator('#return-fragment').isEnabled(),true);
    brokenMedia=false;
    await mediaPage.locator('#film-retry').click();
    await mediaPage.waitForFunction(()=>!document.querySelector('#river-film').paused&&document.querySelector('#river-film').readyState>=2);
    await mediaPage.locator('#river-film').evaluate(video=>video.pause());
    check(`${engine}: media failure and retry leave experiment usable`);
    await mediaPage.close();
    }

    const motionPage=await context.newPage();
    await motionPage.emulateMedia({reducedMotion:'no-preference'});
    await ready(motionPage);
    const still=await state(motionPage);
    await motionPage.locator('#return-fragment').click();
    await motionPage.waitForFunction(()=>{const work=document.querySelector('#clock-work');return work.dataset.returning==='true'&&Number(work.dataset.time)>1;});
    const travelling=await state(motionPage);
    assert.notEqual(travelling.paths[0].d,still.paths[0].d);
    assert.equal(await motionPage.locator('#reveal-connections').isDisabled(),true);
    await motionPage.waitForFunction(()=>document.querySelector('#clock-work').dataset.returning==='false');
    const held=await state(motionPage);
    assert.equal(Number(held.time),2*Math.PI);
    assert.equal(held.withinReturned,'28');
    await motionPage.waitForTimeout(120);
    assert.equal((await state(motionPage)).stateRevision,held.stateRevision,'The user-triggered return stops computing at its exact endpoint');
    await motionPage.locator('#reveal-connections').click();
    assert.equal((await state(motionPage)).state,held.state);
    check(`${engine}: user-triggered cycle travels, returns exactly, then stops; observer remains immutable`);
    await motionPage.close();

    if(routePath==='/'){
      await integration(page,evidence,engine);
      report.engines[engine].navigationConsoleErrors=[...errors];
      report.engines[engine].navigationPageErrors=[...pageErrors];
      report.engines[engine].navigationResourceFailures=[...new Map(failedResources.map(item=>[item.url,item])).values()];
      report.engines[engine].navigationAssetsReady=errors.length===0&&pageErrors.length===0&&failedResources.length===0;
      if(structureOnly&&!report.engines[engine].navigationAssetsReady){
        report.pending.push(`${engine}: restore archive assets before release; exact failed URLs are recorded under navigationResourceFailures`);
      }else{
        assert.deepEqual(errors,[],'Navigation must not produce application console errors');
        assert.deepEqual(pageErrors,[],'Navigation must not produce script errors');
        assert.deepEqual(failedResources,[],'Restore missing archive assets before final-media acceptance');
      }
    }

    if(captureBaseline&&engine==='chromium'){
      const baselinePath=path.join(out,'baseline-live-home.jpg');
      try{await fs.access(baselinePath);check('Baseline already captured; not duplicated');}
      catch{
        const baseline=await context.newPage();
        await baseline.goto('https://site-inky-eight-42.vercel.app/',{waitUntil:'networkidle'});
        await baseline.evaluate(()=>document.fonts.ready);
        await baseline.screenshot({path:baselinePath,type:'jpeg',quality:84});
        report.screenshots.push(baselinePath);check('Live baseline home captured at 1440 × 1080');
        await baseline.close();
      }
    }
    await context.close();await browser.close();browser=null;
  }
  report.passed=true;
}catch(error){
  report.passed=false;report.failure=error.stack;process.exitCode=1;
  if(activePage&&!activePage.isClosed()){try{report.mediaLifecycle??={};report.mediaLifecycle[activeEngine]=await activePage.evaluate(()=>window.__riverMediaTrace||[]);}catch{}}
}
finally{
  if(browser)await browser.close();
  if(draftServer){
    if(draftServer.exitCode===null&&draftServer.signalCode===null){const stopped=new Promise(resolve=>draftServer.once('exit',resolve));draftServer.kill('SIGTERM');await stopped;}
    report.draft.temporaryLoopbackServerClosed=true;
    if(!report.passed)report.draft.serverLog=draftServerErrors;
  }
  await fs.writeFile(path.join(out,'checks.json'),JSON.stringify(report,null,2)+'\n');
}
console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,report:path.join(out,'checks.json'),failure:report.failure},null,2));
