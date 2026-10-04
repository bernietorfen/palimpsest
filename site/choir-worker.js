import {LiveChoir} from './choir-material.js';
let choir=null,running=false,timer=0,last=0,accumulator=0,lastFrame=0,inFlight=false,spare=null,failed=false;
let selected=1,contact=null,pressure=0,targetPressure=0,undo=null,generation=0,demoStart=null,scorePhase='';
let phase='waiting',pendingFrame=false;
const emit=()=>{
  if(!choir)return;
  if(inFlight){pendingFrame=true;return;}
  pendingFrame=false;
  const diagnostics=choir.diagnostics();
  if(!diagnostics.finite){pause();failed=true;postMessage({type:'fault',message:'The choir stopped because its state became non-finite. Open a saved choir or begin again.'});return;}
  const fields=choir.fields(spare??undefined);spare=null;inFlight=true;choir.coordinates();
  postMessage({type:'frame',fields,readout:choir.readout(),bridgeU:Array.from(choir.u),bridgeV:Array.from(choir.v),endpoints:Array.from(choir.endpoints),gates:Array.from(choir.gates),diagnostics,running,generation,selected,phase,demo:demoStart!==null},[fields.buffer]);
};
function pause(){running=false;clearTimeout(timer);accumulator=0;contact=null;targetPressure=pressure=0;choir?.releaseContact();}
function run(){if(failed)throw new Error('Open a saved choir before resuming');if(!running){running=true;last=performance.now();tick();}}
function pulse(t,start,amplitude,attack=.65,hold=.8,release=3.1){
  const x=t-start;if(x<0||x>=attack+hold+release)return 0;
  if(x<attack)return amplitude*.5*(1-Math.cos(Math.PI*x/attack));
  if(x<attack+hold)return amplitude;
  return amplitude*.5*(1+Math.cos(Math.PI*(x-attack-hold)/release));
}
function score(){
  if(demoStart===null)return;
  const t=(choir.steps-demoStart)*choir.dt;
  const fade=1-Math.max(0,Math.min(1,(t-64)/4)),outer=Math.max(0,Math.min(1,(t-24)/6));
  choir.connect(Array.from({length:12},(_,i)=>fade*(i<6?1:outer)));
  const events=[[1,.22,.5,3,.75],[1,.22,.5,10,.62],[1,.22,.5,17,.8],[3,.22,.5,25,.7],[3,.22,.5,32,-.85],[3,.22,.5,39,.62],[5,.62,.72,46,.72],[5,.62,.72,53,.85],[5,.62,.72,60,.66]];
  let active=null;
  for(const [body,x,y,start,amplitude]of events){const amount=pulse(t,start,amplitude);if(amount!==0)active={body,x,y,amount};}
  if(active){
    if(!contact||contact.body!==active.body||contact.x!==active.x||contact.y!==active.y){contact=active;choir.setContact(active.body,active.x,active.y,active.amount);}
    else choir.contact.strength=active.amount;
    selected=active.body;
  }else{choir.releaseContact();contact=null;}
  phase=t<3?'Before the first touch':t<24?'One voice enters':t<46?'The circle opens':t<64?'An exchange':t<68?'The connections leave':'What remains';
  if(t>=72){demoStart=null;phase='Your turn';contact=null;choir.releaseContact();postMessage({type:'demo-ended'});}
}
function tick(){
  if(!running)return;
  const now=performance.now();accumulator+=Math.min((now-last)/1000,.125);last=now;let steps=0;
  while(accumulator>=choir.dt&&steps<12){
    if(demoStart!==null)score();
    else if(contact){pressure+=(targetPressure-pressure)*(1-Math.exp(-choir.dt/.13));choir.contact.strength=pressure;}
    else if(Math.abs(pressure)>.0001){pressure*=Math.exp(-choir.dt/.22);if(choir.contact)choir.contact.strength=pressure;}
    else choir.releaseContact();
    choir.step();accumulator-=choir.dt;steps++;
  }
  if(steps===12)accumulator=Math.min(accumulator,choir.dt);
  if(now-lastFrame>=1000/24){emit();lastFrame=now;}
  if(running)timer=setTimeout(tick,Math.max(0,8-(performance.now()-now)));
}
onmessage=({data})=>{
  try{
    if(data.type==='init'){choir=new LiveChoir(data.scene);phase='Seven bodies, unwritten';emit();return;}
    if(!choir)throw new Error('The choir is still preparing');
    if(data.type==='recycle'){if(data.fields?.length===choir.bodies.length*choir.count*4)spare=data.fields;inFlight=false;if(pendingFrame)emit();}
    else if(data.type==='run')run();
    else if(data.type==='pause'){pause();emit();}
    else if(data.type==='select'){if(!Number.isInteger(data.body)||!choir.bodies[data.body])throw new Error('Invalid body');selected=data.body;emit();}
    else if(data.type==='contact'){
      if(!Number.isFinite(data.strength)||Math.abs(data.strength)>1.6)throw new Error('Invalid touch pressure');
      demoStart=null;phase='Writing into '+choir.scene.bodies[data.body]?.name;
      choir.setContact(data.body,data.x,data.y,pressure);contact={body:data.body,x:data.x,y:data.y};
      selected=data.body;targetPressure=data.strength;
    }else if(data.type==='release'){contact=null;targetPressure=0;phase=choir.gates.some(v=>v>0)?'Passing between bodies':'Separate, carrying their pasts';}
    else if(data.type==='leave-demo'){demoStart=null;contact=null;pressure=targetPressure=0;choir.releaseContact();phase='Your turn';emit();}
    else if(data.type==='connections'){
      demoStart=null;const values=Array(choir.edges.length).fill(data.connected?1:0);
      choir.connect(values,{newBridges:true});phase=data.connected?'The circle is joined':'The connections are cut';emit();
    }else if(data.type==='isolate'){
      demoStart=null;if(!Number.isInteger(data.body)||!choir.bodies[data.body])throw new Error('Invalid body');
      choir.connect(choir.edges.map((e,i)=>e.first[0]===data.body||e.second[0]===data.body?0:choir.gates[i]));phase='Voice '+choir.scene.bodies[data.body].name+' is separate';emit();
    }else if(data.type==='settle'){demoStart=null;contact=null;pressure=targetPressure=0;choir.resetMotion();phase='Motion cleared; inscriptions remain';emit();}
    else if(data.type==='snapshot')postMessage({type:'snapshot',request:data.request,state:choir.snapshot()});
    else if(data.type==='restore'){choir.restore(data.state);pause();demoStart=null;failed=false;generation++;phase='A saved encounter';emit();postMessage({type:'restored',source:data.source});}
    else if(data.type==='fresh'||data.type==='demo'){
      undo=failed?null:choir.snapshot();pause();choir=new LiveChoir(choir.scene);failed=false;generation++;phase='Seven bodies, unwritten';
      demoStart=data.type==='demo'?0:null;emit();postMessage({type:'undo',available:Boolean(undo)});if(data.type==='demo')run();
    }else if(data.type==='undo'&&undo){pause();choir.restore(undo);undo=null;failed=false;demoStart=null;generation++;phase='The previous encounter';emit();postMessage({type:'undo',available:false});}
    else if(data.type==='inspect')postMessage({type:'inspection',request:data.request,running,diagnostics:choir.diagnostics(),snapshot:choir.snapshot()});
  }catch(error){postMessage({type:'error',message:error.message,request:data.request});}
};
