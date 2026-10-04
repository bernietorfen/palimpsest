import assert from 'node:assert/strict';
import {LiveRecovery} from '../site/live-recovery.js';
import {LiveMaterial} from '../site/live-material.js';
import {LiveScore} from '../site/live-score.js';

const values=new Map([['unrelated','keep me']]);let denyWrites=false;
const storage={getItem:key=>values.get(key)??null,removeItem:key=>values.delete(key),
  setItem(key,value){if(denyWrites)throw new Error('Quota exceeded');values.set(key,value);}};
const recovery=new LiveRecovery(storage),material=new LiveMaterial(),drive=new Float64Array(12);
drive[4]=.36;
for(let step=0;step<384;step++)material.step(drive);
const state={...material.snapshot(),phrase:null,replies:[null,null]};
assert.equal(recovery.write(state),true);
assert.deepEqual(recovery.read().state,state);
const copy=values.get('palimpsest-live-recovery-v1');
denyWrites=true;
assert.equal(recovery.write({...state,steps:999}),false);
assert.equal(values.get('palimpsest-live-recovery-v1'),copy);
denyWrites=false;
assert.equal(recovery.write({...state,oversized:'x'.repeat(1_500_000)}),false);
assert.equal(values.get('palimpsest-live-recovery-v1'),copy);
values.set('palimpsest-live-recovery-v1','{corrupt');
assert.equal(recovery.read(),null);
assert.deepEqual([...values],[['unrelated','keep me']]);
assert.equal(new LiveRecovery(null).write(state),false);

const before=material.snapshot(),invalid=[];
for(const mutate of [s=>s.u.fill(9999),s=>s.v[0]=65,s=>s.delay[0]=-65,
  s=>s.phase[0]=2*Math.PI,s=>s.phase[0]=-.1,s=>s.p[0]=.81,
  s=>s.z[0]=-1,s=>s.u[0]=NaN,s=>s.steps=Number.MAX_SAFE_INTEGER+1]){
  const bad=structuredClone(before);mutate(bad);
  assert.throws(()=>material.restore(bad));assert.deepEqual(material.snapshot(),before);invalid.push(true);
}
const score=new LiveScore();
const phrase={version:1,dt:1/96,initial_drive:Array(12).fill(0),duration_steps:384,
  events:[{step:0,values:Array(12).fill(.3)},{step:192,values:Array(12).fill(0)}]};
const response=Array.from({length:96},(_,i)=>({step:(i+1)*4,pitch:Array.from({length:12},(_,voice)=>100+voice+i/100)}));
assert.deepEqual(score.validateResponses([response,response],score.validate(phrase)),[response,response]);
for(const bad of [[response.slice(1),response],[response,null],[response,[...response,{step:388,pitch:Array(12).fill(100)}]]])assert.throws(()=>score.validateResponses(bad,phrase));
const bad=structuredClone(response);bad[10].pitch[2]=Infinity;
assert.throws(()=>score.validateResponses([response,bad],phrase));
assert.deepEqual(score.validateResponses(undefined,null),[null,null]);
const restored=new LiveMaterial();restored.restore(state);
assert.deepEqual(restored.snapshot(),material.snapshot());
console.log(JSON.stringify({bounded_single_copy:true,copy_characters:copy.length,
  denied_or_oversized_write_preserves_last_copy:true,corrupt_copy_removes_only_owned_key:true,
  invalid_material_cases_rejected_atomically:invalid.length,valid_material_roundtrip_exact:true,
  completed_replies_roundtrip_exact:true,invalid_reply_cases_rejected:4,
  original_material_files_without_replies_accepted:true}));
