// Reciprocal wave bridges between PALIMPSEST bodies. Authored for the second act.
// Both forces use the same old state. The footprint is also the endpoint reader.
import {LiveMaterial} from './live-material.js';

export function footprint(size, x, y, width=.16) {
  if (![x,y,width].every(Number.isFinite)||x<0||x>=1||y<0||y>=1||width<.04||width>.3) throw new Error('Invalid contact point');
  const values=new Float64Array(size*size);let norm=0;
  for(let j=0;j<size;j++)for(let i=0;i<size;i++){
    const dx=((i/size-x+.5)%1+1)%1-.5,dy=((j/size-y+.5)%1+1)%1-.5;
    const v=Math.exp(-(dx*dx+dy*dy)/(2*width*width));values[j*size+i]=v;norm+=v*v;
  }
  norm=Math.sqrt(norm/values.length);for(let i=0;i<values.length;i++)values[i]/=norm;
  return values;
}

export class LiveChoir {
  constructor(scene, options={}){
    if(scene.format!=='palimpsest-choir-scene'||scene.version!==1)throw new Error('Unsupported choir scene');
    this.scene=scene;this.size=options.size??scene.material.live_size;
    this.bodies=scene.bodies.map(()=>new LiveMaterial({size:this.size,dt:options.dt??1/scene.material.rate,feedback:scene.material.feedback}));
    this.count=this.size*this.size;this.dt=this.bodies[0].config.dt;
    this.beads=scene.bridge.beads;this.edges=scene.connections;
    this.ports=this.edges.flatMap(e=>[e.first,e.second]).map(p=>({body:p[0],map:footprint(this.size,p[1],p[2],scene.bridge.port_width)}));
    this.u=new Float64Array(this.edges.length*this.beads);this.v=new Float64Array(this.u.length);this.acceleration=new Float64Array(this.u.length);
    this.gates=new Float64Array(this.edges.length).fill(1);this.endpoints=new Float64Array(this.edges.length*2);
    this.forces=this.bodies.map(()=>new Float64Array(this.count));this.zero=new Float64Array(12);
    this.contact=null;
    if(this.edges.some(e=>Math.sqrt(4*e.tension*(this.beads+1)/(scene.bridge.mass/this.beads))*this.dt>=1.5))throw new Error('Bridge timestep exceeds its admitted bound');
    this.sceneIdentity=JSON.stringify({material:scene.material,bridge:scene.bridge,connections:scene.connections,bodies:scene.bodies.map(b=>b.name)});
  }
  get steps(){return this.bodies[0].steps;}
  coordinates(){
    for(let p=0;p<this.ports.length;p++){
      const port=this.ports[p],field=this.bodies[port.body].u;let sum=0;
      for(let k=0;k<this.count;k++)sum+=field[k]*port.map[k];this.endpoints[p]=sum/this.count;
    }
    return this.endpoints;
  }
  setContact(body,x,y,strength=1){
    if(!Number.isInteger(body)||body<0||body>=this.bodies.length||!Number.isFinite(strength)||Math.abs(strength)>1.6)throw new Error('Invalid touch');
    this.contact={body,x,y,strength,map:footprint(this.size,x,y,this.scene.bridge.port_width)};
  }
  releaseContact(){this.contact=null;}
  step(excitations=null, external=null){
    for(const f of this.forces)f.fill(0);this.coordinates();
    const beads=this.beads,mass=this.scene.bridge.mass/beads;
    for(let e=0;e<this.edges.length;e++){
      const offset=e*beads,k=this.edges[e].tension*(beads+1)*this.gates[e];
      const left=this.endpoints[e*2],right=this.endpoints[e*2+1];
      for(let j=0;j<beads;j++)this.acceleration[offset+j]=k/mass*((j?this.u[offset+j-1]:left)-2*this.u[offset+j]+(j+1<beads?this.u[offset+j+1]:right));
      const a=k*(this.u[offset]-left),b=k*(this.u[offset+beads-1]-right);
      for(const [p,force] of [[e*2,a],[e*2+1,b]]){
        const port=this.ports[p],target=this.forces[port.body];for(let j=0;j<this.count;j++)target[j]+=force*port.map[j];
      }
    }
    if(this.contact){const {body,map,strength}=this.contact,force=this.forces[body];for(let k=0;k<this.count;k++)force[k]+=map[k]*strength;}
    for(let i=0;i<this.bodies.length;i++){
      if(external?.[i])for(let k=0;k<this.count;k++)this.forces[i][k]+=external[i][k];
      this.bodies[i].step(excitations?.[i]??this.zero,undefined,this.forces[i]);
    }
    const denominator=1+this.dt*this.scene.bridge.damping;
    for(let k=0;k<this.u.length;k++){this.v[k]=(this.v[k]+this.dt*this.acceleration[k])/denominator;this.u[k]+=this.dt*this.v[k];}
  }
  connect(values,{newBridges=false}={}){
    if(values.length!==this.gates.length||Array.from(values).some(v=>!Number.isFinite(v)||v<0||v>1))throw new Error('Invalid connections');
    if(newBridges){
      this.coordinates();
      for(let e=0;e<this.edges.length;e++)if(values[e]>0&&this.gates[e]===0){
        for(let j=0;j<this.beads;j++){const t=(j+1)/(this.beads+1);this.u[e*this.beads+j]=this.endpoints[e*2]*(1-t)+this.endpoints[e*2+1]*t;this.v[e*this.beads+j]=0;}
      }
    }
    this.gates.set(values);
  }
  resetMotion(){
    for(const body of this.bodies){body.u.set(body.p);body.v.fill(0);body.delay.fill(0);body.phase.fill(0);body.project();}
    this.coordinates();for(let e=0;e<this.edges.length;e++)for(let j=0;j<this.beads;j++){const t=(j+1)/(this.beads+1);this.u[e*this.beads+j]=this.endpoints[e*2]*(1-t)+this.endpoints[e*2+1]*t;}
    this.v.fill(0);this.releaseContact();
  }
  fields(target=new Float32Array(this.bodies.length*this.count*4)){
    for(let i=0;i<this.bodies.length;i++)this.bodies[i].fields(target.subarray(i*this.count*4,(i+1)*this.count*4));return target;
  }
  readout(){return this.bodies.map(body=>body.readout());}
  diagnostics(){
    const bodies=this.bodies.map(b=>b.diagnostics());return {time:this.steps*this.dt,bodies,finite:bodies.every(b=>b.finite)&&this.u.every(Number.isFinite)&&this.v.every(Number.isFinite)};
  }
  snapshot(){
    return {format:'palimpsest-live-choir',version:1,scene:this.sceneIdentity,bodies:this.bodies.map(b=>b.snapshot()),bridgeU:Array.from(this.u),bridgeV:Array.from(this.v),gates:Array.from(this.gates)};
  }
  restore(state){
    if(state?.format!=='palimpsest-live-choir'||state.version!==1||state.scene!==this.sceneIdentity||!Array.isArray(state.bodies)||state.bodies.length!==this.bodies.length)throw new Error('This file belongs to a different choir');
    for(const [name,count,limit]of[['bridgeU',this.u.length,16],['bridgeV',this.v.length,64],['gates',this.gates.length,1]]){
      const a=state[name];if(!Array.isArray(a)||a.length!==count||a.some(v=>!Number.isFinite(v)||Math.abs(v)>limit)||(name==='gates'&&a.some(v=>v<0)))throw new Error('Invalid saved connections');
    }
    const staged=state.bodies.map(s=>{const body=new LiveMaterial(this.bodies[0].config);body.restore(s);return body;});
    if(staged.some(b=>b.steps!==staged[0].steps||b.index!==staged[0].index))throw new Error('The saved body clocks differ');
    this.bodies=staged;this.u.set(state.bridgeU);this.v.set(state.bridgeV);this.gates.set(state.gates);this.releaseContact();this.coordinates();
  }
}
