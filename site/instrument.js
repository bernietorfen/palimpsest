import {PITCHES} from './live-material.js';
import {LiveRenderer} from './live-renderer.js';
import {LiveSound} from './live-sound.js';
import {drawReplyPair,replyPlate} from './live-glyph.js';

const $=selector=>document.querySelector(selector),letters='QWERTYUIOPAS'.split('');
const keys=$('#voice-keys'),status=$('#live-status'),canvas=$('#live-sculpture');
const voiceButtons=letters.map((letter,index)=>{
  const button=document.createElement('button');button.className='voice-key';button.dataset.voice=index;
  button.setAttribute('aria-pressed','false');button.setAttribute('aria-label',`Voice ${index+1}, key ${letter}`);button.disabled=true;
  const number=document.createElement('span');number.className='voice-index';number.textContent=String(index+1).padStart(2,'0');
  const name=document.createElement('span');name.className='voice-letter';name.textContent=letter;
  const pitch=document.createElement('span');pitch.className='voice-pitch';pitch.textContent=PITCHES[index].toFixed(1);
  const level=document.createElement('span');level.className='voice-level';level.setAttribute('aria-hidden','true');
  button.append(number,name,pitch,level);keys.append(button);return button;
});
const sound=new LiveSound();
let renderer,worker,started=false,running=false,soundEnabled=false,starting=false,fading=false;
let lastFrame=null,lastLabels=-Infinity,lastMaps=-Infinity,snapshotRequest=0,pendingSave=0;
let score={mode:'idle',hasPhrase:false,duration:0,time:0},lastScoreMode='idle';
let exporting=false,lastComparison=null;
const held=new Map(),pulses=new Map();
const contexts=['inscription-map','wear-map'].map(id=>$(`#${id}`).getContext('2d'));
const mapImages=contexts.map(context=>context.createImageData(64,64));
const say=message=>{status.textContent=message;};
const timeLabel=t=>`${String(Math.floor(t/60)).padStart(2,'0')}:${String(Math.floor(t%60)).padStart(2,'0')}`;

