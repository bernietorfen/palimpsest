const $=selector=>document.querySelector(selector),ROOT='/assets/generated/choir-witness/',NS='http://www.w3.org/2000/svg';
let documentData,selected='E',history='before',audio,output,sources=[],gains=[],playing=false,position=0,started=0,request=0,frame=0,seeking=false,seekWasPlaying=false;
const buffers=new Map();
const copy={
 E:['An unchanged<br><em>answer.</em>','E’s recorded tuning and response are identical in the two questions. An unchanged witness does not mean an unchanged choir.'],
 A:['The centre<br><em>keeps a trace.</em>','A was not touched by the writing hand. Forces arrived through the connections. Its returning answer carries that encounter.'],
 C:['A neighbour<br><em>answers differently.</em>','B wrote through a connection into C. After the source has gone and the bridge has been cut, the returning question finds an altered voice.'],
 G:['An encounter<br><em>outlasts its source.</em>','G carries one of the clearest changes in this performance. The connection is absent from the returning question; the retained material still matters.']
};
function say(text,error=false){$('#witness-status').textContent=text;$('#witness-status').dataset.error=String(error);}
function body(){return documentData.bodies.find(b=>b.id===selected);}
function clock(value){return `${Math.floor(value/60).toString().padStart(2,'0')}:${Math.floor(value%60).toString().padStart(2,'0')}`;}
function time(){return playing?Math.max(0,Math.min(40,audio.currentTime-started)):position;}
function updateTime(){const t=time();if(!seeking)$('#question-time').value=String(t);$('#question-clock').textContent=`${clock(t)} / 00:40`;const x=20+t/40*800;$('#reading-cursor').setAttribute('x1',x);$('#reading-cursor').setAttribute('x2',x);document.body.dataset.position=t.toFixed(3);}
function control(){document.body.dataset.playing=String(playing);$('#play-question').innerHTML=playing?'Pause the question <span aria-hidden="true">Ⅱ</span>':'Listen to the question <span aria-hidden="true">▶</span>';}
function stopSources(){for(const source of sources){try{source.stop();}catch{}source.disconnect();}for(const gain of gains)gain.disconnect();sources=[];gains=[];}
function pause(message){position=time();playing=false;stopSources();cancelAnimationFrame(frame);control();updateTime();if(message)say(message);}
function tick(){if(!playing)return;if(time()>=40){position=40;playing=false;stopSources();control();updateTime();say('The question has ended. Change the witness, or listen again.');return;}updateTime();frame=requestAnimationFrame(tick);}
async function prepareAudio(){if(!audio){const Context=window.AudioContext||window.webkitAudioContext;if(!Context)throw new Error('This browser cannot open the listening piece. The recorded files remain available below.');audio=new Context();output=audio.createGain();output.gain.value=1;output.connect(audio.destination);}await audio.resume();}
async function load(name){
 if(!buffers.has(name))buffers.set(name,(async()=>{const response=await fetch(ROOT+name);if(!response.ok)throw new Error('This answer could not be loaded. Please try listening again.');return audio.decodeAudioData(await response.arrayBuffer());})().catch(error=>{buffers.delete(name);throw error;}));
 return buffers.get(name);
}
async function play(){
 const token=++request;$('#play-question').disabled=true;$('#listening').setAttribute('aria-busy','true');say('Opening the two answers…');
 try{
  await prepareAudio();const current=body();const pair=await Promise.all([load(current.before),load(current.after)]);
  if(token!==request)return;
  if(document.hidden){say('Paused while you were away. Listen when you return.');return;}
  if(position>=39.99)position=0;
  const when=audio.currentTime+.035;started=when-position;
  stopSources();
  for(let i=0;i<2;i++){const source=audio.createBufferSource(),gain=audio.createGain();source.buffer=pair[i];gain.gain.value=(i===0)===(history==='before')?1:0;source.connect(gain);gain.connect(output);source.start(when,Math.min(position,pair[i].duration-.01));sources.push(source);gains.push(gain);}
  playing=true;control();tick();say(selected==='E'?'E’s two answers are identical. Switch Before and After, then choose another witness.':'Switch Before and After while the same question unfolds.');
 }catch(error){if(token===request){pause();say(error.message,true);}}
 finally{if(token===request){$('#play-question').disabled=false;$('#listening').removeAttribute('aria-busy');}}
}
function setHistory(value){history=value;document.body.dataset.history=history;for(const button of document.querySelectorAll('button[data-history]'))button.setAttribute('aria-pressed',String(button.dataset.history===value));$('#portrait-before').dataset.active=String(value==='before');$('#portrait-after').dataset.active=String(value==='after');if(audio)gains.forEach((gain,i)=>{gain.gain.cancelScheduledValues(audio.currentTime);gain.gain.setTargetAtTime((i===0)===(history==='before')?1:0,audio.currentTime,.025);});}
function element(tag,attributes){const node=document.createElementNS(NS,tag);for(const [key,value]of Object.entries(attributes))node.setAttribute(key,value);return node;}
function draw(){
 const data=body();document.body.dataset.listener=selected;
 for(const button of document.querySelectorAll('[data-body]'))button.setAttribute('aria-pressed',String(button.dataset.body===selected));
 for(const part of ['before','after']){const image=$('#'+part+'-image');image.src=ROOT+data[part+'_image'];image.alt=`Vessel ${selected} ${part==='before'?'before the encounter':'after the source has left'}, in the same fixed display pose`;}
 $('#reading-title').innerHTML=copy[selected][0];$('#reading-copy').textContent=copy[selected][1];$('#difference').textContent=`${data.pitch_difference_rms_hz.toFixed(3)} Hz`;$('#trajectory-caption').textContent=selected==='E'?'No measured tuning change':'Return minus the first answer';
 const zero=$('#tuning-zero'),curves=$('#tuning-curves');zero.replaceChildren();curves.replaceChildren();
 for(let mode=0;mode<12;mode++){
  const baseline=23+mode*19;zero.append(element('line',{x1:20,x2:820,y1:baseline,y2:baseline,class:'tuning-zero'}));
  const points=data.pitch_delta_hz.map((row,i)=>`${i?'L':'M'}${(20+i/(data.pitch_delta_hz.length-1)*800).toFixed(2)},${(baseline-row[mode]*3).toFixed(3)}`).join('');
  curves.append(element('path',{d:points,class:'tuning-curve'}));
 }
 updateTime();
}
async function choose(id){if(!documentData||id===selected)return;const resume=playing;request++;pause();selected=id;draw();$('#play-question').disabled=false;$('#listening').removeAttribute('aria-busy');say(selected==='E'?'E keeps an unchanged answer. Choose Before or After, then listen.':`Listen to ${selected}, then switch Before and After.`);if(resume)await play();}
$('#play-question').addEventListener('click',()=>playing?pause('Paused. The two answers stay aligned.'):play());
for(const button of document.querySelectorAll('[data-body]'))button.addEventListener('click',()=>choose(button.dataset.body));
for(const button of document.querySelectorAll('button[data-history]'))button.addEventListener('click',()=>setHistory(button.dataset.history));
$('#question-time').addEventListener('input',event=>{if(!seeking){seekWasPlaying=playing||$('#listening').getAttribute('aria-busy')==='true';seeking=true;request++;pause();$('#play-question').disabled=false;$('#listening').removeAttribute('aria-busy');}position=Number(event.target.value);updateTime();});
$('#question-time').addEventListener('change',()=>{seeking=false;updateTime();if(seekWasPlaying){seekWasPlaying=false;play();}});
$('#question-time').addEventListener('blur',()=>{if(seeking){seeking=false;updateTime();if(seekWasPlaying){seekWasPlaying=false;play();}}});
document.addEventListener('visibilitychange',()=>{if(document.hidden){request++;pause('Paused while you were away. Listen to continue.');$('#play-question').disabled=!documentData;$('#listening').removeAttribute('aria-busy');}});
window.addEventListener('pagehide',()=>{request++;pause();});
(async()=>{try{const response=await fetch(ROOT+'witness.json');if(!response.ok)throw new Error('The comparison record could not be loaded. Reload to try again.');const data=await response.json();if(data.format!=='palimpsest-choir-witness'||data.duration!==40||data.bodies.length!==4||!data.bodies.every(b=>copy[b.id]&&Number.isFinite(b.pitch_difference_rms_hz)&&b.pitch_delta_hz.length===481&&b.pitch_delta_hz.every(row=>row.length===12&&row.every(Number.isFinite))))throw new Error('The comparison record is incomplete.');documentData=data;draw();setHistory('before');$('#play-question').disabled=false;$('#question-time').disabled=false;document.body.dataset.ready='true';say('Begin with E. Then choose a different witness.');}catch(error){say(error.message,true);}})();
