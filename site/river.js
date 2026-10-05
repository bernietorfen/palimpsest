const $=selector=>document.querySelector(selector);
const film=$('#river-film'),stage=$('.film-stage'),watch=$('#watch-film');
const excerpts=[...document.querySelectorAll('.listening-excerpt audio')];
const filmSources={full:film.dataset.src,compact:film.dataset.compactSrc};
let filmRequest=0,pausedAway=false,frameWatch=null,bufferTimer=null,pendingSwitch=null,lastPosition=0;

function stopBufferSuggestion(){clearTimeout(bufferTimer);bufferTimer=null;$('#film-compact').hidden=true;}
function suggestCompactAfterWait(){
  if(bufferTimer!==null||film.dataset.quality!=='full')return;
  bufferTimer=setTimeout(()=>{
    bufferTimer=null;
    if(film.dataset.quality==='full'&&!film.paused&&!document.hidden&&stage.dataset.videoState==='loading'){
      $('#film-compact').hidden=false;
      $('#film-status').textContent='Still buffering. Compact uses a smaller picture and keeps your place and the same soundtrack.';
    }
  },4000);
}

function filmState(value,message=''){
  if(value!=='loading')stopBufferSuggestion();
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
    if(!pendingSwitch&&!film.paused&&!film.ended&&!document.hidden&&stage.dataset.videoState==='loading'){
      pausedAway=false;filmState('playing');
    }
  });
}

async function resumeFilm(request){
  try{await film.play();if(request===filmRequest&&!pendingSwitch&&!film.paused&&!film.ended)filmState('playing');}
  catch(error){
    if(request!==filmRequest)return;
    if(error.name==='AbortError')return;
    if(film.error)filmState('error','The film could not open. Try again, or use the separate video link.');
    else filmState('paused','Use the video’s play control to begin.');
  }
}

function completeQualityChange(){
  const change=pendingSwitch;
  if(!change||change.request!==filmRequest||film.seeking||film.readyState<1||change.phase!=='seeking')return;
  pendingSwitch=null;lastPosition=film.currentTime;
  if(film.textTracks[0]&&change.captions)film.textTracks[0].mode=change.captions;
  if(change.resume&&!document.hidden&&!film.paused){suggestCompactAfterWait();watchPresentedFrame();}
  else filmState('paused',pausedAway?'Paused while this page was away. Use Play to continue.':'');
}

function loadFilmSource({time=0,resume=false}={}){
  stopFrameWatch();stopBufferSuggestion();
  pendingSwitch={request:++filmRequest,time,resume,captions:film.textTracks[0]?.mode,phase:'metadata'};
  filmState('loading',time>0?'Changing playback. Your place is kept.':'Opening the film. Sound begins when it is ready.');
  $('#film-fullscreen').disabled=true;
  film.src=film.dataset.src;film.load();
  // Keep the native play request in the user gesture. Metadata/seek events
  // restore the held position before presentation; they do not grant sound consent.
  if(resume&&!document.hidden)resumeFilm(pendingSwitch.request);
}

function selectFilmQuality(quality){
  if(!Object.hasOwn(filmSources,quality)||quality===film.dataset.quality)return;
  const time=pendingSwitch?.time??(film.error?lastPosition:film.currentTime);
  const resume=pendingSwitch?.resume??(!film.paused&&!film.ended);
  film.dataset.quality=quality;film.dataset.src=filmSources[quality];
  document.querySelectorAll('[data-film-quality]').forEach(node=>node.setAttribute('aria-pressed',String(node.dataset.filmQuality===quality)));
  $('#quality-note').textContent=quality==='full'?'1080p · More detail':'720p · Smaller download, same soundtrack';
  $('#film-separate').href=filmSources[quality];
  stopBufferSuggestion();
  // Choosing a quality before Watch does not request media or start sound.
  if(film.getAttribute('src'))loadFilmSource({time,resume});
}

