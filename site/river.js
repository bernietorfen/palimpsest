const $=selector=>document.querySelector(selector);
const film=$('#river-film'),stage=$('.film-stage'),watch=$('#watch-film');
let filmRequest=0,pausedAway=false,frameWatch=null;

function filmState(value,message=''){
  stage.dataset.videoState=value;
  watch.hidden=!['idle','error'].includes(value);
  $('#film-wait').hidden=value!=='loading';
  $('#film-status').textContent=message;
  $('#film-retry').hidden=value!=='error';
  $('#film-next').hidden=value!=='ended';
}

function stopFrameWatch(){if(frameWatch!==null)film.cancelVideoFrameCallback?.(frameWatch);frameWatch=null;}
function watchPresentedFrame(){
  if(frameWatch!==null||typeof film.requestVideoFrameCallback!=='function')return;
  frameWatch=film.requestVideoFrameCallback(()=>{
    frameWatch=null;
    // Some media backends continue presenting frames while delaying `playing`
    // after a seek. A fresh displayed frame is sufficient to clear buffering.
    if(!film.paused&&!film.ended&&!document.hidden&&stage.dataset.videoState==='loading'){
      pausedAway=false;filmState('playing');
    }
  });
}

async function playFilm({retry=false}={}){
  const request=++filmRequest;
  film.controls=true;
  film.muted=false;
  filmState('loading','Opening the film. Sound begins when it is ready.');
  if(retry||!film.getAttribute('src')){film.src=film.dataset.src;film.load();}
  try{await film.play();if(request===filmRequest&&!film.paused&&!film.ended)filmState('playing');}
  catch(error){
    if(request!==filmRequest)return;
    if(error.name==='AbortError')return;
    if(film.error)filmState('error','The film could not open. Try again, or use the separate video link.');
    else filmState('paused','Use the video’s play control to begin.');
  }
}
watch.addEventListener('click',()=>playFilm({retry:stage.dataset.videoState==='error'}));
$('#film-retry').addEventListener('click',()=>playFilm({retry:true}));
film.addEventListener('loadedmetadata',()=>{$('#film-fullscreen').disabled=false;});
film.addEventListener('play',watchPresentedFrame);
film.addEventListener('playing',()=>{if(film.paused||film.ended)return;stopFrameWatch();pausedAway=false;filmState('playing');});
film.addEventListener('waiting',()=>{if(!film.paused){filmState('loading','The film is buffering. Your place is kept.');watchPresentedFrame();}});
film.addEventListener('pause',()=>{stopFrameWatch();if(!film.ended&&stage.dataset.videoState!=='error')filmState('paused',pausedAway?'Paused while this page was away. Use Play to continue.':'');});
film.addEventListener('ended',()=>{stopFrameWatch();filmState('ended','The film has ended. Try changing the view below.');});
film.addEventListener('error',()=>{stopFrameWatch();$('#film-fullscreen').disabled=true;filmState('error','The film could not open. Try again, or use the separate video link.');});
$('#film-fullscreen').addEventListener('click',async()=>{
  try{
    if(film.requestFullscreen)await film.requestFullscreen();
    else if(film.webkitEnterFullscreen)film.webkitEnterFullscreen();
    else $('#film-status').textContent='Use the video’s full-screen control, or open the separate film.';
  }catch{$('#film-status').textContent='Full screen is unavailable here. The film can still play in this page.';}
});
document.addEventListener('visibilitychange',()=>{if(document.hidden){filmRequest++;pausedAway=true;film.pause();if(film.src&&!film.ended&&stage.dataset.videoState!=='error')filmState('paused','Paused while this page was away. Use Play to continue.');}});
window.addEventListener('pagehide',()=>{filmRequest++;stopFrameWatch();film.pause();});

