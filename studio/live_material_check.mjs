import {performance} from 'node:perf_hooks';
import {LiveMaterial} from '../site/live-material.js';

const size=Number(process.argv[2]||64), dt=Number(process.argv[3]||1/96);
const material=new LiveMaterial({size,dt}), force=new Float64Array(12);
const steps=Math.round(24/dt), started=performance.now();
for(let i=0;i<steps;i++) {
  const t=i*dt;
  for(let m=0;m<12;m++) {
    const local=t-m*.81;
    force[m]=local>0&&local<5 ? .26*Math.sin(Math.PI*local/5)**2 : 0;
  }
  material.step(force,t>17?.075:.0008);
}
const elapsed=performance.now()-started, state=material.snapshot();
const restored=new LiveMaterial({size,dt});
restored.restore(state);
force.fill(0);
for(let k=0;k<96;k++) { material.step(force); restored.step(force); }
if(JSON.stringify(material.snapshot())!==JSON.stringify(restored.snapshot())) throw new Error('Checkpoint continuation differs');
const before=JSON.stringify(restored.snapshot());
const invalid=structuredClone(state); invalid.z[0]=2;
let rejected=false;
try { restored.restore(invalid); } catch { rejected=true; }
if(!rejected||JSON.stringify(restored.snapshot())!==before) throw new Error('Invalid import mutated state');
const fresh=new LiveMaterial({size,dt});
for(let k=0;k<96;k++) fresh.step(force);
if(fresh.u.some(Boolean)||fresh.p.some(Boolean)||fresh.z.some(Boolean)) throw new Error('Unforced material drift');
console.log(JSON.stringify({state,elapsed_ms:elapsed,steps_per_second:steps/(elapsed/1000),
  checkpoint_exact:true,invalid_import_atomic:true,silence_exact:true}));
