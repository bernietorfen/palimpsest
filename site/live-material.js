// The material equations of PALIMPSEST, authored here, expressed in JavaScript.
// Fixed simulation time; wall-clock cadence never changes the integration step.
export const PITCHES = [110, 137.5, 146.6666667, 165, 183.3333333, 220,
  247.5, 275, 293.3333333, 330, 366.6666667, 440];
const PAIRS = [[1,0],[1,1],[2,1],[3,1],[2,3],[4,1],[3,3],[5,2],[4,3],[5,4],[6,5],[7,3]];
const TAU = 2 * Math.PI;
export const LIVE_CONFIG = Object.freeze({size:64, dt:1/96, stiffness:2.4,
  tension:1.2, bending:.08, damping:.38, cubic:.7, yield_strain:.095,
  write_rate:.32, memory_limit:.8, memory_diffusion:.035, forgetting:.0008,
  fatigue_rate:.26, fatigue_recovery:.001, feedback:.20, feedback_delay:.79,
  memory_tuning:.65, echo_twist:.018, force_scale:1.6});

export class LiveMaterial {
  constructor(options = {}) {
    this.config = {...LIVE_CONFIG, ...options};
    const c = this.config, n = c.size;
    if (![32,64,128].includes(n) || !Number.isFinite(c.dt) || c.dt <= 0 || c.dt > 1/96) {
      throw new Error('Unsupported live material resolution or timestep');
    }
    for (const value of Object.values(c)) if (!Number.isFinite(value)) throw new Error('Non-finite material constant');
    this.count = n*n;
    this.delayLength = Math.max(1, Math.round(c.feedback_delay/c.dt));
    for (const name of ['u','v','p','z','lapU','lapP']) this[name] = new Float64Array(this.count);
    for (const name of ['modes','weights','echoModes','echoQuadratures']) this[name] = new Float64Array(this.count*12);
    this.neighbors = new Uint32Array(this.count*4);
    this.delay = new Float64Array(this.delayLength*12);
    for (const name of ['phase','memory','fatigue','pitch','velocity','position','strain','amplitude','echoC','echoS']) this[name] = new Float64Array(12);
    this.index = 0;
    this.steps = 0;
    this.makePatterns();
    this.project();
  }

  makePatterns() {
    const n = this.config.size, count = this.count, q = new Float64Array(count*12);
    for (let y=0; y<n; y++) for (let x=0; x<n; x++) {
      const k = y*n+x, j = k*4;
      this.neighbors[j] = y*n+(x+n-1)%n;
      this.neighbors[j+1] = y*n+(x+1)%n;
      this.neighbors[j+2] = ((y+n-1)%n)*n+x;
      this.neighbors[j+3] = ((y+1)%n)*n+x;
    }
    for (let m=0; m<12; m++) {
      const [a,b] = PAIRS[m], phase = m*Math.PI*(3-Math.sqrt(5));
      let mean=0, meanQ=0;
      for (let y=0; y<n; y++) for (let x=0; x<n; x++) {
        const px=x*TAU/n, py=y*TAU/n, k=(y*n+x)*12+m;
        const first=a*px+b*py+phase, second=(a+1)*px-(b+1)*py-phase;
        const third=(b+2)*px+(a+1)*py+.7*phase;
        this.modes[k]=Math.cos(first)+.31*Math.sin(second)+.17*Math.cos(third);
        q[k]=-Math.sin(first)+.31*Math.cos(second)-.17*Math.sin(third);
        mean+=this.modes[k]; meanQ+=q[k];
      }
      mean/=count; meanQ/=count;
      let variance=0, varianceQ=0;
      for (let k=m; k<count*12; k+=12) {
        this.modes[k]-=mean; q[k]-=meanQ;
        variance+=this.modes[k]**2; varianceQ+=q[k]**2;
      }
      const rms=Math.sqrt(variance/count), rmsQ=Math.sqrt(varianceQ/count);
      let weightMean=0;
      for (let k=m; k<count*12; k+=12) {
        this.modes[k]/=rms; q[k]/=rmsQ;
        this.weights[k]=this.modes[k]**2; weightMean+=this.weights[k];
      }
      weightMean/=count;
      for (let k=m; k<count*12; k+=12) this.weights[k]/=weightMean;
    }
    const sy=Math.floor(n/7), sx=Math.floor(n/11);
    for (let y=0; y<n; y++) for (let x=0; x<n; x++) {
      const to=(y*n+x)*12, from=(((y+n-sy)%n)*n+(x+n-sx)%n)*12;
      for (let m=0; m<12; m++) {
        this.echoModes[to+m]=this.modes[from+m];
        this.echoQuadratures[to+m]=q[from+m];
      }
    }
  }

