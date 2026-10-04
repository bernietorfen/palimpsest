const $=selector=>document.querySelector(selector),NS='http://www.w3.org/2000/svg';
const DATA_SHA='e8010a136443c2bd0b3854965aade4dd7def03d612d1b3f2dab529c962e8e886';
let data=null,alpha=0,playing=false,frameId=0,startTime=0,timeline=[],drawing=null,tableRows=[],fontPromise=null,loading=false;
const artStyle='.origin-track{stroke:#bbb7ab;stroke-width:1;fill:none}.origin-divider{stroke:#aaa797;stroke-width:.6}.origin-midpoint{stroke:#7e8277;stroke-width:.9;stroke-dasharray:3 5}.origin-anchor{stroke:#2b3939;stroke-width:1.2;fill:#e9e5dc}.origin-trail{stroke:#a64c34;stroke-width:1.25;opacity:.38}.origin-current{fill:#a64c34}.origin-current[data-own="true"]{fill:#315d6b}.origin-current[data-tied="true"]{fill:#e9e5dc;stroke:#895235;stroke-width:2}.origin-ghost{fill:none;stroke:#a64c34;stroke-width:.85;opacity:.5}.origin-text{fill:#2b3939;font-family:"Palimpsest Sans",Arial,sans-serif;font-size:14px}.origin-id{fill:#626960;font-family:"Palimpsest Sans",Arial,sans-serif;font-size:11px;letter-spacing:1px}.origin-own-label{fill:#315d6b;font-family:"Palimpsest Serif",Georgia,serif;font-size:23px}.origin-rival-label{fill:#626960;font-family:"Palimpsest Serif",Georgia,serif;font-size:23px}.origin-reading-label{fill:#626960;font-family:"Palimpsest Sans",Arial,sans-serif;font-size:11px}';
function svg(tag,attributes={},text){const node=document.createElementNS(NS,tag);for(const [key,value]of Object.entries(attributes))node.setAttribute(key,String(value));if(text!==undefined)node.textContent=text;return node;}
function reading(position){
 const nearest=[],ownDistances=[];let own=0,tied=0;
 for(let h=0;h<24;h++){
  const values=data.a[h].map((a,j)=>a-2*position*data.b[h][j]),minimum=Math.min(...values),choices=[];
  for(let j=0;j<24;j++)if(values[j]<=minimum+data.squared_hz_tie_tolerance)choices.push(j);
  nearest.push(choices);if(choices.length===1&&choices[0]===h)own++;if(choices.length>1)tied++;
  ownDistances.push(Math.sqrt(Math.max(0,values[h]+position*position*data.c)));
 }
 return {nearest,own,tied,ownDistances};
}
function validate(value){
 const number=x=>Number.isFinite(x),index=x=>Number.isInteger(x)&&x>=0&&x<24;
 if(value.version!==1||value.coordinates!==3468||value.receiver!==1||value.rates?.join()!=='96,192'||value.orders?.length!==24||new Set(value.orders).size!==24||!value.orders.every(x=>/^[ABCD]{4}$/.test(x)&&new Set(x).size===4))throw Error('Invalid measured collection');
 for(const name of ['a','b'])if(value[name]?.length!==24||!value[name].every(row=>row.length===24&&row.every(number)))throw Error('Invalid comparison coefficients');
 if(!number(value.c)||value.c<=0||value.squared_hz_tie_tolerance!==1e-15||value.rows?.length!==6||value.events?.length!==6)throw Error('Invalid comparison geometry');
 for(const row of value.rows)if(!index(row.history)||!index(row.rival)||row.history===row.rival||![row.raw_projection,row.aligned_projection,row.pair_separation_hz].every(number)||row.pair_separation_hz<=0)throw Error('Invalid projection');
 for(const event of value.events)if(!index(event.history)||!index(event.before)||!index(event.after)||!(event.alpha>0&&event.alpha<1)||!event.at?.every(index))throw Error('Invalid crossing');
 return value;
}
function artwork(width){
 const group=svg('g'),margin=width<700?28:66,x=t=>margin+(t+.16)/1.32*(width-2*margin),rows=[];
 data.rows.forEach((row,i)=>{
  const y=65+i*113,g=svg('g',{'data-history':data.orders[row.history]});
  g.append(svg('text',{x:width<700?8:margin,y:y-22,class:'origin-id'},String(i+1).padStart(2,'0')),
   svg('text',{x:x(0),y:y-18,'text-anchor':'middle',class:'origin-own-label'},data.orders[row.history]),
   svg('text',{x:x(1),y:y-18,'text-anchor':'middle',class:'origin-rival-label'},data.orders[row.rival]),
   svg('line',{x1:x(-.12),x2:x(1.10),y1:y,y2:y,class:'origin-track'}),
   svg('line',{x1:x(.5),x2:x(.5),y1:y-13,y2:y+16,class:'origin-midpoint'}));
  for(const t of [0,1])g.append(svg('circle',{cx:x(t),cy:y,r:4.5,class:'origin-anchor'}));
  const trail=svg('line',{x1:x(row.raw_projection),x2:x(row.raw_projection),y1:y,y2:y,class:'origin-trail'}),point=svg('circle',{cx:x(row.raw_projection),cy:y,r:6.5,class:'origin-current'}),label=svg('text',{x:x(.5),y:y+33,'text-anchor':'middle',class:'origin-reading-label'});
  g.append(trail,svg('circle',{cx:x(row.raw_projection),cy:y,r:4,class:'origin-ghost'}),point,
   svg('text',{x:x(0),y:y+30,'text-anchor':'middle',class:'origin-reading-label'},'Own history'),
   svg('text',{x:x(1),y:y+30,'text-anchor':'middle',class:'origin-reading-label'},'Original rival'),label,
   svg('line',{x1:margin,x2:width-margin,y1:y+67,y2:y+67,class:'origin-divider'}));
  group.append(g);rows.push({row,point,trail,label,x});
 });
 group.append(svg('text',{x:margin,y:787,class:'origin-reading-label'},'One shared vector, expressed along six different directions.'));
 return {group,rows,width};
}
function paint(target,state,position=alpha){for(const {row,point,trail,label,x}of target.rows){const projection=row.raw_projection+position*(row.aligned_projection-row.raw_projection),choices=state.nearest[row.history],own=choices.length===1&&choices[0]===row.history,tied=choices.length>1;point.setAttribute('cx',x(projection));point.dataset.own=String(own);point.dataset.tied=String(tied);trail.setAttribute('x2',x(projection));label.textContent=tied?'An equal-distance reading':'Read as '+data.orders[choices[0]];}}
function rebuild(){if(!data)return;const width=matchMedia('(max-width:600px)').matches?500:1100;drawing=artwork(width);const root=$('#origin-drawing');root.setAttribute('viewBox',`0 0 ${width} 820`);root.querySelector('g')?.remove();root.append(drawing.group);paint(drawing,reading(alpha));}
function status(message){$('#origin-status').textContent=message;}
function position(value,{announce=false}={}){
 if(!data)return;alpha=Math.max(0,Math.min(1,Number(value)));if(!Number.isFinite(alpha))alpha=0;const state=reading(alpha);
 document.body.dataset.alpha=String(alpha);document.body.dataset.own=String(state.own);document.body.dataset.ties=String(state.tied);$('#origin-shift').value=String(alpha);$('#origin-shift').setAttribute('aria-valuetext',`${(alpha*100).toFixed(2)} percent aligned; ${state.own} unique own-history matches${state.tied?`; ${state.tied} tied`:''}`);
 $('#origin-position').textContent=(alpha*100).toFixed(1)+'%';$('#origin-count').replaceChildren(document.createTextNode(String(state.own)),Object.assign(document.createElement('span'),{textContent:' / 24'}));$('#origin-count-caption').textContent=state.tied?`own histories; ${state.tied} tied reading`:'read as their own history';
 const event=data.events.find(event=>Math.abs(event.alpha-alpha)<1e-10);
 $('#origin-state').textContent=event?`${data.orders[event.history]} meets the boundary between ${data.orders[event.before]} and ${data.orders[event.after]}.`:alpha===0?'The original reading: eighteen own histories, six other matches.':alpha===1?'The collections are aligned. All twenty-four find their own history.':state.own===24?'All twenty-four find their own history. The shared shift continues.':`${state.own} histories find their own past as the origin moves.`;
 $('#origin-next').disabled=!data.events.some(event=>event.alpha>alpha+1e-10);paint(drawing,state);
 for(let h=0;h<24;h++){const choices=state.nearest[h],row=tableRows[h];row.tr.dataset.own=String(choices.length===1&&choices[0]===h);row.tr.dataset.tied=String(choices.length>1);row.choice.textContent=choices.map(j=>data.orders[j]).join(' / ')+(choices.length>1?' (tie)':'');row.distance.textContent=state.ownDistances[h].toFixed(6)+' Hz';}
 if(announce)status(`${state.own} of twenty-four own-history matches${state.tied?`, with ${state.tied} tied reading`:''}.`);
}
function stop(message){playing=false;cancelAnimationFrame(frameId);document.body.dataset.playing='false';$('#origin-play').textContent='Let it move ↗';if(message)status(message);}
function atTime(seconds){for(let i=1;i<timeline.length;i++){const a=timeline[i-1],b=timeline[i];if(seconds<=b.time)return a.alpha+(b.alpha-a.alpha)*(seconds-a.time)/(b.time-a.time);}return 1;}
function timeAt(value){for(let i=1;i<timeline.length;i++){const a=timeline[i-1],b=timeline[i];if(value<=b.alpha)return b.alpha===a.alpha?a.time:a.time+(value-a.alpha)/(b.alpha-a.alpha)*(b.time-a.time);}return timeline.at(-1).time;}
function tick(now){if(!playing)return;const elapsed=(now-startTime)/1000;position(atTime(elapsed));if(elapsed>=timeline.at(-1).time){position(1);stop('The passage is complete. All twenty-four histories find their own past.');return;}frameId=requestAnimationFrame(tick);}
function play(){if(!data)return;if(playing){stop('The movement is paused.');return;}if(alpha>=1)position(0);playing=true;document.body.dataset.playing='true';$('#origin-play').textContent='Pause the movement';status('The passage pauses briefly at each measured crossing.');startTime=performance.now()-timeAt(alpha)*1000;frameId=requestAnimationFrame(tick);}
function table(){tableRows=[];const body=$('#origin-table');body.replaceChildren();for(const history of data.orders){const tr=document.createElement('tr'),th=document.createElement('th'),choice=document.createElement('td'),distance=document.createElement('td');th.scope='row';th.textContent=history;tr.append(th,choice,distance);body.append(tr);tableRows.push({tr,choice,distance});}}
async function bounded(url,limit){const response=await fetch(url);if(!response.ok)throw Error('Asset unavailable');const reader=response.body.getReader(),parts=[];let size=0;try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>limit){await reader.cancel();throw Error('Asset exceeds its budget');}parts.push(value);}}finally{reader.releaseLock();}const bytes=new Uint8Array(size);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.length;}return bytes;}
function base64(bytes){let result='';for(let i=0;i<bytes.length;i+=8192)result+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(result);}
async function fonts(){if(!fontPromise)fontPromise=Promise.all(['serif.woff2','sans.woff2','font-license.txt'].map(name=>bounded('/assets/generated/'+name,300000))).catch(error=>{fontPromise=null;throw error;});return fontPromise;}
async function exportDrawing(){if(!data)return;stop();$('#origin-export').disabled=true;status('Preparing the measured drawing…');try{
 const captured=alpha,state=reading(captured),[serif,sans,license]=await fonts(),root=svg('svg',{xmlns:NS,width:1440,height:1375,viewBox:'0 0 1100 1050'}),style=svg('style',{},`@font-face{font-family:'Palimpsest Serif';src:url(data:font/woff2;base64,${base64(serif)}) format('woff2')}@font-face{font-family:'Palimpsest Sans';src:url(data:font/woff2;base64,${base64(sans)}) format('woff2')}${artStyle}`);
 root.append(svg('title',{},'The origin moves / PALIMPSEST'),svg('desc',{},`A measured geometric print at ${(captured*100).toFixed(6)} percent collection alignment. ${state.own} unique own-history matches and ${state.tied} tied readings.`),svg('metadata',{},JSON.stringify({title:'The origin moves',author:'Codex',alpha:captured,data_sha256:DATA_SHA,own_matches:state.own,tied_readings:state.tied,nearest_sets:state.nearest.map(values=>values.map(j=>data.orders[j])),input_sha256:data.input_sha256,font_license:new TextDecoder().decode(license)})),style,svg('rect',{width:1100,height:1050,fill:'#e9e5dc'}),svg('text',{x:66,y:43,class:'origin-id'},'PALIMPSEST / THE OBSERVER'),svg('text',{x:66,y:106,'font-family':'Palimpsest Serif, Georgia, serif','font-size':45,fill:'#2b3939'},'The origin moves.'),svg('text',{x:66,y:143,class:'origin-text'},`${(captured*100).toFixed(6)}% of one shared translation / ${state.own} own histories${state.tied?` / ${state.tied} tied`:''}`));
 const art=artwork(1100);paint(art,state,captured);art.group.setAttribute('transform','translate(0 175)');root.append(art.group,svg('text',{x:66,y:1017,class:'origin-reading-label'},'CODEX / 2026 · Fixed recorded replies. One shared change of origin. Complete measurement identity in the SVG metadata.'));
 const blob=new Blob(['<?xml version="1.0" encoding="UTF-8"?>\n',new XMLSerializer().serializeToString(root)],{type:'image/svg+xml'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`the-origin-moves-${(captured*100).toFixed(4)}-percent.svg`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status('The drawing keeps this position, its measured readings and source identity.');
 }catch{status('The drawing could not be prepared. Try saving it again.');}finally{$('#origin-export').disabled=false;}}
async function load(){if(loading)return;loading=true;$('#origin-retry').hidden=true;$('#moving-origin').setAttribute('aria-busy','true');$('#origin-status').dataset.error='false';try{
 const bytes=await bounded('/assets/generated/observer-origin-v1.json',200000),digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');if(digest!==DATA_SHA)throw Error('The measured file changed');data=validate(JSON.parse(new TextDecoder().decode(bytes)));
 if(reading(0).own!==18||reading(1).own!==24)throw Error('The reference readings differ');timeline=[{time:0,alpha:0}];data.events.forEach((event,i)=>timeline.push({time:2.8*(i+1),alpha:event.alpha},{time:2.8*(i+1)+.65,alpha:event.alpha}));timeline.push({time:24,alpha:1});
 table();rebuild();for(const id of ['origin-play','origin-reset','origin-shift','origin-next','origin-export'])$('#'+id).disabled=false;position(0);document.body.dataset.ready='true';document.body.dataset.dataSha256=DATA_SHA;document.body.dataset.playing='false';status('Move the slider, or let the six crossings unfold.');
 }catch{data=null;document.body.dataset.ready='false';$('#origin-status').dataset.error='true';$('#origin-state').textContent='The measured comparison is unavailable.';status('The measured comparisons could not be opened. The original print and companion remain available below.');$('#origin-retry').hidden=false;for(const id of ['origin-play','origin-reset','origin-shift','origin-next','origin-export'])$('#'+id).disabled=true;}finally{loading=false;$('#moving-origin').setAttribute('aria-busy','false');}}
$('#origin-play').addEventListener('click',play);$('#origin-reset').addEventListener('click',()=>{stop();position(0,{announce:true});});$('#origin-shift').addEventListener('input',event=>{stop();position(event.target.value);});$('#origin-shift').addEventListener('change',()=>position(alpha,{announce:true}));
$('#origin-shift').addEventListener('keydown',event=>{let next;if(event.key==='ArrowLeft'||event.key==='ArrowDown')next=alpha-(event.shiftKey ? .001 : .01);else if(event.key==='ArrowRight'||event.key==='ArrowUp')next=alpha+(event.shiftKey ? .001 : .01);else if(event.key==='Home')next=0;else if(event.key==='End')next=1;else return;event.preventDefault();stop();position(next,{announce:true});});
$('#origin-next').addEventListener('click',()=>{stop();const event=data?.events.find(event=>event.alpha>alpha+1e-10);if(event)position(event.alpha,{announce:true});});$('#origin-export').addEventListener('click',exportDrawing);$('#origin-retry').addEventListener('click',load);matchMedia('(max-width:600px)').addEventListener('change',rebuild);document.addEventListener('visibilitychange',()=>{if(document.hidden&&playing)stop('The movement paused while the page was away.');});window.addEventListener('pagehide',()=>stop());load();