const NS='http://www.w3.org/2000/svg',TAU=2*Math.PI,FILM_PERIOD=104;
let clock=null,current=null,initial=null,observer='disconnected',ready=false,loading=false,returned=false,stateRevision=0,returning=false,returnFrame=0;
const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
const withinColors=['#805536','#465e60','#80745d','#4e7776'];
const edgeKey=edge=>edge.join(':');
function svg(tag,attributes={}){const node=document.createElementNS(NS,tag);for(const [key,value]of Object.entries(attributes))node.setAttribute(key,String(value));return node;}
function clockLabel(seconds){return `${Math.floor(seconds/60).toString().padStart(2,'0')}:${Math.floor(seconds%60).toString().padStart(2,'0')}`;}
function number(value){return value<1e-24?'below 10⁻²⁴':value<.001?value.toExponential(3):value.toFixed(6);}
function announceReading(message){const node=$('#clock-status');if(node.textContent!==message)node.textContent=message;}
function pathData(points){return points.map((point,index)=>`${index?'L':'M'}${point[0].toFixed(4)},${point[1].toFixed(4)}`).join(' ');}
function normReading(state,edge){const value=clock.coherence(state,...edge),scale=Math.sqrt(clock.parameters.populations[edge[0]]*clock.parameters.populations[edge[1]]);return{real:value.real/scale,imaginary:value.imaginary/scale};}

// Every displayed displacement is an authored map of both calculated quadratures.
// The reference geometry is evaluated from the same mapping at time zero.
function readingCurve(edge,state){
  const value=normReading(state,edge),firstGroup=Math.floor(edge[0]/8),secondGroup=Math.floor(edge[1]/8);
  const points=[];
  if(firstGroup===secondGroup){
    const strand=edge[0]%8,base=179+strand*6.7,center=-Math.PI/2+firstGroup*Math.PI/2;
    for(let k=0;k<=72;k++){
      const s=k/72,window=Math.sin(Math.PI*s),angle=center+(s-.5)*1.31+.07*value.imaginary*window;
      const radius=base+28*(value.real-1)*window*window+31*value.imaginary*Math.sin(2*Math.PI*s)*window;
      points.push([500+radius*1.50*Math.cos(angle),300+radius*.98*Math.sin(angle)]);
    }
  }else{
    const angleA=-Math.PI/2+firstGroup*Math.PI/2+.61,angleB=-Math.PI/2+secondGroup*Math.PI/2-.61;
    const a=[500+220*1.5*Math.cos(angleA),300+220*.98*Math.sin(angleA)];
    const b=[500+220*1.5*Math.cos(angleB),300+220*.98*Math.sin(angleB)];
    const midpoint=(angleA+angleB)/2,normal=[Math.cos(midpoint),Math.sin(midpoint)];
    const tangent=[-normal[1],normal[0]],shift=92*(value.real-1),slide=105*value.imaginary;
    const c=[500+normal[0]*(200+shift)*1.5+tangent[0]*slide,300+normal[1]*(200+shift)*.98+tangent[1]*slide];
    for(let k=0;k<=72;k++){const s=k/72;points.push([(1-s)**2*a[0]+2*(1-s)*s*c[0]+s*s*b[0],(1-s)**2*a[1]+2*(1-s)*s*c[1]+s*s*b[1]]);}
  }
  return pathData(points);
}