function playFilm({retry=false}={}){
  film.controls=true;film.muted=false;pausedAway=false;
  if(retry||!film.getAttribute('src')){
    loadFilmSource({time:retry?(pendingSwitch?.time??lastPosition):0,resume:true});
  }else{
    filmState('loading','Opening the film. Sound begins when it is ready.');
    suggestCompactAfterWait();resumeFilm(++filmRequest);
  }
}
watch.addEventListener('click',()=>playFilm({retry:stage.dataset.videoState==='error'}));
$('#film-retry').addEventListener('click',()=>playFilm({retry:true}));
document.querySelectorAll('[data-film-quality]').forEach(node=>node.addEventListener('click',()=>selectFilmQuality(node.dataset.filmQuality)));
$('#film-compact').addEventListener('click',()=>selectFilmQuality('compact'));
film.addEventListener('loadedmetadata',()=>{
  $('#film-fullscreen').disabled=false;
  const change=pendingSwitch;
  if(!change||change.request!==filmRequest||film.readyState<1)return;
  change.phase='seeking';
  const time=Math.max(0,Math.min(change.time,Number.isFinite(film.duration)?film.duration:change.time));
  if(Math.abs(film.currentTime-time)>.001)film.currentTime=time;
  else completeQualityChange();
});
film.addEventListener('seeked',completeQualityChange);
film.addEventListener('timeupdate',()=>{if(!pendingSwitch&&!film.error)lastPosition=film.currentTime;});
film.addEventListener('play',()=>{excerpts.forEach(audio=>audio.pause());watchPresentedFrame();suggestCompactAfterWait();});
film.addEventListener('playing',()=>{if(pendingSwitch||film.paused||film.ended)return;stopFrameWatch();pausedAway=false;filmState('playing');});
film.addEventListener('waiting',()=>{if(!pendingSwitch&&!film.paused){filmState('loading','The film is buffering. Your place is kept.');suggestCompactAfterWait();watchPresentedFrame();}});
film.addEventListener('pause',()=>{stopFrameWatch();stopBufferSuggestion();if(!pendingSwitch&&!film.ended&&stage.dataset.videoState!=='error')filmState('paused',pausedAway?'Paused while this page was away. Use Play to continue.':'');});
film.addEventListener('ended',()=>{stopFrameWatch();filmState('ended','The film has ended. Try changing the view below.');});
film.addEventListener('error',()=>{stopFrameWatch();if(pendingSwitch)lastPosition=pendingSwitch.time;pendingSwitch=null;$('#film-fullscreen').disabled=true;filmState('error','The film could not open. Try again, choose another quality, or use the separate video link.');});
$('#film-fullscreen').addEventListener('click',async()=>{
  try{
    if(film.requestFullscreen)await film.requestFullscreen();
    else if(film.webkitEnterFullscreen)film.webkitEnterFullscreen();
    else $('#film-status').textContent='Use the video’s full-screen control, or open the separate film.';
  }catch{$('#film-status').textContent='Full screen is unavailable here. The film can still play in this page.';}
});
function pauseAllMedia(){
  filmRequest++;pausedAway=true;stopFrameWatch();stopBufferSuggestion();
  if(pendingSwitch){pendingSwitch.request=filmRequest;pendingSwitch.resume=false;}
  film.pause();excerpts.forEach(audio=>audio.pause());
  if(film.src&&!film.ended&&stage.dataset.videoState!=='error')filmState('paused','Paused while this page was away. Use Play to continue.');
}
document.addEventListener('visibilitychange',()=>{if(document.hidden)pauseAllMedia();});
window.addEventListener('pagehide',pauseAllMedia);

for(const audio of excerpts){
  const figure=audio.closest('.listening-excerpt'),status=figure.querySelector('[role=status]'),retry=figure.querySelector('.excerpt-retry');
  audio.addEventListener('play',()=>{
    if(pendingSwitch)pendingSwitch.resume=false;
    film.pause();excerpts.filter(other=>other!==audio).forEach(other=>other.pause());
    status.textContent='';retry.hidden=true;
  });
  audio.addEventListener('playing',()=>{figure.dataset.audioState='playing';});
  audio.addEventListener('pause',()=>{if(!audio.error)figure.dataset.audioState=audio.ended?'ended':'paused';});
  audio.addEventListener('ended',()=>{figure.dataset.audioState='ended';});
  audio.addEventListener('error',()=>{figure.dataset.audioState='error';status.textContent='The excerpt could not open. Try again or use the download link.';retry.hidden=false;});
  retry.addEventListener('click',async()=>{
    status.textContent='Opening the excerpt…';retry.hidden=true;audio.load();
    try{await audio.play();status.textContent='';}
    catch{status.textContent='The excerpt could not open. Try again or use the download link.';retry.hidden=false;}
  });
}

const NS='http://www.w3.org/2000/svg',TAU=2*Math.PI,FILM_PERIOD=104;
const exactMoments=[0,104,208],imageCache=new Map();
let clock=null,current=null,initial=null,observer='disconnected',ready=false,loading=false,stateRevision=0,selectedMoment=0,viewRequest=0;
const withinColors=['#805536','#465e60','#80745d','#4e7776'];
const edgeKey=edge=>edge.join(':');
function svg(tag,attributes={}){const node=document.createElementNS(NS,tag);for(const [key,value]of Object.entries(attributes))node.setAttribute(key,String(value));return node;}
function clockLabel(seconds){return `${Math.floor(seconds/60).toString().padStart(2,'0')}:${Math.floor(seconds%60).toString().padStart(2,'0')}`;}
function number(value){return value<1e-24?'below 10⁻²⁴':value<.001?value.toExponential(3):value.toFixed(6);}
function announceReading(message){const node=$('#clock-status');if(node.textContent!==message)node.textContent=message;}
function pathData(points){return points.map((point,index)=>`${index?'L':'M'}${point[0].toFixed(4)},${point[1].toFixed(4)}`).join(' ');}
function normReading(state,edge){const value=clock.coherence(state,...edge),scale=Math.sqrt(clock.parameters.populations[edge[0]]*clock.parameters.populations[edge[1]]);return{real:value.real/scale,imaginary:value.imaginary/scale};}

