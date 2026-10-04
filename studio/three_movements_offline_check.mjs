// Run on the authorized production host after an exact fresh package extraction.
// Signal/playback evidence is not perceptual audition or a physical-device test.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import {chromium,webkit} from '../.tools/browser/node_modules/playwright/index.mjs';

const args=process.argv.slice(2);
function argument(name,fallback=null){const at=args.indexOf(name);return at<0?fallback:args[at+1];}
const proof=path.resolve(argument('--proof','artwork/three-movements-proof-001'));
const output=path.resolve(argument('--out','artwork/three-movements-offline-001'));
const engine=argument('--engine','chromium');
assert.ok(['chromium','webkit'].includes(engine));
assert.ok(output!==proof&&!output.startsWith(proof+path.sep),'Evidence stays outside the verified installation');
await fs.mkdir(output,{recursive:false});
const inventory=JSON.parse(await fs.readFile(path.join(proof,'installation-content.json'),'utf8'));
const report={engine,sourceCommit:inventory.source_commit,checks:[],errors:[],consoleErrors:[],externalDependencies:[],failedLocalRequests:[],scope:'Fresh extracted installation with a dead external proxy and loopback range server; real file playback, calculated readings, live signal/state and export checks. No perceptual audition or physical-device claim.'};
let server,browser,page,serverErrors='',origin;
function check(name,detail={}){report.checks.push({name,...detail});}
async function checkedFiles(){
  const canonical=await fs.realpath(proof);
  for(const item of inventory.files){
    assert.ok(!path.isAbsolute(item.path)&&!item.path.split('/').some(part=>part.startsWith('.')));
    const file=path.join(proof,item.path),metadata=await fs.lstat(file);
    assert.ok(metadata.isFile()&&!metadata.isSymbolicLink());assert.equal(metadata.size,item.bytes);
    assert.equal(await fs.realpath(file),path.join(canonical,item.path),'No linked ancestor may change a verified input');
    const hash=createHash('sha256');for await(const block of createReadStream(file))hash.update(block);
    assert.equal(hash.digest('hex'),item.sha256,`Changed extraction: ${item.path}`);
  }
  check('Every extracted file still matches the exact package inventory',{files:inventory.files.length});
}
async function open(route){await page.goto(origin+route,{waitUntil:'networkidle'});}
async function film(selector,button,seconds,duration){
  await page.locator(button).click();
  await page.waitForFunction(selector=>document.querySelector(selector).readyState>=1,selector);
  await page.locator(selector).evaluate((video,time)=>{video.currentTime=time;video.play().catch(()=>{});},seconds);
  await page.waitForFunction(({selector,seconds})=>{const video=document.querySelector(selector);return video.videoWidth===1920&&video.currentTime>seconds+.6&&!video.paused&&!video.seeking;},{selector,seconds});
  const state=await page.locator(selector).evaluate(video=>{const state={time:video.currentTime,duration:video.duration,width:video.videoWidth,height:video.videoHeight,source:new URL(video.currentSrc).pathname};video.pause();return state;});
  assert.ok(Math.abs(state.duration-duration)<.06);assert.equal(state.height,1080);return state;
}
async function seekFrame(seconds){
  await page.locator('#river-film').evaluate((video,time)=>new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(new Error('Seek did not complete')),15000);
    video.addEventListener('seeked',()=>{clearTimeout(timer);requestAnimationFrame(()=>requestAnimationFrame(resolve));},{once:true});
    video.pause();video.currentTime=time;
  }),seconds);
  return page.locator('#river-film').evaluate(video=>{
    const canvas=document.createElement('canvas');canvas.width=32;canvas.height=18;
    const context=canvas.getContext('2d');context.drawImage(video,0,0,32,18);
    const data=context.getImageData(0,0,32,18).data;let maximum=0,total=0;
    for(let i=0;i<data.length;i+=4)for(let c=0;c<3;c++){maximum=Math.max(maximum,data[i+c]);total+=data[i+c];}
    return {time:video.currentTime,maximumRgb:maximum,meanRgb:total/(32*18*3)};
  });
}
async function download(button,name){
  const [item]=await Promise.all([page.waitForEvent('download'),page.locator(button).click()]);
  const file=path.join(output,name);await item.saveAs(file);assert.equal(await item.failure(),null);
  return fs.readFile(file,'utf8');
}
async function localPdf(href){
  assert.ok(href.startsWith('/assets/generated/'));
  const record=inventory.files.find(item=>item.path==='site'+href);assert.ok(record,href);
  const response=await page.request.head(origin+href);assert.equal(response.status(),200);
  assert.match(response.headers()['content-type'],/application\/pdf/);
  assert.equal(Number(response.headers()['content-length']),record.bytes);
}
try{
  await checkedFiles();
  const code=`from functools import partial
from http.server import ThreadingHTTPServer
import json,runpy,sys
handler=runpy.run_path(sys.argv[1])["Handler"]
with ThreadingHTTPServer(("127.0.0.1",0),partial(handler,directory=sys.argv[2])) as server:
 print(json.dumps({"port":server.server_address[1]}),flush=True)
 server.serve_forever()
`;
  server=spawn('python3',['-u','-c',code,path.join(proof,'serve.py'),path.join(proof,'site')],{stdio:['ignore','pipe','pipe']});
  server.stderr.on('data',data=>{serverErrors=(serverErrors+data.toString()).slice(-4096);});
  const port=await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(new Error('Portable server did not start')),10000);
    server.once('error',error=>{clearTimeout(timer);reject(error);});
    server.once('exit',code=>{clearTimeout(timer);reject(new Error(`Portable server exited (${code})`));});
    server.stdout.once('data',data=>{clearTimeout(timer);try{resolve(JSON.parse(data.toString()).port);}catch(error){reject(error);}});
  });
  origin=`http://127.0.0.1:${port}`;
  const options={headless:true,proxy:{server:'http://127.0.0.1:9',bypass:'127.0.0.1,localhost'}};
  if(engine==='chromium')options.args=['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader'];
  browser=await({chromium,webkit}[engine]).launch(options);
  const context=await browser.newContext({viewport:{width:1440,height:1080},reducedMotion:'reduce',acceptDownloads:true});
  await context.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(url.origin===origin)await route.continue();
    else{report.externalDependencies.push(url.href);await route.abort('internetdisconnected');}
  });
  page=await context.newPage();page.setDefaultTimeout(45000);
  page.on('pageerror',error=>report.errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')report.consoleErrors.push(message.text());});
  page.on('response',response=>{if(response.url().startsWith(origin)&&response.status()>=400)report.failedLocalRequests.push({path:new URL(response.url()).pathname,status:response.status()});});
  const requests=[];page.on('request',request=>requests.push(new URL(request.url()).pathname));
  await open('/');await page.waitForFunction(()=>document.querySelector('#clock-work').dataset.ready==='true');
  assert.equal(await page.locator('#river-film').getAttribute('src'),null);
  assert.ok(!requests.includes('/assets/generated/river-viewing.mp4'));
  await page.screenshot({path:path.join(output,'entry.jpg'),type:'jpeg',quality:80});
  check('The new film waits for sound consent');
  check('New viewing film plays and seeks locally',await film('#river-film','#watch-film',102,240));
  const frames=[];
  for(const seconds of [104,120.9,123.25,208]){
    const frame=await seekFrame(seconds);frames.push(frame);
    assert.ok(Math.abs(frame.time-seconds)<.06);
    if(seconds===120.9)assert.ok(frame.maximumRgb<=2);else assert.ok(frame.meanRgb>1);
  }
  await page.locator('#river-film').evaluate(video=>video.textTracks[0].mode='showing');
  await page.waitForFunction(()=>document.querySelector('#river-film').textTracks[0].cues?.length>=15);
  const cues=await page.locator('#river-film').evaluate(video=>video.textTracks[0].cues.length);
  check('Both returns, central blackout, reappearance and native captions survive offline',{frames,cues});
  await page.locator('#return-fragment').click();
  const held=await page.locator('#clock-state-record').textContent();
  assert.equal(await page.locator('#clock-work').getAttribute('data-within-returned'),'28');
  await page.locator('#reveal-connections').click();
  assert.equal(await page.locator('#clock-state-record').textContent(),held);
  assert.equal(await page.locator('#clock-work').getAttribute('data-changed-bridges'),'3');
  assert.equal(Number(await page.locator('#clock-work').getAttribute('data-time')),2*Math.PI);
  check('Changing the offline observer preserves the exact calculated state and time');
  await localPdf('/assets/generated/river-companion.pdf');
  const external=await page.locator('a[href^="https://"],a[href^="http://"]').evaluateAll(nodes=>nodes.map(node=>node.textContent));
  assert.ok(external.every(text=>text.includes('Online')));check('External screening/source/science links are visibly marked Online');
  await page.locator('.work-links a[href="/movements.html"]').click();
  await page.waitForURL(origin+'/movements.html');
  await page.waitForFunction(()=>document.querySelectorAll('#choir-downloads a').length>0);
  check('Preserved second film plays and seeks locally',await film('#ensemble-film','#enter-ensemble',248,288));
  for(const selector of ['#notebook .arrow-link','#received .arrow-link','#received .received-print','#observer .observer-companion','#observer>a'])await localPdf(await page.locator(selector).getAttribute('href'));
  for(const name of ['encounter','after','source']){
    await page.locator(`[data-choir-sculpture="${name}"]`).click();
    await page.waitForFunction(()=>document.querySelector('#choir-sculpture-canvas').dataset.state==='ready');
    assert.equal(await page.locator('#download-choir-sculpture').getAttribute('href'),`/assets/generated/choir-${name}.glb`);
    await page.locator('#choir-sculpture-canvas').press('ArrowLeft');await page.keyboard.press('Escape');
  }
  check('Legacy books and three turnable choir sculptures use included files');
  await open('/choir.html');await page.waitForFunction(()=>document.body.dataset.ready==='true');
  await page.locator('#enter-sound').click();await page.waitForFunction(()=>document.body.dataset.running==='true');
  await page.locator('.choir-voice[data-body="1"]').click();await page.keyboard.down('Space');
  await page.waitForFunction(()=>Number(document.querySelector('#choir-clock').dataset.time)>10);await page.keyboard.up('Space');
  const choir=await page.evaluate(()=>({memory:[...document.querySelectorAll('.choir-voice')].map(node=>Number(node.dataset.memory)),audioPeak:Number(document.body.dataset.audioPeak)}));
  assert.ok(choir.memory[1]>.1&&choir.memory[0]>.001&&choir.audioPeak>.0001);
  await page.locator('#pause').click();await page.waitForFunction(()=>document.body.dataset.materialRunning==='false');
  const saved=JSON.parse(await download('#save','choir-before.json'));
  await page.waitForFunction(()=>document.querySelector('#recovery').dataset.saved==='true');await page.reload();
  await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Recovered the recent encounter'));
  assert.deepEqual(JSON.parse(await download('#save','choir-after.json')),saved);check('Live choir signal and exact paused recovery survive offline',choir);
  await open('/witness.html');await page.waitForFunction(()=>document.body.dataset.ready==='true');
  await page.locator('#play-question').click();await page.waitForFunction(()=>Number(document.body.dataset.position)>1);
  await page.locator('[data-body="G"]').click();await page.waitForFunction(()=>document.body.dataset.listener==='G'&&Number(document.body.dataset.position)>2);
  await page.locator('button[data-history="after"]').click();assert.equal(await page.locator('#difference').textContent(),'4.694 Hz');
  await page.locator('#play-question').click();check('The recorded witness changes listener without losing playback');
  await open('/observer.html');await page.waitForFunction(()=>document.body.dataset.ready==='true');
  await page.locator('#origin-next').click();assert.equal(await page.locator('body').getAttribute('data-ties'),'1');
  await page.locator('#origin-shift').focus();await page.keyboard.press('End');assert.equal(await page.locator('body').getAttribute('data-own'),'24');
  const drawing=await download('#origin-export','observer.svg');
  assert.equal((drawing.match(/data:font\/woff2;base64,/g)||[]).length,2);check('The moving observer exports its drawing with both fonts embedded');
  await open('/first-act.html');await page.waitForFunction(()=>document.querySelectorAll('#download-list a').length>0);
  check('The first viewing film plays and seeks locally',await film('#main-film','#enter-film',370,432));
  await localPdf(await page.locator('#notebook .arrow-link').getAttribute('href'));
  await open('/atlas.html');await page.waitForFunction(()=>!document.querySelector('#probe-play').disabled);
  assert.equal(await page.locator('.history-glyph').count(),120);await page.locator('#probe-play').click();
  await page.waitForFunction(()=>document.querySelector('#probe-0').currentTime>1);await page.locator('#probe-play').click();check('All 120 histories load and a recorded question plays');
  await open('/pressure.html');await page.waitForFunction(()=>document.body.dataset.pressureReady==='true');
  await page.getByRole('button',{name:'Allow for pressure',exact:true}).click();assert.equal(await page.locator('#identified-count').textContent(),'881 / 960');
  await download('#export-pressure','pressure.svg');check('The pressure explorer retains its measured result and SVG export');
  await open('/instrument.html');await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.state==='ready');
  await page.locator('#begin-sound').click();await page.waitForFunction(()=>document.body.dataset.running==='true');
  await page.keyboard.down('q');await page.waitForFunction(()=>Number(document.querySelector('#live-sculpture').dataset.time)>4);await page.keyboard.up('q');
  const first=await page.locator('#live-sculpture').evaluate(node=>({...node.dataset}));assert.ok(Number(first.memory)>.1&&Number(first.audioPeak)>.005);
  await page.locator('#pause-material').click();await page.waitForFunction(()=>document.querySelector('#live-sculpture').dataset.materialRunning==='false'&&document.querySelector('#recovery-note').dataset.saved==='true');
  const paused=await page.locator('#live-sculpture').evaluate(node=>({...node.dataset}));
  await page.waitForFunction(time=>Math.abs(Number(document.querySelector('#recovery-note').dataset.time)-Number(time))<.00001,paused.time);await page.reload();
  await page.waitForFunction(()=>Number(document.querySelector('#live-sculpture').dataset.time)>4);
  const recovered=await page.locator('#live-sculpture').evaluate(node=>({...node.dataset}));
  for(const key of ['time','memory','wear'])assert.equal(recovered[key],paused[key]);check('The first instrument retains signal and exact paused summary recovery');
  await page.setViewportSize({width:393,height:852});await open('/');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth),0);
  await page.screenshot({path:path.join(output,'mobile.jpg'),type:'jpeg',quality:80});check('The new mobile entry fits without horizontal overflow');
  assert.deepEqual(report.errors,[]);assert.deepEqual(report.consoleErrors,[]);assert.deepEqual(report.externalDependencies,[]);assert.deepEqual(report.failedLocalRequests,[]);
  await context.unroute('**/*');
  const blocked=await page.evaluate(async()=>{try{await fetch('https://example.com/',{mode:'no-cors',signal:AbortSignal.timeout(3000)});return false;}catch(error){return error.name==='TypeError';}});
  assert.ok(blocked);check('External connectivity is actually unavailable, beyond route interception');
  report.passed=true;
}catch(error){report.passed=false;report.failure=error.stack;process.exitCode=1;if(page&&!page.isClosed())await page.screenshot({path:path.join(output,'failure.jpg'),type:'jpeg',quality:75}).catch(()=>{});}
finally{
  if(browser)await browser.close();
  if(server&&server.exitCode===null&&server.signalCode===null){const closed=new Promise(resolve=>server.once('exit',resolve));server.kill('SIGTERM');await closed;}
  report.temporaryLoopbackServerClosed=!server||server.exitCode!==null||server.signalCode!==null;
  const sizes=await Promise.all((await fs.readdir(output)).map(async name=>(await fs.stat(path.join(output,name))).size));
  report.evidenceBytesBeforeReceipt=sizes.reduce((sum,value)=>sum+value,0);
  if(report.evidenceBytesBeforeReceipt>16_000_000){report.passed=false;report.failure='Browser evidence exceeded its reserved 16 MB';process.exitCode=1;}
  await fs.writeFile(path.join(output,'checks.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,evidenceBytes:report.evidenceBytesBeforeReceipt,report:path.join(output,'checks.json')}));
}
