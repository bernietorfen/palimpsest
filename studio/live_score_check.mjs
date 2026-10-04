import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {LiveMaterial} from '../site/live-material.js';
import {LiveScore} from '../site/live-score.js';

const dt=1/96, material=new LiveMaterial(), score=new LiveScore();
const drive=new Float64Array(12),targets=new Float64Array(12),writtenForces=[];
const commands=new Map([[0,[0,.36]],[73,[4,.24]],[158,[2,.31]],[244,[7,.18]],[350,[3,.29]],[450,[-1,0]]]);
const envelope=()=>{for(let i=0;i<12;i++){const rate=targets[i]>drive[i] ? .12 : .48;drive[i]+=(targets[i]-drive[i])*(1-Math.exp(-dt/rate));}};
score.record(0,drive,targets);
for(let step=0;step<800;step++){
  if(commands.has(step)){
    targets.fill(0);const[voice,level]=commands.get(step);if(voice>=0)targets[voice]=level;score.event(step,targets);
  }
  if(step===500){score.finish(step);targets.fill(0);}
  if(score.beforeStep(step,targets))break;
  envelope();writtenForces.push(Array.from(drive));material.step(drive);score.sample(material.steps,material.pitch);
}
assert.equal(score.mode,'idle');assert.equal(score.phrase.duration_steps,692);
const originalState=material.snapshot(),originalResponse=structuredClone(score.lastResponse);
const phrase=score.validate(JSON.parse(JSON.stringify(score.phrase)));
assert.deepEqual(phrase,score.phrase);
assert.equal(writtenForces.length,692);
let rejected=0;
for(const mutate of [p=>p.events[0].values[0]=Infinity,p=>p.events[1].step=-1,p=>p.duration_steps=1e9,p=>p.events.at(-1).values[0]=.2]){
  const bad=structuredClone(phrase);mutate(bad);assert.throws(()=>score.validate(bad));rejected++;
}

function replay(targetMaterial,targetScore){
  const offset=targetMaterial.steps;
  drive.set(targetScore.replay(offset));targets.set(targetScore.phrase.events[0].values);
  let maxForceError=0;
  for(let local=0;local<=phrase.duration_steps;local++){
    if(targetScore.beforeStep(offset+local,targets))break;
    envelope();
    for(let i=0;i<12;i++)maxForceError=Math.max(maxForceError,Math.abs(drive[i]-writtenForces[local][i]));
    targetMaterial.step(drive);targetScore.sample(targetMaterial.steps,targetMaterial.pitch);
  }
  assert.equal(maxForceError,0);
  return maxForceError;
}
const fresh=new LiveMaterial(),freshScore=new LiveScore();freshScore.phrase=phrase;
replay(fresh,freshScore);
assert.deepEqual(fresh.snapshot(),originalState);
assert.deepEqual(freshScore.lastResponse,originalResponse);
replay(material,score);
const comparison=score.comparison();
assert.ok(comparison&&comparison.rms_hz>.001);
const report={created_utc:new Date().toISOString(),duration_seconds:phrase.duration_steps*dt,
  gesture_events:phrase.events.length,force_envelopes_identical:true,fresh_replay_state_identical:true,
  fresh_replay_readouts_identical:true,invalid_phrases_rejected:rejected,
  repeated_on_changed_material:{rms_hz:comparison.rms_hz,samples:comparison.samples},
  scope:'Actual JavaScript solver and score: captured input force envelopes replay exactly; fresh-state repetition is exact; changed-state repetition has a different answer. This is a deterministic implementation check, not a perceptual claim.'};
const destination=process.argv[2]||'artifacts/analysis/live-score-001.json';
await writeFile(destination,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
