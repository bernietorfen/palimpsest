import assert from 'node:assert/strict';
import {performance} from 'node:perf_hooks';
import {writeFile} from 'node:fs/promises';
import {LiveMaterial} from '../site/live-material.js';

const cases=[];
for(const protocol of ['maximum_chord','alternating_writing_and_forgetting','seeded_gestures']){
  const material=new LiveMaterial(),drive=new Float64Array(12),targets=new Float64Array(12);
  const duration=600,steps=duration*96,began=performance.now();
  let seed=20261004,peakU=0,peakV=0,maxMemory=0,maxWear=0,minPitch=Infinity,maxPitch=0;
  const random=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return(seed>>>0)/4294967296;};
  for(let step=0;step<steps;step++){
    const time=step/96;
    if(protocol==='maximum_chord')targets.fill(.6);
    else if(protocol==='alternating_writing_and_forgetting'){
      targets.fill(0);if(Math.floor(time/12)%2===0){targets[Math.floor(time/24)%12]=.6;targets[(Math.floor(time/24)+5)%12]=.6;}
    }else if(step%48===0){for(let m=0;m<12;m++)targets[m]=random()>.7?.15+.45*random():0;}
    for(let m=0;m<12;m++){const rate=targets[m]>drive[m] ? .12 : .48;drive[m]+=(targets[m]-drive[m])*(1-Math.exp(-material.config.dt/rate));}
    material.step(drive,protocol==='alternating_writing_and_forgetting'&&Math.floor(time/12)%2 ? .1 : .0008);
    if(step%96===0){
      const d=material.diagnostics();assert.ok(d.finite);
      peakU=Math.max(peakU,d.max_displacement);maxMemory=Math.max(maxMemory,d.memory_rms);maxWear=Math.max(maxWear,d.fatigue_mean);
      for(const value of material.v)peakV=Math.max(peakV,Math.abs(value));
      for(const value of material.p)assert.ok(Math.abs(value)<=.8);
      for(const value of material.z)assert.ok(value>=0&&value<=1);
      for(const value of material.pitch){assert.ok(Number.isFinite(value)&&value>0);minPitch=Math.min(minPitch,value);maxPitch=Math.max(maxPitch,value);}
    }
  }
  cases.push({protocol,duration_seconds:duration,steps,wall_seconds:(performance.now()-began)/1000,
    finite:true,retained_bounds:true,peak_displacement:peakU,peak_velocity:peakV,
    max_memory_rms:maxMemory,max_fatigue_mean:maxWear,pitch_range_hz:[minPitch,maxPitch],final:material.diagnostics()});
  console.log(JSON.stringify(cases.at(-1)));
}
const report={created_utc:new Date().toISOString(),cases,scope:'Three 600-second deterministic stress trajectories at the UI pressure limit. This checks these trajectories, not all possible gestures or a formal stability bound.'};
await writeFile('artifacts/analysis/live-stress-001.json',JSON.stringify(report,null,2)+'\n');