  step(excitation, forgetting = this.config.forgetting, fieldForce = null) {
    if (excitation.length !== 12) throw new Error('Twelve force envelopes are required');
    if (fieldForce && fieldForce.length !== this.count) throw new Error('External force must match the material grid');
    const c=this.config, dt=c.dt, count=this.count, grid=(c.size/128)**2;
    const {u,v,p,z,lapU,lapP,neighbors,modes,echoModes,echoQuadratures} = this;
    for (let m=0; m<12; m++) {
      const echo=Math.tanh(this.delay[this.index*12+m]/.18)*c.feedback;
      this.echoC[m]=echo*Math.cos(this.phase[m]);
      this.echoS[m]=echo*Math.sin(this.phase[m]);
    }
    for (let k=0; k<count; k++) {
      const j=k*4, a=neighbors[j], b=neighbors[j+1], d=neighbors[j+2], e=neighbors[j+3];
      lapU[k]=(u[a]+u[b]+u[d]+u[e]-4*u[k])*grid;
      lapP[k]=(p[a]+p[b]+p[d]+p[e]-4*p[k])*grid;
    }
    for (let k=0; k<count; k++) {
      const j=k*4, offset=k*12, difference=u[k]-p[k];
      const lap2=(lapU[neighbors[j]]+lapU[neighbors[j+1]]+lapU[neighbors[j+2]]+lapU[neighbors[j+3]]-4*lapU[k])*grid;
      let force=fieldForce ? fieldForce[k] : 0;
      for (let m=0; m<12; m++) {
        force+=c.force_scale*excitation[m]*modes[offset+m]
          +this.echoC[m]*echoModes[offset+m]+this.echoS[m]*echoQuadratures[offset+m];
      }
      const accel=c.tension*lapU[k]-c.bending*lap2-c.stiffness*(1-.58*z[k])*difference-c.cubic*difference**3+force;
      v[k]=(v[k]+dt*accel)/(1+dt*c.damping);
      u[k]+=dt*v[k];
      const strain=u[k]-p[k], excess=Math.max(0,Math.abs(strain)-c.yield_strain*(1-.35*z[k]));
      const write=c.write_rate*excess*Math.tanh(strain/.035), capacity=Math.max(0,1-(p[k]/c.memory_limit)**2);
      p[k]=Math.max(-c.memory_limit,Math.min(c.memory_limit,p[k]+dt*(write*capacity-forgetting*p[k]+c.memory_diffusion*lapP[k])));
      z[k]=Math.max(0,Math.min(1,z[k]+dt*(c.fatigue_rate*excess**2*(1-z[k])-c.fatigue_recovery*z[k])));
    }
    this.project();
    for (let m=0; m<12; m++) {
      this.phase[m]=((this.phase[m]+dt*TAU*c.echo_twist*(this.pitch[m]-PITCHES[m]))%TAU+TAU)%TAU;
      this.delay[this.index*12+m]=this.velocity[m];
    }
    this.index=(this.index+1)%this.delayLength;
    this.steps++;
  }

