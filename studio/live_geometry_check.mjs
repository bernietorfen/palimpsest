import {mkdir,writeFile} from 'node:fs/promises';
import {performance} from 'node:perf_hooks';
import {LiveMaterial} from '../site/live-material.js';
import {buildLiveSheet,sculptureSTL,pointAt,windowAt} from '../site/live-geometry.js';

const root=process.argv[2]||'artifacts/analysis/live-geometry-001';
await mkdir(root,{recursive:false});
const material=new LiveMaterial(),drive=new Float64Array(12),cases=[];
for(const[name,duration,forget]of[['fresh',0,.0008],['inscribed',8,.0008],['worn',88,.0008],['faded',16,.1]]){
  for(let step=0;step<duration*96;step++){
    for(let voice=0;voice<12;voice++)drive[voice]=name==='faded'?0:(voice%3===Math.floor(material.steps/288)%3?.42:0);
    material.step(drive,forget);
  }
  const fields=material.fields(),began=performance.now(),mesh=buildLiveSheet(fields),stl=sculptureSTL(mesh,material.steps/96);
  await writeFile(`${root}/${name}.stl`,new Uint8Array(stl.buffer));
  await writeFile(`${root}/${name}.f32`,new Uint8Array(fields.buffer));
  const parameters=Array.from({length:65},(_,i)=>[-1+2*(i%13)/12,-Math.PI+4*Math.PI*Math.floor(i/13)/4]);
  cases.push({name,...stl.stats,build_ms:performance.now()-began,time:material.steps/96,
    parameters,positions:parameters.map(([s,phi])=>pointAt(s,phi,fields,64,1)),
    windows:parameters.map(([s,phi])=>windowAt(s,phi,fields,64))});
  console.log(JSON.stringify({name,triangles:stl.stats.triangles,bytes:stl.stats.bytes,ms:cases.at(-1).build_ms}));
}
await writeFile(`${root}/construction.json`,JSON.stringify({created_utc:new Date().toISOString(),cases},null,2)+'\n');