function controlledSource(view,seconds){return `/assets/generated/river-${view}-${String(seconds).padStart(3,'0')}.jpg`;}
function decodedImage(source){
  if(imageCache.has(source))return imageCache.get(source);
  const image=new Image();image.decoding='async';image.src=source;
  let timeout;
  const promise=Promise.race([
    image.decode().then(()=>image),
    new Promise((_,reject)=>{timeout=setTimeout(()=>reject(Error('View timed out')),15000);})
  ]).finally(()=>clearTimeout(timeout)).catch(error=>{imageCache.delete(source);throw error;});
  imageCache.set(source,promise);
  return promise;
}

async function renderControlledViews(){
  const request=++viewRequest,view=observer==='connected'?'wide':'local',seconds=selectedMoment;
  const pair=$('#controlled-views'),beginning=$('#beginning-view'),held=$('#held-view');
  const sources=[controlledSource(view,0),controlledSource(view,seconds)];
  pair.dataset.viewState='loading';pair.setAttribute('aria-busy','true');
  // Old images are concealed until both exact requested images have decoded.
  // A late response from an earlier choice must never relabel the current pair.
  $('#view-retry').hidden=true;
  $('#view-status').textContent='Opening the matched views…';
  pair.querySelectorAll('.image-placeholder').forEach(node=>{node.textContent='Opening the view…';});
  try{
    await Promise.all(sources.map(decodedImage));
    if(request!==viewRequest)return;
    beginning.src=sources[0];held.src=sources[1];
    beginning.alt=view==='local'?'The copper stitch and pale reference folds at the beginning.':'The whole woven artwork at the beginning, with its narrow, folded opening.';
    held.alt=view==='local'?`The reference stitch at ${clockLabel(seconds)}, matching its shape at the beginning.`:seconds===0?'The whole woven artwork at the beginning, with its narrow, folded opening.':seconds===104?'The whole woven artwork at 01:44: the opening broadens and the surrounding bands cross differently.':'The whole woven artwork at 03:28: the surrounding bands form another arrangement around the returning reference.';
    await Promise.all([beginning.decode(),held.decode()]);
    if(request!==viewRequest)return;
    pair.dataset.viewState='ready';pair.dataset.view=view;pair.dataset.moment=String(seconds);
    pair.setAttribute('aria-busy','false');$('#view-status').textContent='';
  }catch{
    if(request!==viewRequest)return;
    pair.dataset.viewState='error';pair.setAttribute('aria-busy','false');
    pair.querySelectorAll('.image-placeholder').forEach(node=>{node.textContent='View unavailable';});
    $('#view-status').textContent='The matched images could not open. The calculated readings below are still available.';
    $('#view-retry').hidden=false;
  }
}

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
  $('#reading-mode').textContent=observer==='connected'?'The same moment, with connecting readings':'Four separate observation groups';
  $('#reading-count').textContent=`${graph.edges.length} selected readings${observer==='connected'?' · 3 between groups':''}`;
  $('#moment-label').textContent=clockLabel(seconds);
  $('#held-label').textContent=atStart?'Selected moment':selectedMoment===104?'First return':'Second return';
  $('#view-label').textContent=observer==='connected'?'The wider arrangement':'The reference fragment';
  document.querySelectorAll('button[data-moment]').forEach(node=>node.setAttribute('aria-pressed',String(Number(node.dataset.moment)===selectedMoment)));
  $('#reveal-connections').setAttribute('aria-pressed',String(observer==='connected'));
  $('#reveal-label').textContent=observer==='connected'?'Show the fragment again':'Open its surroundings';
  $('#reveal-connections').disabled=atStart;
  $('#measure-r').textContent=number(measure.discrepancy);
  $('#measure-d').textContent=measure.distance.toFixed(6);
  $('#measure-gap').textContent=measure.certificate.spectralGap===0?'0 · disconnected':number(measure.certificate.spectralGap);
  $('#measure-bound').textContent=!measure.certificate.available?'These four separate observation groups supply no global-distance bound.':measure.certificate.upperBound>=1?'Here the connected-graph bound is D ≤ 1. It gives no restriction beyond the normal distance range.':`The connected-graph bound at this moment is D ≤ ${number(measure.certificate.upperBound)}. It uses the known model assumptions stated below.`;
  if(atStart){
    announceReading('Both views begin at 00:00. Return the fragment to compare it with the beginning.');
    $('#takeaway').textContent='A part can look familiar before we know what has changed around it.';
    $('#comparison-finding').textContent='Begin with the fragment. Its wider setting comes next.';
  }else if(observer==='connected'){
    announceReading(`Time stays held at ${clockLabel(seconds)}. The wider view and connecting readings are now visible. The clock has not changed.`);
    $('#takeaway').textContent='The reference returns. The wider arrangement does not.';
    $('#comparison-finding').textContent=`${agreement} readings match the beginning. ${changed===3?'Three':changed} added readings differ.`;
  }else if(allBack){
    announceReading(`Held at ${clockLabel(seconds)}. The reference fragment has returned. Reveal its surroundings without advancing time.`);
    $('#takeaway').textContent='The familiar fragment is here. Its wider setting is still hidden.';
    $('#comparison-finding').textContent='All 28 readings inside the four groups match the beginning within numerical tolerance.';
  }
  $('#clock-description').textContent=`A map of ${graph.edges.length} selected complex coherence readings. Both real and imaginary parts change the solid curves; faint curves mark the beginning. ${agreement} of 28 within-group readings agree with the beginning. ${observer==='connected'?`${changed} of three added bridge readings differ.`:'Connecting readings are hidden.'}`;
  const work=$('#clock-work');work.dataset.observer=observer;work.dataset.time=String(current.time);work.dataset.distance=String(measure.distance);work.dataset.discrepancy=String(measure.discrepancy);work.dataset.withinReturned=String(agreement);work.dataset.changedBridges=String(changed);work.dataset.stateRevision=String(stateRevision);work.dataset.moment=String(selectedMoment);
}