  project() {
    const count=this.count;
    this.memory.fill(0); this.fatigue.fill(0); this.velocity.fill(0); this.position.fill(0);
    for (let k=0; k<count; k++) for (let m=0; m<12; m++) {
      const j=k*12+m, f=this.modes[j];
      this.memory[m]+=this.p[k]*f;
      this.fatigue[m]+=this.z[k]*this.weights[j];
      this.velocity[m]+=this.v[k]*f;
      this.position[m]+=this.u[k]*f;
    }
    for (let m=0; m<12; m++) {
      this.memory[m]/=count; this.fatigue[m]/=count; this.velocity[m]/=count; this.position[m]/=count;
      this.strain[m]=this.position[m]-this.memory[m];
      this.pitch[m]=PITCHES[m]*Math.sqrt(1-.58*this.fatigue[m])*Math.exp(this.config.memory_tuning*this.memory[m]);
      this.amplitude[m]=Math.sqrt(this.velocity[m]**2+.55*this.strain[m]**2+1e-12);
    }
  }

  readout() {
    return Object.fromEntries(['position','velocity','strain','memory','fatigue','pitch','amplitude','phase'].map(name=>[name,Array.from(this[name])]));
  }

  fields(target = new Float32Array(this.count*4)) {
    for (let k=0; k<this.count; k++) {
      target[k*4]=this.u[k]; target[k*4+1]=this.p[k];
      target[k*4+2]=this.z[k]; target[k*4+3]=this.v[k];
    }
    return target;
  }

  diagnostics() {
    let memory=0, fatigue=0, displacement=0, finite=true;
    for (let k=0; k<this.count; k++) {
      memory+=this.p[k]**2; fatigue+=this.z[k]; displacement=Math.max(displacement,Math.abs(this.u[k]));
      finite=finite&&Number.isFinite(this.u[k]+this.v[k]+this.p[k]+this.z[k]);
    }
    return {time:this.steps*this.config.dt, memory_rms:Math.sqrt(memory/this.count),
      fatigue_mean:fatigue/this.count, max_displacement:displacement, finite};
  }

  snapshot() {
    return {format:'palimpsest-live-material',version:1,config:{...this.config},steps:this.steps,index:this.index,
      ...Object.fromEntries(['u','v','p','z','delay','phase'].map(name=>[name,Array.from(this[name])]))};
  }

  restore(state) {
    if (state?.format!=='palimpsest-live-material'||state.version!==1) throw new Error('This is not a PALIMPSEST material');
    for (const [key,value] of Object.entries(this.config)) if (state.config?.[key]!==value) throw new Error('The material uses different rules');
    if (!Number.isSafeInteger(state.steps)||state.steps<0||!Number.isInteger(state.index)||state.index<0||state.index>=this.delayLength) throw new Error('Invalid material clock');
    const names=['u','v','p','z','delay','phase'];
    for (const name of names) {
      const a=state[name];
      if (!Array.isArray(a)||a.length!==this[name].length||a.some(v=>!Number.isFinite(v)||Math.abs(v)>1e4)) throw new Error(`Invalid ${name} field`);
    }
    // Imported files must remain within a broad live operating envelope. These
    // are file-admission limits, not clamps applied to the material equations.
    if (state.u.some(v=>Math.abs(v)>16)||state.v.some(v=>Math.abs(v)>64)||state.delay.some(v=>Math.abs(v)>64)) throw new Error('The file exceeds the live material operating range');
    if (state.phase.some(v=>v<0||v>=TAU)) throw new Error('Invalid echo phase');
    if (state.p.some(v=>Math.abs(v)>this.config.memory_limit)||state.z.some(v=>v<0||v>1)) throw new Error('The retained fields exceed material bounds');
    // Validate the entire document before touching the running material.
    for (const name of names) this[name].set(state[name]);
    this.steps=state.steps; this.index=state.index; this.project();
  }
}
