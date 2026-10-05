// Focused native-caption regression. Run only on the authorized remote host.
// A captured metadata event places a caption choice deterministically between
// source loading and the application's completion handler; it is not a click
// through the browser's inaccessible native caption menu.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {chromium,webkit} from '../.tools/browser/node_modules/playwright/index.mjs';
import {checkQualityPlayback} from './river_media_checks.mjs';

const args=process.argv.slice(2),root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const argument=(name,fallback)=>{const index=args.indexOf(name);return index<0?fallback:args[index+1];};
const base=argument('--base','http://127.0.0.1:8778');
const script=path.resolve(argument('--script',path.join(root,'site/river.js')));
const out=path.resolve(argument('--out',path.join(root,'artwork/river-caption-check-001')));
assert.ok(['127.0.0.1','localhost','[::1]'].includes(new URL(base).hostname),'Use a private loopback server');
await fs.mkdir(out,{recursive:false});
const raw=await fs.readFile(script),sha256=bytes=>createHash('sha256').update(bytes).digest('hex');
await fs.writeFile(path.join(out,'river.js'),raw);
await fs.copyFile(fileURLToPath(import.meta.url),path.join(out,'check.mjs'));
const report={scope:'Actual loopback media with an explicitly supplied source override. Deterministic native TextTrack choices at captured loadedmetadata, followed by actual metadata/seek completion. Not physical native-menu input, continuous viewing, or audition.',base,source:{path:script,bytes:raw.length,sha256:sha256(raw)},checks:[],engines:{},passed:false};
let failure;
try{
  for(const [engine,launcher]of Object.entries({chromium,webkit})){
    const browser=await launcher.launch({headless:true,env:{...process.env,LIBGL_ALWAYS_SOFTWARE:'1'},...(engine==='chromium'?{args:['--disable-gpu']}: {})});
    try{
      const context=await browser.newContext({viewport:{width:1440,height:1080}}),page=await context.newPage();
      page.setDefaultTimeout(30000);
      await context.route(new URL('/river.js',base).href,route=>route.fulfill({status:200,contentType:'text/javascript',body:raw}));
      const response=await page.goto(base,{waitUntil:'networkidle'});
      report.engines[engine]={entrySha256:sha256(await response.body())};
      await page.evaluate(()=>{
        window.captionRegression={armed:null,events:[]};
        document.addEventListener('loadedmetadata',event=>{
          if(event.target.id!=='river-film'||!window.captionRegression.armed)return;
          const choice=window.captionRegression.armed;window.captionRegression.armed=null;
          const track=event.target.textTracks[0];
          const before=track.mode;track.mode=choice.mode;
          window.captionRegression.events.push({...choice,event:'captured loadedmetadata',before,after:track.mode,source:new URL(event.target.currentSrc).pathname,time:event.target.currentTime});
        },true);
      });
      async function arm(name,mode){await page.evaluate(({name,mode})=>{window.captionRegression.armed={name,mode};},{name,mode});}
      async function settled(source){
        await page.waitForFunction(source=>{const video=document.querySelector('#river-film');return video.currentSrc.endsWith(source)&&!video.paused&&!video.seeking&&video.currentTime>.3&&document.querySelector('.film-stage').dataset.videoState==='playing';},source);
      }
      async function record(name,expected){
        const value=await page.locator('#river-film').evaluate(video=>({mode:video.textTracks[0].mode,cues:video.textTracks[0].cues?.length??null,time:video.currentTime,seeking:video.seeking,stage:document.querySelector('.film-stage').dataset.videoState,events:window.captionRegression.events}));
        assert.equal(value.events.filter(event=>event.name===name).length,1,'Exactly one controlled early choice must occur');
        const passed=value.mode===expected;
        report.checks.push({engine,name,expected,...value,passed});
        return passed;
      }
      await arm('first-load choice','showing');await page.locator('#watch-film').click();
      await settled('/river-viewing.mp4');
      const firstPassed=await record('first-load choice','showing');
      await page.locator('#river-film').evaluate(video=>new Promise(resolve=>{video.pause();video.addEventListener('seeked',resolve,{once:true});video.currentTime=1.5;}));
      if(firstPassed)await page.waitForFunction(()=>document.querySelector('#river-film').textTracks[0].activeCues?.length>0);
      await page.locator('#river-film').screenshot({path:path.join(out,`${engine}-first-choice.jpg`),type:'jpeg',quality:78,animations:'disabled'});
      await page.locator('#river-film').evaluate(video=>{video.textTracks[0].mode='showing';video.play();});
      await settled('/river-viewing.mp4');
      await arm('switch choice off','disabled');await page.locator('[data-film-quality="compact"]').click();
      await settled('/river-compact.mp4');await record('switch choice off','disabled');
      await page.locator('#river-film').evaluate(video=>{video.textTracks[0].mode='disabled';});
      await arm('switch choice on','showing');await page.locator('[data-film-quality="full"]').click();
      await settled('/river-viewing.mp4');await record('switch choice on','showing');
      report.checks.push({engine,name:'existing paused/playing quality preservation',...await checkQualityPlayback(page,{finalDimensions:true}),passed:true});
      await context.close();
    }finally{await browser.close();}
  }
  report.passed=report.checks.every(check=>check.passed);
  if(!report.passed)failure=Error('A caption choice was overwritten by source completion');
}catch(error){failure=error;report.error={message:error.message,stack:error.stack};}
await fs.writeFile(path.join(out,'checks.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({output:path.join(out,'checks.json'),passed:report.passed,checks:report.checks.map(({engine,name,passed,expected,mode})=>({engine,name,passed,expected,mode})),error:report.error},null,2));
if(failure)process.exitCode=1;