function setMoment(seconds){
  if(!exactMoments.includes(seconds))return;
  selectedMoment=seconds;current=clock.state(seconds/FILM_PERIOD*TAU);stateRevision++;
  $('#clock-state-record').textContent=JSON.stringify(current);
  renderDrawing();renderControlledViews();
}

function returnFragment(){
  if(!ready)return;
  observer='disconnected';setMoment(104);
}

async function loadClock(){
  if(loading)return;loading=true;ready=false;$('#clock-work').dataset.ready='false';$('#clock-work').setAttribute('aria-busy','true');$('#clock-retry').hidden=true;
  for(const node of document.querySelectorAll('#return-fragment,#reveal-connections,#clock-reset,button[data-moment]'))node.disabled=true;
  $('#clock-status').textContent='Opening the phase clock…';
  try{
    const [response,module]=await Promise.all([fetch('/assets/data/relational-clock.json'),import('/assets/relational-clock-core.js')]);
    if(!response.ok)throw Error('Clock data unavailable');
    const data=await response.json(),spec=data.models?.thirtyTwo;
    if(data.format!=='palimpsest-relational-clock-web'||data.version!==1||spec?.id!=='thirtyTwo'||spec.groups?.length!==32||!spec.groups.every((g,i)=>g===Math.floor(i/8)))throw Error('Unexpected clock record');
    const next=module.createRelationalClock(spec);
    if(next.parameters.size!==32||next.graphs.disconnected?.edges.length!==28||next.graphs.connected?.edges.length!==31)throw Error('Unexpected observer inventory');
    clock=next;initial=clock.state(0);observer='disconnected';ready=true;
    setMoment(0);
    for(const node of document.querySelectorAll('#return-fragment,#clock-reset,button[data-moment]'))node.disabled=false;
    $('#clock-work').dataset.ready='true';
  }catch{
    ready=false;$('#clock-work').dataset.ready='false';$('#clock-status').textContent='The phase clock could not open. Try again; the film and scientific record remain available.';$('#clock-retry').hidden=false;
    viewRequest++;$('#controlled-views').dataset.viewState='error';$('#controlled-views').setAttribute('aria-busy','false');
    document.querySelectorAll('.image-placeholder').forEach(node=>{node.textContent='Open the clock to compare its views';});
  }finally{loading=false;$('#clock-work').setAttribute('aria-busy','false');}
}
$('#return-fragment').addEventListener('click',returnFragment);
$('#reveal-connections').addEventListener('click',()=>{if(!ready||selectedMoment===0)return;observer=observer==='disconnected'?'connected':'disconnected';renderDrawing();renderControlledViews();});
$('#clock-reset').addEventListener('click',()=>{if(!ready)return;observer='disconnected';setMoment(0);});
document.querySelectorAll('button[data-moment]').forEach(node=>node.addEventListener('click',()=>{if(!ready)return;const seconds=Number(node.dataset.moment);if(seconds===0)observer='disconnected';setMoment(seconds);}));
$('#clock-retry').addEventListener('click',loadClock);
$('#view-retry').addEventListener('click',()=>{if(ready)renderControlledViews();});
loadClock();
