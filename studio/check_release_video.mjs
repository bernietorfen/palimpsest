// Check native cross-origin playback before selecting a hosting arrangement.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {chromium,webkit} from '../.tools/browser/node_modules/playwright/index.mjs';
const engine=process.argv[2]??'chromium';
const browser=await(engine==='webkit'?webkit:chromium).launch({headless:true,args:engine==='chromium'?['--no-sandbox']:[]});
const page=await browser.newPage();const errors=[],responses=[],failed=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{const url=new URL(r.url());if(url.hostname!=='127.0.0.1')responses.push({host:url.hostname,status:r.status(),type:r.headers()['content-type'],range:r.headers()['content-range']});});page.on('requestfailed',r=>failed.push({host:new URL(r.url()).hostname,error:r.failure()?.errorText}));page.setDefaultTimeout(45000);
try{
 await page.goto('http://127.0.0.1:8766/');
 await page.evaluate(()=>{const video=document.querySelector('#main-film');video.src='https://github.com/bernietorfen/palimpsest/releases/download/v1.0.0/palimpsest-viewing-1080p.mp4';video.load();});
 await page.locator('#enter-film').click();await page.waitForFunction(()=>document.querySelector('#main-film').currentTime>1);
 await page.evaluate(()=>{document.querySelector('#main-film').currentTime=370;});await page.waitForFunction(()=>{const v=document.querySelector('#main-film');return v.currentTime>371&&!v.paused&&!v.seeking&&v.readyState>=2&&v.videoWidth===1920;});
 const result=await page.evaluate(()=>{const v=document.querySelector('#main-film');return{time:v.currentTime,duration:v.duration,readyState:v.readyState,width:v.videoWidth,height:v.videoHeight};});assert.equal(result.duration,432);assert.deepEqual(errors,[]);console.log(JSON.stringify({engine,...result,errors}));
}catch(error){console.log(JSON.stringify({engine,errors,responses,failed,media:await page.evaluate(()=>{const v=document.querySelector('#main-film');return{time:v.currentTime,duration:v.duration,readyState:v.readyState,networkState:v.networkState,paused:v.paused,error:v.error?{code:v.error.code,message:v.error.message}:null,status:document.querySelector('#film-status').textContent};})},null,2));throw error;}finally{await browser.close();}
