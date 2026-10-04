import {ChoirRenderer} from './choir-renderer.js';
const $=s=>document.querySelector(s),RECOVERY='palimpsest-choir-recovery-v1';
let scene,renderer,worker,ready=false,started=false,running=false,starting=false,failed=false,graphicsLost=false,selected=1,solo=false,inward=false,connected=true,soundEnabled=false,latest=null;
let snapshotRequest=0,lastRecovery=0,pendingRecovery=0,saving=new Set(),recovering=false,demo=false,spaceHeld=false;
let audio=null,voiceNode=null,gain=null,analyser=null,roomNodes=[],peak=0,pans=Array(7).fill(0);
const labels=[],voiceButtons=[];
const timeLabel=t=>`${String(Math.floor(t/60)).padStart(2,'0')}:${String(Math.floor(t%60)).padStart(2,'0')}`;
const say=text=>{$('#status').textContent=text;};
const send=(data,transfer=[])=>worker?.postMessage(data,transfer);
function controls(){
  for(const id of ['pause','demonstration','connections','isolate','settle','save','new','solo'])$('#'+id).disabled=!started||starting||failed||graphicsLost;
  $('#new').disabled=!ready||starting||graphicsLost;
  $('#sound').disabled=!started||starting;$('#pause').textContent=running?'Pause':'Resume';$('#sound').textContent=soundEnabled?'Sound on':'Sound off';$('#sound').setAttribute('aria-pressed',String(soundEnabled));
  $('#connections').textContent=connected?'Cut the connections':'Rejoin the circle';$('#isolate').textContent='Separate voice '+scene?.bodies[selected]?.name;$('#solo').textContent='Listen to '+scene?.bodies[selected]?.name+' alone';$('#solo').setAttribute('aria-pressed',String(solo));
  $('#demonstration').textContent=demo?'Leave the demonstration':'A 72-second encounter ↗';
  $('#enter-sound').disabled=!ready||starting||recovering;$('#enter-silent').disabled=!ready||starting||recovering;
  voiceButtons.forEach((b,i)=>{b.disabled=!started||failed;b.setAttribute('aria-pressed',String(i===selected));});
  document.body.dataset.running=String(running);document.body.dataset.sound=String(soundEnabled);document.body.dataset.ready=String(ready);
}
async function prepareAudio(){
  if(!audio){
    audio=new AudioContext({latencyHint:'interactive'});
    try{
      await audio.audioWorklet.addModule('/choir-audio-worklet.js');voiceNode=new AudioWorkletNode(audio,'palimpsest-choir',{outputChannelCount:[2]});gain=audio.createGain();gain.gain.value=Number($('#volume').value)/100;analyser=audio.createAnalyser();analyser.fftSize=1024;voiceNode.connect(gain);gain.connect(analyser);analyser.connect(audio.destination);
      const split=audio.createChannelSplitter(2),merge=audio.createChannelMerger(2);voiceNode.connect(split);
      for(let i=0;i<2;i++){const delay=audio.createDelay(.3),filter=audio.createBiquadFilter(),feedback=audio.createGain(),wet=audio.createGain();delay.delayTime.value=i?.137:.089;filter.type='lowpass';filter.frequency.value=1800;feedback.gain.value=.34;wet.gain.value=.17;split.connect(delay,i);delay.connect(filter);filter.connect(feedback);feedback.connect(delay);filter.connect(wet);wet.connect(merge,0,1-i);roomNodes.push(delay,filter,feedback,wet);}merge.connect(gain);roomNodes.push(split,merge);
      voiceNode.port.onmessage=({data})=>{if(data.type==='meter'){peak=data.peak;document.body.dataset.audioPeak=peak.toFixed(6);}};
      voiceNode.onprocessorerror=()=>{soundEnabled=false;say('Sound was interrupted. Your choir is still here; continue silently.');controls();};
    }catch(error){await audio.close();audio=null;throw error;}
  }
  await audio.resume();
}
function audioControl(){if(voiceNode&&soundEnabled&&running&&latest)voiceNode.port.postMessage({type:'control',readout:latest.readout,solo:solo?selected:-1,pans});}
async function start(withSound){
  if(!ready||starting||failed||graphicsLost)return;
  starting=true;controls();
  try{if(withSound){await prepareAudio();soundEnabled=true;}started=true;$('#choir-entry').hidden=true;
    if(!document.hidden){running=true;send({type:'run'});say('Touch and hold a vessel. Its neighbours can receive the gesture.');}else pause();
  }catch(error){say(`${error.message}. You can enter silently.`);}finally{starting=false;controls();}
}
function requestRecovery(force=false){if(!started||failed||recovering||pendingRecovery||!worker||(!force&&performance.now()-lastRecovery<5000))return;pendingRecovery=++snapshotRequest;lastRecovery=performance.now();send({type:'snapshot',request:pendingRecovery});}
function pause(message='Paused. The choir keeps its history.'){
  if(!started)return;running=false;spaceHeld=false;send({type:'pause'});voiceNode?.port.postMessage({type:'quiet'});audio?.suspend().catch(()=>{});say(message);controls();requestRecovery(true);
}
function touch(hit,event){
  if(!running)return;selected=hit.body;demo=false;controls();const pen=event?.pointerType==='pen'&&event.pressure>0?event.pressure:1;
  send({type:'contact',...hit,strength:Number($('#pressure').value)/100*(inward?-1:1)*pen});
}
function release(){send({type:'release'});spaceHeld=false;}
function select(index){selected=index;renderer.selected=index;renderer.requestDraw();send({type:'select',body:index});controls();audioControl();}
function download(data,name,type){const url=URL.createObjectURL(new Blob([data],{type})),link=document.createElement('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}
function updateLabels(matrix){
  if(!scene)return;
  scene.bodies.forEach((body,i)=>{const p=[...body.position];p[1]+=1.35*body.scale;const x=matrix[0]*p[0]+matrix[4]*p[1]+matrix[8]*p[2]+matrix[12],y=matrix[1]*p[0]+matrix[5]*p[1]+matrix[9]*p[2]+matrix[13],w=matrix[3]*p[0]+matrix[7]*p[1]+matrix[11]*p[2]+matrix[15];const sx=x/w,sy=y/w;labels[i].style.left=`${(sx*.5+.5)*100}%`;labels[i].style.top=`${(.5-sy*.5)*100}%`;labels[i].hidden=w<=0||Math.abs(sx)>1||Math.abs(sy)>1;labels[i].dataset.selected=String(i===selected);pans[i]=Math.max(-.85,Math.min(.85,sx*.9));});
}
function frame(data){
  const newGeneration=latest&&latest.generation!==data.generation;
  document.body.dataset.materialRunning=String(data.running);
  latest={...data,fields:null};running=data.running;demo=data.demo;selected=data.selected;connected=data.gates.some(g=>g>.005);renderer.update(data);
  send({type:'recycle',fields:data.fields},[data.fields.buffer]);
  $('#choir-clock').textContent=timeLabel(data.diagnostics.time);$('#choir-clock').dataset.time=data.diagnostics.time.toFixed(6);$('#scene-caption').textContent=data.phase;
  data.diagnostics.bodies.forEach((body,i)=>{const button=voiceButtons[i];button.dataset.memory=body.memory_rms.toFixed(8);button.querySelector('small').textContent=body.memory_rms<.0001?'unwritten':'inscribed';const bars=button.querySelectorAll('rect');data.readout[i].amplitude.forEach((a,m)=>{const height=Math.max(.4,Math.min(21,Math.sqrt(Math.max(0,a))*23));bars[m].setAttribute('y',String(22-height));bars[m].setAttribute('height',String(height));});});
  audioControl();controls();requestRecovery(Boolean(newGeneration));
}
function onMessage({data}){
  if(data.type==='frame'){
    // Keep only the renderer's fixed-size field copies; recycle the worker packet.
    frame(data);
  }else if(data.type==='snapshot'){
    if(saving.delete(data.request)){download(JSON.stringify(data.state),'palimpsest-encounter.json','application/json');say('Encounter saved: bodies, connections, motion and history.');}
    if(data.request===pendingRecovery){pendingRecovery=0;try{sessionStorage.setItem(RECOVERY,JSON.stringify(data.state));$('#recovery').textContent=`A recovery copy at ${timeLabel(data.state.bodies[0].steps*data.state.bodies[0].config.dt)} stays in this tab. Save a file to keep it.`;$('#recovery').dataset.saved='true';}catch{$('#recovery').textContent='This tab could not keep a recovery copy. Save a file to keep the encounter.';$('#recovery').dataset.saved='false';}}
  }else if(data.type==='restored'){recovering=false;started=true;running=false;failed=false;$('#choir-entry').hidden=true;say(data.source==='recovery'?'Recovered the recent encounter. Resume when you are ready.':'Encounter opened. Resume when you are ready.');controls();requestRecovery(true);}
  else if(data.type==='undo'){$('#undo').hidden=!data.available;}
  else if(data.type==='demo-ended'){demo=false;say('The connections have gone. Touch a voice and hear what it has kept.');controls();}
  else if(data.type==='error'||data.type==='fault'){if(data.type==='fault'){failed=true;pause();}recovering=false;if(data.request===pendingRecovery)pendingRecovery=0;saving.delete(data.request);say(data.message);controls();}
}
async function initialize(){
  const responses=await Promise.all(['/choir-scene.json','/shaders/choir.vert','/shaders/choir.frag'].map(path=>fetch(path).then(r=>{if(!r.ok)throw new Error('A part of the choir could not be loaded');return r.text();})));
  scene=JSON.parse(responses[0]);
  scene.bodies.forEach((body,i)=>{
    const label=document.createElement('span');label.className='body-label';label.textContent=body.name;$('#body-labels').append(label);labels.push(label);
    const button=document.createElement('button');button.className='choir-voice';button.dataset.body=i;button.setAttribute('aria-label',`Select voice ${body.name}, keyboard ${i+1}`);button.innerHTML=`<span>${body.name}</span><svg viewBox="0 0 58 24" aria-hidden="true"><g class="voice-bars">${Array.from({length:12},(_,m)=>`<rect x="${m*4+6}" y="21.5" width="2" height=".5"/>`).join('')}</g></svg><small>unwritten</small>`;button.addEventListener('click',()=>select(i));$('#voice-buttons').append(button);voiceButtons.push(button);
  });
  renderer=new ChoirRenderer($('#choir-canvas'),scene,responses.slice(1),{touch,release,draw:updateLabels,lost:()=>{graphicsLost=true;pause('The drawing was interrupted. The choir is kept while the graphics recover.');},restored:()=>{graphicsLost=false;say('The drawing is back. Resume the encounter when ready.');controls();},error:error=>say(error.message)});
  worker=new Worker('/choir-worker.js',{type:'module'});worker.onmessage=onMessage;worker.onerror=()=>{failed=true;pause('The choir was interrupted. Reload to recover the most recent copy.');};send({type:'init',scene});ready=true;$('#preparing').hidden=true;
  try{const saved=sessionStorage.getItem(RECOVERY);if(saved&&saved.length<4_000_000){const state=JSON.parse(saved);recovering=true;send({type:'restore',state,source:'recovery'});}}catch{say('The recent recovery copy could not be opened. You can begin a new choir.');}
  controls();
}
$('#enter-sound').addEventListener('click',()=>start(true));$('#enter-silent').addEventListener('click',()=>start(false));
$('#pause').addEventListener('click',()=>running?pause():start(soundEnabled));
$('#sound').addEventListener('click',async()=>{if(soundEnabled){soundEnabled=false;voiceNode?.port.postMessage({type:'quiet'});await audio?.suspend();}else{try{await prepareAudio();soundEnabled=true;audioControl();}catch(error){say(error.message);}}controls();});
$('#volume').addEventListener('input',()=>{if(gain)gain.gain.setTargetAtTime(Number($('#volume').value)/100,audio.currentTime,.04);});
$('#view-home').addEventListener('click',()=>renderer?.reset());
for(const mode of ['touch','turn'])$('#mode-'+mode).addEventListener('click',()=>{renderer.mode=mode;release();$('#mode-touch').setAttribute('aria-pressed',String(mode==='touch'));$('#mode-turn').setAttribute('aria-pressed',String(mode==='turn'));$('#touch-hint').textContent=mode==='touch'?'Touch a vessel · Drag the space to turn':'Drag to turn · Scroll or pinch to approach';});
$('#polarity').addEventListener('click',()=>{inward=!inward;$('#polarity').setAttribute('aria-pressed',String(inward));$('#polarity').textContent=inward?'Press outward':'Press inward';});
$('#connections').addEventListener('click',()=>send({type:'connections',connected:!connected}));$('#isolate').addEventListener('click',()=>send({type:'isolate',body:selected}));
$('#solo').addEventListener('click',()=>{solo=!solo;controls();audioControl();});$('#settle').addEventListener('click',()=>send({type:'settle'}));
$('#demonstration').addEventListener('click',async()=>{
  if(demo){send({type:'leave-demo'});say('The choir is yours to play.');return;}
  if(!ready||starting||failed||graphicsLost)return;
  starting=true;controls();
  try{
    if(soundEnabled)await prepareAudio();
    if(document.hidden)return;
    started=true;running=true;$('#choir-entry').hidden=true;
    // The worker captures the previous encounter before it starts the new one.
    send({type:'demo'});say('One voice enters; the circle carries its gestures.');
  }catch(error){say(error.message);}finally{starting=false;controls();}
});
$('#new').addEventListener('click',()=>{pause();send({type:'fresh'});say('A new, unwritten choir. Your previous encounter can be restored below.');});$('#undo').addEventListener('click',()=>{pause();send({type:'undo'});});
$('#save').addEventListener('click',()=>{const request=++snapshotRequest;saving.add(request);send({type:'snapshot',request});});
$('#open').addEventListener('change',async event=>{const file=event.target.files?.[0];if(!file)return;try{if(file.size>4_000_000)throw new Error('This file is too large to be a saved choir');const state=JSON.parse(await file.text());send({type:'restore',state,source:'file'});}catch(error){say(error.message);}event.target.value='';});
window.addEventListener('keydown',event=>{if(event.ctrlKey||event.metaKey||event.altKey||['INPUT','SELECT','TEXTAREA'].includes(event.target.tagName))return;if(/^[1-7]$/.test(event.key)){event.preventDefault();if(ready)select(Number(event.key)-1);}else if(event.code==='Space'&&running&&!event.repeat&&(event.target===document.body||event.target===$('#choir-canvas')||event.target.closest('.choir-voice'))){event.preventDefault();spaceHeld=true;touch({body:selected,x:.22,y:.5});}});
window.addEventListener('keyup',event=>{if(event.code==='Space'&&spaceHeld){event.preventDefault();release();}});
window.addEventListener('blur',()=>{if(spaceHeld)release();});document.addEventListener('visibilitychange',()=>{if(document.hidden)pause('Paused while you were away. Resume to continue the encounter.');});window.addEventListener('pagehide',()=>pause());
initialize().catch(error=>{$('#preparing').textContent=error.message;say(error.message);});