function renderDrawing(){
  const reference=$('#clock-reference'),drawing=$('#clock-current'),labels=$('#clock-labels');
  reference.replaceChildren();drawing.replaceChildren();labels.replaceChildren();
  const graph=clock.graphs[observer];
  for(const edge of graph.edges){
    const group=Math.floor(edge[0]/8),bridge=group!==Math.floor(edge[1]/8);
    const ref=svg('path',{d:readingCurve(edge,initial),class:'reference-line','data-edge':edgeKey(edge)});
    const path=svg('path',{d:readingCurve(edge,current),class:`readout-line${bridge?' bridge-line':''}`,stroke:bridge?'#a35a30':withinColors[group],'data-edge':edgeKey(edge),'data-reading':bridge?'bridge':'within'});
    reference.append(ref);drawing.append(path);
  }
  const positions=[[500,41],[897,307],[500,572],[102,307]];
  positions.forEach(([x,y],index)=>{const label=svg('text',{x,y,'text-anchor':'middle',class:'group-label'});label.textContent=['I','II','III','IV'][index];labels.append(label);});
  const within=clock.graphs.disconnected.edges;
  const agreement=within.filter(edge=>{const a=clock.coherence(current,...edge),b=clock.coherence(initial,...edge);return Math.hypot(a.real-b.real,a.imaginary-b.imaginary)<1e-12;}).length;
  const seconds=current.time/TAU*FILM_PERIOD,measure=clock.measure(current,observer);
  const bridges=clock.graphs.connected.edges.filter(edge=>Math.floor(edge[0]/8)!==Math.floor(edge[1]/8));
  const changed=bridges.filter(edge=>{const a=clock.coherence(current,...edge),b=clock.coherence(initial,...edge);return Math.hypot(a.real-b.real,a.imaginary-b.imaginary)>1e-12;}).length;
  const allBack=agreement===within.length,atStart=current.time===0;
  $('#reading-mode').textContent=observer==='connected'?'The same moment, with connecting readings':'Four separate views';
  $('#reading-count').textContent=`${graph.edges.length} selected readings${observer==='connected'?' · 3 between groups':''}`;
  $('#moment-label').textContent=clockLabel(seconds);
  $('#clock-time').value=String(seconds);
  $('#clock-time').setAttribute('aria-valuetext',`${clockLabel(seconds)} in the film; model time ${(current.time/Math.PI).toFixed(3)} pi`);
  $('#reveal-connections').setAttribute('aria-pressed',String(observer==='connected'));
  $('#reveal-label').textContent=observer==='connected'?'Hide connecting readings':'Reveal connections';
  $('#reveal-connections').disabled=!returned;
  $('#measure-r').textContent=number(measure.discrepancy);
  $('#measure-d').textContent=measure.distance.toFixed(6);
  $('#measure-gap').textContent=measure.certificate.spectralGap===0?'0 · disconnected':number(measure.certificate.spectralGap);
  $('#measure-bound').textContent=!measure.certificate.available?'These four separate observation groups supply no global-distance bound.':measure.certificate.upperBound>=1?'Here the connected-graph bound is D ≤ 1. It gives no restriction beyond the normal distance range.':`The connected-graph bound at this moment is D ≤ ${number(measure.certificate.upperBound)}. It uses the known model assumptions stated below.`;
  if(returning){announceReading('Following the readings through one cycle. They will stop at their return.');$('#takeaway').textContent='Watch what a limited view can—and cannot—tell us.';}
  else if(atStart){announceReading('At the beginning, every selected reading agrees with its reference.');$('#takeaway').textContent='A part can look familiar before we know what has changed around it.';}
  else if(observer==='connected'){announceReading(`Time is held. ${changed} of the 3 added readings differ from the beginning. The state has not been changed.`);$('#takeaway').textContent=allBack?'The fragment returned. Its relations did not.':'A wider view reveals another part of the change.';}
  else if(allBack){announceReading('All 28 limited readings have returned within numerical tolerance. Time is held. Reveal what lies between the groups.');$('#takeaway').textContent='The familiar part is here. The wider view is still missing.';}
  else{announceReading('The limited readings are changing. Return this fragment to hold their first exact return.');$('#takeaway').textContent='A return depends on which relations can be seen.';}
  $('#clock-description').textContent=`A map of ${graph.edges.length} selected complex coherence readings. Both real and imaginary parts change the solid curves; faint curves mark the beginning. ${agreement} of 28 within-group readings agree with the beginning. ${observer==='connected'?`${changed} of three added bridge readings differ.`:'Connecting readings are hidden.'}`;
  const work=$('#clock-work');work.dataset.observer=observer;work.dataset.time=String(current.time);work.dataset.distance=String(measure.distance);work.dataset.discrepancy=String(measure.discrepancy);work.dataset.withinReturned=String(agreement);work.dataset.changedBridges=String(changed);work.dataset.stateRevision=String(stateRevision);work.dataset.returning=String(returning);
}

