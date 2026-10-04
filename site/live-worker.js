import {LiveMaterial, LIVE_CONFIG} from './live-material.js';
import {LiveScore} from './live-score.js';
import {buildLiveSheet,sculptureSTL} from './live-geometry.js';

let material = new LiveMaterial(), running = false, timer = 0, last = 0, accumulator = 0;
let targets = new Float64Array(12), drive = new Float64Array(12), fading = false;
let frames = 0, lastFrame = 0, spare = new Float32Array(material.count*4), inFlight = false;
let generation = 0;
const score=new LiveScore();
let undo=null;
const MAX_CATCHUP = 12;

function publish(force = false) {
  if (inFlight && !force) return;
  if (!spare || spare.byteLength !== material.count*16) spare = new Float32Array(material.count*4);
  const fields = material.fields(spare);
  postMessage({type:'frame',generation,fields,readout:material.readout(),drive:Array.from(drive),
    diagnostics:material.diagnostics(),running,fading,targets:Array.from(targets),score:score.describe(material.steps)},[fields.buffer]);
  spare = null;
  inFlight = true;
  frames++;
}

function tick() {
  if (!running) return;
  const now = performance.now();
  accumulator += Math.min((now-last)/1000, .125);
  last = now;
  let steps = 0;
  while (accumulator >= LIVE_CONFIG.dt && steps < MAX_CATCHUP) {
    const oldMode=score.mode;
    const completed=score.beforeStep(material.steps,targets);
    if(oldMode!==score.mode)postMessage({type:'score',score:score.describe(material.steps),comparison:completed?score.comparison():null});
    for (let i=0;i<12;i++) {
      const rate=targets[i]>drive[i] ? .12 : .48;
      drive[i]+=(targets[i]-drive[i])*(1-Math.exp(-LIVE_CONFIG.dt/rate));
    }
    material.step(drive,fading ? .10 : LIVE_CONFIG.forgetting);
    score.sample(material.steps,material.pitch);
    accumulator-=LIVE_CONFIG.dt;
    steps++;
  }
  // A slow device slows the instrument's clock; it never changes its physics
  // or builds an unbounded backlog. Returning to this tab requires Resume.
  if (steps===MAX_CATCHUP) accumulator=Math.min(accumulator,LIVE_CONFIG.dt);
  if (now-lastFrame>=1000/24) { publish(); lastFrame=now; }
  timer=setTimeout(tick,Math.max(0,8-(performance.now()-now)));
}

function pause() {
  // Preserve the written part if the visitor pauses or leaves mid-capture.
  // Its two-second release will be heard when the kept phrase is replayed.
  if(score.mode==='recording')score.finish(material.steps);
  running=false;
  clearTimeout(timer);
  targets.fill(0); drive.fill(0); fading=false;
  accumulator=0;score.stop();
}

onmessage = ({data}) => {
  try {
    if (data.type==='recycle') {
      if (data.fields instanceof Float32Array && data.fields.length===material.count*4) spare=data.fields;
      inFlight=false;
    } else if (data.type==='run') {
      if (!running) { running=true; last=performance.now(); tick(); }
    } else if (data.type==='pause') {
      pause(); publish(true);
    } else if (data.type==='drive') {
      if (!Array.isArray(data.values)||data.values.length!==12||data.values.some(x=>!Number.isFinite(x)||x<0||x>.65)) throw new Error('Invalid gesture');
      if(score.mode==='replaying'||score.mode==='releasing')return;
      targets.set(data.values);score.event(material.steps,targets);
    } else if (data.type==='fade') {
      fading=Boolean(data.value);
    } else if (data.type==='fresh') {
      undo=material.snapshot();pause();material=new LiveMaterial();generation++;publish(true);postMessage({type:'undo',available:true});
    } else if (data.type==='undo') {
      if(undo){pause();material.restore(undo);undo=null;generation++;publish(true);postMessage({type:'undo',available:false});}
    } else if (data.type==='snapshot') {
      postMessage({type:'snapshot',request:data.request,state:{...material.snapshot(),phrase:score.phrase}});
    } else if (data.type==='sculpture') {
      pause();
      const time=material.steps*LIVE_CONFIG.dt;
      const result=sculptureSTL(buildLiveSheet(material.fields()),time);
      postMessage({type:'sculpture',time,...result},[result.buffer]);
      publish(true);
    } else if (data.type==='restore') {
      // Validation is atomic. A rejected file preserves the current session.
      const phrase=score.validate(data.state.phrase);
      material.restore(data.state);pause();score.phrase=phrase;score.clearResponses();undo=null;generation++;publish(true);
      postMessage({type:'undo',available:false});
      postMessage({type:'restored'});
    } else if (data.type==='record') {
      if(!running)throw new Error('Resume the material before recording a phrase');
      if(score.mode==='recording'){score.finish(material.steps);targets.fill(0);}
      else if(score.mode==='idle'){score.record(material.steps,drive,targets);}
      postMessage({type:'score',score:score.describe(material.steps),comparison:null});
    } else if (data.type==='replay') {
      if(!running)throw new Error('Resume the material before asking again');
      if(score.mode==='replaying'||score.mode==='releasing'){score.stop();targets.fill(0);}
      else{drive.set(score.replay(material.steps));targets.set(score.phrase.events[0].values);}
      postMessage({type:'score',score:score.describe(material.steps),comparison:null});
    } else if (data.type==='inspect') {
      postMessage({type:'inspection',request:data.request,frames,generation,running,diagnostics:material.diagnostics()});
    }
  } catch (error) {
    postMessage({type:'error',message:error.message});
  }
};
publish(true);
