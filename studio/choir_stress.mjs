// A declared finite stress trajectory of the shipped live equations. RunPod only.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {performance} from 'node:perf_hooks';
import {LiveChoir} from '../site/choir-material.js';
const path=process.argv[2]??'research/choir-stress-001.json';if(fs.existsSync(path))throw new Error('Use a new receipt');
const scene=JSON.parse(fs.readFileSync('site/choir-scene.json','utf8')),choir=new LiveChoir(scene),began=performance.now(),records=[];
const duration=600,rate=96;let peakU=0,peakV=0,peakBridge=0,peakBridgeV=0;
for(let step=0;step<duration*rate;step++){
 const second=step/rate;
 if(step%(rate*7)===0){const event=Math.floor(second/7);choir.setContact(event%7,.12+(event%5)*.17,.13+((event*3)%5)*.16,(event%2?-1:1)*1.4);}
 if(step%(rate*19)===0){const epoch=Math.floor(second/19);choir.connect(scene.connections.map((edge,i)=>(i+epoch)%3===0?0:1),{newBridges:true});}
 if(step%(rate*61)===0&&step>0)choir.resetMotion();
 choir.step();
 if(step%rate===0){const d=choir.diagnostics();assert(d.finite);for(const body of choir.bodies){for(const x of body.u)peakU=Math.max(peakU,Math.abs(x));for(const x of body.v)peakV=Math.max(peakV,Math.abs(x));assert(body.p.every(v=>Math.abs(v)<=.8));assert(body.z.every(v=>v>=0&&v<=1));}for(const x of choir.u)peakBridge=Math.max(peakBridge,Math.abs(x));for(const x of choir.v)peakBridgeV=Math.max(peakBridgeV,Math.abs(x));}
 if(step%(rate*60)===rate*60-1){records.push(choir.diagnostics());console.log(JSON.stringify({time:(step+1)/rate,elapsed:(performance.now()-began)/1000,peakU,peakV,peakBridge,peakBridgeV}));}
}
choir.releaseContact();const state=choir.snapshot(),copy=new LiveChoir(scene);copy.restore(state);for(let i=0;i<96;i++){choir.step();copy.step();}assert.deepEqual(choir.snapshot(),copy.snapshot());
const before=copy.snapshot();for(const mutate of [s=>s.bodies[6].p[0]=NaN,s=>s.bridgeV[0]=100,s=>s.gates[3]=-.2,s=>s.bodies[2].steps+=1]){const bad=structuredClone(before);mutate(bad);assert.throws(()=>copy.restore(bad));assert.deepEqual(copy.snapshot(),before);}
const result={created_utc:new Date().toISOString(),simulation_seconds:duration,size:32,rate,wall_seconds:(performance.now()-began)/1000,peakU,peakV,peakBridge,peakBridgeV,all_finite:true,retained_bounds:true,exact_continuation:true,atomic_rejections:4,records,scope:'One deterministic ten-minute stress trajectory: alternating maximum UI pressure, moving contact, repeated cuts/rejoins and motion resets. This does not prove global stability or measure browser rendering performance.'};
fs.writeFileSync(path,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({...result,records:records.length}));
