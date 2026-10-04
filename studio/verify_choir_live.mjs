// Run on RunPod. Independent JS result for Python comparison and continuation.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {performance} from 'node:perf_hooks';
import {LiveChoir} from '../site/choir-material.js';
const scene=JSON.parse(fs.readFileSync('site/choir-scene.json','utf8'));
const choir=new LiveChoir(scene),started=performance.now(),snapshots=[];
for(let i=0;i<2304;i++){
  if(i===0)choir.setContact(1,.22,.5,1.1);
  if(i===480)choir.releaseContact();
  if(i===960)choir.setContact(3,.63,.4,-.8);
  if(i===1440){choir.releaseContact();choir.connect(Array(12).fill(0));}
  if(i===1728)choir.connect(Array(12).fill(1),{newBridges:true});
  choir.step();
  if([0,479,959,1439,1727,2303].includes(i))snapshots.push({step:i+1,fields:Array.from(choir.fields()),bridgeU:Array.from(choir.u),bridgeV:Array.from(choir.v),readout:choir.readout()});
}
const elapsed=performance.now()-started,state=choir.snapshot(),copy=new LiveChoir(scene);copy.restore(state);
for(let i=0;i<96;i++){choir.step();copy.step();}
assert.deepEqual(choir.snapshot(),copy.snapshot());
const before=copy.snapshot(),bad=structuredClone(before);bad.bodies[6].p[9]=9;
assert.throws(()=>copy.restore(bad));assert.deepEqual(copy.snapshot(),before);
const report={steps:2304,seconds:elapsed/1000,simulation_seconds:24,realtime_ratio:24000/elapsed,size:choir.size,bodies:7,exact_continuation:true,atomic_rejection:true,diagnostics:choir.diagnostics(),snapshots};
const output=process.argv[2];if(!output||fs.existsSync(output))throw new Error('Provide a new output file');
fs.writeFileSync(output,JSON.stringify(report));console.log(JSON.stringify({...report,snapshots:`${snapshots.length} complete states in ${output}`}));