function setMoment(time){
  current=clock.state(time);stateRevision++;
  $('#clock-state-record').textContent=JSON.stringify(current);
  renderDrawing();
}

function stopReturn(){cancelAnimationFrame(returnFrame);returnFrame=0;returning=false;$('#return-fragment').removeAttribute('aria-busy');}
function returnFragment(){
  if(!ready)return;
  stopReturn();observer='disconnected';returned=false;
  if(reducedMotion.matches){returned=true;setMoment(TAU);return;}
  returning=true;$('#return-fragment').setAttribute('aria-busy','true');setMoment(0);
  const start=performance.now();let lastFrame=-Infinity;
  const advance=now=>{
    const progress=Math.min(1,(now-start)/2400);
    if(progress===1){stopReturn();returned=true;setMoment(TAU);}
    else{if(now-lastFrame>=1000/30){lastFrame=now;setMoment(TAU*progress);}returnFrame=requestAnimationFrame(advance);}
  };
  returnFrame=requestAnimationFrame(advance);
}

async function loadClock(){
  if(loading)return;loading=true;ready=false;$('#clock-work').dataset.ready='false';$('#clock-work').setAttribute('aria-busy','true');$('#clock-retry').hidden=true;
  for(const id of ['return-fragment','reveal-connections','clock-time','clock-reset'])$('#'+id).disabled=true;
  $('#clock-status').textContent='Opening the phase clock…';
  try{
    const [response,module]=await Promise.all([fetch('/assets/data/relational-clock.json'),import('/assets/relational-clock-core.js')]);
    if(!response.ok)throw Error('Clock data unavailable');
    const data=await response.json(),spec=data.models?.thirtyTwo;
    if(data.format!=='palimpsest-relational-clock-web'||data.version!==1||spec?.id!=='thirtyTwo'||spec.groups?.length!==32||!spec.groups.every((g,i)=>g===Math.floor(i/8)))throw Error('Unexpected clock record');
    const next=module.createRelationalClock(spec);
    if(next.parameters.size!==32||next.graphs.disconnected?.edges.length!==28||next.graphs.connected?.edges.length!==31)throw Error('Unexpected observer inventory');
    clock=next;initial=clock.state(0);observer='disconnected';returned=false;ready=true;
    setMoment(0);
    for(const id of ['return-fragment','clock-time','clock-reset'])$('#'+id).disabled=false;
    $('#clock-work').dataset.ready='true';
  }catch{
    ready=false;$('#clock-work').dataset.ready='false';$('#clock-status').textContent='The phase clock could not open. Try again; the film and scientific record remain available.';$('#clock-retry').hidden=false;
  }finally{loading=false;$('#clock-work').setAttribute('aria-busy','false');}
}
$('#return-fragment').addEventListener('click',returnFragment);
$('#reveal-connections').addEventListener('click',()=>{if(!ready||!returned)return;observer=observer==='disconnected'?'connected':'disconnected';renderDrawing();});
$('#clock-reset').addEventListener('click',()=>{if(!ready)return;stopReturn();observer='disconnected';returned=false;setMoment(0);});
$('#clock-time').addEventListener('input',event=>{if(!ready)return;stopReturn();returned=true;setMoment(Number(event.target.value)*TAU/FILM_PERIOD);});
$('#clock-retry').addEventListener('click',loadClock);
document.addEventListener('visibilitychange',()=>{if(document.hidden&&returning){stopReturn();renderDrawing();}});
reducedMotion.addEventListener('change',()=>{if(reducedMotion.matches&&returning){stopReturn();returned=true;setMoment(TAU);}});
loadClock();