function controls(){
  $('#pause-material').disabled=!started||starting;$('#pause-material').textContent=running?'Pause':'Resume';
  $('#sound-toggle').disabled=!started||starting;$('#sound-toggle').textContent=soundEnabled?'Sound on':'Sound off';
  $('#sound-toggle').setAttribute('aria-pressed',String(soundEnabled));
  $('#fade-material').disabled=!running;$('#fade-material').setAttribute('aria-pressed',String(fading));
  $('#fade-material').textContent=fading?'Keep what remains':'Let the inscription fade';
  const locked=score.mode==='replaying'||score.mode==='releasing';
  $('#save-material').disabled=!started||score.mode!=='idle';$('#fresh-material').disabled=!started||score.mode!=='idle';
  $('#export-sculpture').disabled=!started||score.mode!=='idle'||exporting;
  $('#export-sculpture').textContent=exporting?'Making sculpture…':'Save sculpture ↓';
  for(const button of voiceButtons)button.disabled=!running||locked;
  $('#record-phrase').disabled=!running||locked;
  $('#record-phrase').textContent=score.mode==='recording'?'Finish phrase ◼':'Record a phrase ●';
  $('#record-phrase').dataset.active=String(score.mode==='recording');
  $('#replay-phrase').disabled=!running||!score.hasPhrase||score.mode==='recording';
  $('#replay-phrase').textContent=locked?'Stop phrase ◼':'Ask again ↻';
  $('#replay-phrase').dataset.active=String(locked);
  $('#begin-sound').disabled=starting;$('#begin-silent').disabled=starting;
  document.body.dataset.running=String(running);document.body.dataset.sound=String(soundEnabled);
  document.body.dataset.phrase=score.mode;
}
function sendDrive(){
  const values=Array(12).fill(0),pressure=Number($('#pressure').value)/100;
  if(running)for(const index of held.values())values[index]=pressure;
  for(let i=0;i<12;i++)voiceButtons[i].setAttribute('aria-pressed',String(values[i]>0));
  worker?.postMessage({type:'drive',values});
}
function clearHeld(){
  for(const id of held.keys())if(id.startsWith('pointer-')){
    const pointer=Number(id.slice(8));if(keys.hasPointerCapture(pointer))keys.releasePointerCapture(pointer);
  }
  held.clear();for(const timer of pulses.values())clearTimeout(timer);pulses.clear();sendDrive();
}
async function start(withSound=soundEnabled){
  if(starting||!worker)return;
  starting=true;controls();
  try{
    if(withSound){await sound.start();soundEnabled=true;}
    started=true;$('#begin-panel').hidden=true;
    if(document.hidden)pause('Paused while you were away. Resume to continue.');
    else{
      running=true;worker.postMessage({type:'run'});say('Hold a voice and watch the material remember.');
      if(matchMedia('(max-width: 640px)').matches)$('#playing').scrollIntoView({block:'start',behavior:'instant'});
    }
  }catch(error){say(`${error.message}. You can begin silently.`);}
  finally{starting=false;controls();}
}
function pause(message='Paused. The material keeps its history.'){
  if(!started)return;
  running=false;fading=false;score={...score,mode:'idle',time:0};clearHeld();worker?.postMessage({type:'pause'});sound.suspend().catch(()=>{});controls();say(message);
}
function updateScore(value,comparison=null){
  score=value;
  if(score.mode!==lastScoreMode){
    const messages={recording:'Recording your gestures. Finish when the phrase is complete.',releasing:'Keeping the final two seconds of the response…',replaying:'The same timing and pressure, written into the present material.',idle:score.hasPhrase?'Phrase kept. Ask it again, or write a new one.':'Recording keeps the timing and pressure of your gestures. A repeat starts from the material you have now.'};
    $('#phrase-status').textContent=messages[score.mode];lastScoreMode=score.mode;controls();
    if(score.mode==='recording'){$('#reply-comparison').hidden=true;say('Recording your phrase. Hold the voices to write.');}
    if(score.mode==='replaying')say('Your phrase is returning to the changed material.');
  }
  $('#phrase-clock').textContent=score.mode==='idle'?(score.hasPhrase?`${score.duration.toFixed(1)} seconds kept`:'Up to 24 seconds'):`${score.time.toFixed(1)} / ${score.mode==='recording'?'24':score.duration.toFixed(1)} s`;
  if(comparison){
    lastComparison=comparison;
    drawReplyPair($('#earlier-reply'),$('#current-reply'),comparison);
    $('#reply-title').replaceChildren(document.createTextNode('The same gestures.'),document.createElement('br'),document.createTextNode(comparison.rms_hz<1e-8?'The same reply.':'Another answer.'));
    $('#reply-measure').textContent=`The recorded voice tunings differ by ${comparison.rms_hz.toFixed(3)} Hz RMS across the phrase.`;
    $('#reply-comparison').dataset.rmsHz=comparison.rms_hz;$('#reply-comparison').hidden=false;
    say('Your two replies are ready below the voices.');
  }
}
function saveBlob(blob,filename){
  const url=URL.createObjectURL(blob);
  const link=document.createElement('a');link.href=url;link.download=filename;
  document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function download(state){
  const savedDocument={...state,edition:'PALIMPSEST live',saved_utc:new Date().toISOString()};
  saveBlob(new Blob([JSON.stringify(savedDocument)],{type:'application/json'}),`palimpsest-material-${Math.round(state.steps*state.config.dt)}s.json`);
  say('Material saved. Open this file to continue from the same state.');
}
function maps(fields){
  for(let k=0;k<64*64;k++){
    const p=fields[k*4+1],z=fields[k*4+2],ink=Math.min(1,Math.abs(p)/.42);
    const color=p<0?[40,76,79]:[122,76,30],paper=[225,217,193];
    for(let channel=0;channel<3;channel++){
      mapImages[0].data[k*4+channel]=paper[channel]*(1-ink)+color[channel]*ink;
      mapImages[1].data[k*4+channel]=paper[channel]*(1-z)+[27,47,51][channel]*z;
    }
    mapImages[0].data[k*4+3]=255;mapImages[1].data[k*4+3]=255;
  }
  contexts.forEach((context,index)=>context.putImageData(mapImages[index],0,0));
}
function frame(data){
  const {fields,readout:r,diagnostics:d}=data;
  if(!d.finite){pause('The material stopped because its state was no longer finite. Open a saved state or begin a new material.');return;}
  const forceLabels=!data.running||data.generation!==lastFrame?.generation;
  renderer.update(fields);sound.control(r,data.drive);
  updateScore(data.score||score);
  if(score.mode==='replaying'||score.mode==='releasing')for(let i=0;i<12;i++)voiceButtons[i].setAttribute('aria-pressed',String(data.targets[i]>0));
  lastFrame={readout:r,diagnostics:d,generation:data.generation};
  const now=performance.now();
  if(forceLabels||now-lastMaps>160){maps(fields);lastMaps=now;}
  if(forceLabels||now-lastLabels>120){
    $('#material-clock').textContent=timeLabel(d.time);
    $('#material-name').textContent=d.fatigue_mean>.35?'Worn':d.memory_rms>.015?'Inscribed':'Unwritten';
    for(let i=0;i<12;i++){
      voiceButtons[i].querySelector('.voice-pitch').textContent=r.pitch[i].toFixed(1);
      voiceButtons[i].querySelector('.voice-level').style.transform=`scaleX(${Math.min(1,r.amplitude[i]*2)})`;
    }
    canvas.dataset.time=d.time.toFixed(5);canvas.dataset.memory=d.memory_rms.toFixed(8);canvas.dataset.wear=d.fatigue_mean.toFixed(8);
    canvas.dataset.audioPeak=sound.peak.toFixed(6);canvas.dataset.generation=data.generation;
    canvas.dataset.materialRunning=String(data.running);
    lastLabels=now;
  }
  worker.postMessage({type:'recycle',fields},[fields.buffer]);
}

try{
  renderer=new LiveRenderer(canvas,()=>{pause('The graphics context was interrupted. Reload to reopen the live sculpture.');canvas.dataset.state='context-lost';});
  worker=new Worker('/live-worker.js',{type:'module'});
  worker.onmessage=({data})=>{
    if(data.type==='frame')frame(data);
    else if(data.type==='snapshot'&&data.request===pendingSave){pendingSave=0;download(data.state);}
    else if(data.type==='restored'){
      running=false;started=true;fading=false;clearHeld();sound.suspend().catch(()=>{});$('#begin-panel').hidden=true;
      lastComparison=null;$('#reply-comparison').hidden=true;controls();say('Material opened. Resume to continue its history.');
    }else if(data.type==='score')updateScore(data.score,data.comparison);
    else if(data.type==='sculpture'){
      saveBlob(new Blob([data.buffer],{type:'model/stl'}),`palimpsest-sculpture-${Math.round(data.time)}s-200mm.stl`);
      exporting=false;controls();say('Sculpture saved as an STL, scaled to 200 mm across.');
    }
    else if(data.type==='undo')$('#undo-material').hidden=!data.available;
    else if(data.type==='error'){exporting=false;controls();say(data.message);}
  };
  worker.onerror=()=>{pause('The material worker could not continue. Reload to begin again.');};
}catch(error){say(error.message);$('#begin-panel').hidden=true;worker?.terminate();}

$('#begin-sound').addEventListener('click',()=>start(true));
$('#begin-silent').addEventListener('click',()=>start(false));
$('#pause-material').addEventListener('click',()=>running?pause():start());
$('#sound-toggle').addEventListener('click',async()=>{
  if(soundEnabled){soundEnabled=false;await sound.suspend();}
  else{try{await sound.start();soundEnabled=true;if(!running)await sound.suspend();}catch(error){say(error.message);}}
  controls();
});
$('#live-volume').addEventListener('input',event=>sound.volume(Number(event.target.value)/100));
$('#view-reset').addEventListener('click',()=>renderer?.reset());
$('#pressure').addEventListener('input',event=>{$('#pressure-value').textContent=`${event.target.value}%`;sendDrive();});
$('#fade-material').addEventListener('click',()=>{fading=!fading;worker.postMessage({type:'fade',value:fading});controls();say(fading?'The inscription is fading. Wear recovers more slowly.':'The material keeps the writing that remains.');});
$('#save-material').addEventListener('click',()=>{pendingSave=++snapshotRequest;worker.postMessage({type:'snapshot',request:pendingSave});});
$('#export-sculpture').addEventListener('click',()=>{pause('Making a sculpture from the present material…');exporting=true;controls();worker.postMessage({type:'sculpture'});});
$('#open-material').addEventListener('change',async event=>{
  const file=event.target.files[0];event.target.value='';if(!file||!worker)return;
  if(file.size>3_000_000){say('This file is too large for a live material. Choose a saved PALIMPSEST material.');return;}
  try{const state=JSON.parse(await file.text());worker.postMessage({type:'restore',state});}
  catch{say('The file could not be read. Your current material is unchanged.');}
});
$('#fresh-material').addEventListener('click',()=>{pause();worker.postMessage({type:'fresh'});say('A fresh material. Resume when you are ready.');});
$('#undo-material').addEventListener('click',()=>{pause();worker.postMessage({type:'undo'});say('The previous material is back. Resume to continue.');});
$('#record-phrase').addEventListener('click',()=>{
  if(score.mode==='recording')clearHeld();
  else if(matchMedia('(max-width: 640px)').matches)$('#playing').scrollIntoView({block:'start',behavior:'instant'});
  worker.postMessage({type:'record'});
});
$('#replay-phrase').addEventListener('click',()=>{clearHeld();worker.postMessage({type:'replay'});if(matchMedia('(max-width: 640px)').matches)$('#playing').scrollIntoView({block:'start',behavior:'instant'});});
$('#save-reply').addEventListener('click',()=>{if(lastComparison)saveBlob(new Blob([replyPlate(lastComparison)],{type:'image/svg+xml'}),'palimpsest-two-replies.svg');});

keys.addEventListener('pointerdown',event=>{
  const button=event.target.closest('.voice-key');if(!button||button.disabled||!running)return;
  event.preventDefault();keys.setPointerCapture(event.pointerId);button.focus();held.set(`pointer-${event.pointerId}`,Number(button.dataset.voice));sendDrive();
});
keys.addEventListener('pointermove',event=>{
  if(score.mode==='replaying'||score.mode==='releasing')return;
  const id=`pointer-${event.pointerId}`;if(!keys.hasPointerCapture(event.pointerId))return;
  const button=document.elementFromPoint(event.clientX,event.clientY)?.closest('.voice-key');
  if(button&&keys.contains(button))held.set(id,Number(button.dataset.voice));else held.delete(id);
  sendDrive();
});
for(const name of ['pointerup','pointercancel','lostpointercapture'])keys.addEventListener(name,event=>{held.delete(`pointer-${event.pointerId}`);sendDrive();});
document.addEventListener('keydown',event=>{
  if(event.ctrlKey||event.metaKey||event.altKey||event.target.matches('input,textarea,select')||!running||score.mode==='replaying'||score.mode==='releasing')return;
  let index=letters.indexOf(event.code.replace('Key',''));
  if((event.code==='Space'||event.code==='Enter')&&event.target.matches('.voice-key'))index=Number(event.target.dataset.voice);
  if(index<0)return;event.preventDefault();if(event.repeat)return;held.set(`key-${event.code}`,index);sendDrive();
});
document.addEventListener('keyup',event=>{if(held.delete(`key-${event.code}`)){event.preventDefault();sendDrive();}});
keys.addEventListener('click',event=>{
  // Screen readers can activate a button without pointer or key-down events.
  if(event.detail!==0||!running)return;
  const button=event.target.closest('.voice-key');if(!button)return;
  const id=`pulse-${button.dataset.voice}`;clearTimeout(pulses.get(id));held.set(id,Number(button.dataset.voice));sendDrive();
  pulses.set(id,setTimeout(()=>{held.delete(id);pulses.delete(id);sendDrive();},1500));
});
window.addEventListener('blur',clearHeld);
document.addEventListener('visibilitychange',()=>{if(document.hidden&&running)pause('Paused while you were away. Resume to continue.');else renderer?.requestDraw();});
window.addEventListener('pagehide',event=>{pause();if(!event.persisted){worker?.terminate();sound.dispose();renderer?.dispose();}});
window.addEventListener('pageshow',event=>{if(event.persisted){renderer?.requestDraw();controls();say('Paused. Resume to continue the material you left.');}});
controls();
