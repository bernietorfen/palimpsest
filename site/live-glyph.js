import {PITCHES} from './live-material.js';
const NS='http://www.w3.org/2000/svg';
const element=(name,attributes)=>{const e=document.createElementNS(NS,name);for(const[key,value]of Object.entries(attributes))e.setAttribute(key,value);return e;};
function path(points){
  let d=`M ${points[0][0].toFixed(3)} ${points[0][1].toFixed(3)}`;
  for(let i=0;i<12;i++){
    const p0=points[(i+11)%12],p1=points[i],p2=points[(i+1)%12],p3=points[(i+2)%12];
    const values=[p1[0]+(p2[0]-p0[0])/6,p1[1]+(p2[1]-p0[1])/6,p2[0]-(p3[0]-p1[0])/6,p2[1]-(p3[1]-p1[1])/6,p2[0],p2[1]];
    d+=` C ${values.map(v=>v.toFixed(3)).join(' ')}`;
  }
  return d+' Z';
}
export function drawReplyPair(first,second,comparison){
  const replies=[comparison.previous,comparison.current];
  const chosen=replies.map(response=>[.1,.37,.64,.91].map(f=>response[Math.min(response.length-1,Math.floor(f*(response.length-1)))].pitch));
  const extent=Math.max(1,...chosen.flatMap(rings=>rings.flatMap(pitches=>pitches.map((pitch,index)=>Math.abs(pitch-PITCHES[index])))));
  [first,second].forEach((svg,index)=>{
    svg.replaceChildren();
    for(let voice=0;voice<12;voice++){
      const a=voice*Math.PI/6-Math.PI/2;
      svg.append(element('line',{x1:140+21*Math.cos(a),y1:140+21*Math.sin(a),x2:140+121*Math.cos(a),y2:140+121*Math.sin(a),stroke:'#b9b5a5','stroke-width':'.45'}));
      const label=element('text',{x:140+131*Math.cos(a),y:143+131*Math.sin(a),'text-anchor':'middle',fill:'#6b7167','font-size':'7'});
      label.textContent=String(voice+1).padStart(2,'0');svg.append(label);
    }
    for(let ring=0;ring<4;ring++){
      const radius=35+ring*23;
      svg.append(element('circle',{cx:140,cy:140,r:radius,fill:'none',stroke:'#c8c1af','stroke-width':'.5'}));
      const points=chosen[index][ring].map((pitch,voice)=>{
        const a=voice*Math.PI/6-Math.PI/2,r=radius+16*(pitch-PITCHES[voice])/extent;
        return[140+r*Math.cos(a),140+r*Math.sin(a)];
      });
      svg.append(element('path',{d:path(points),fill:'none',stroke:index?'#293c3e':'#8f602e','stroke-width':ring===3?'1.6':'1.1'}));
    }
    svg.dataset.scaleHz=extent.toFixed(6);
  });
}

export function replyPlate(comparison){
  const root=element('svg',{xmlns:NS,width:1400,height:1050,viewBox:'0 0 1400 1050','font-family':'Arial, sans-serif'});
  const title=element('title',{});title.textContent='PALIMPSEST — two replies to one phrase';root.append(title);
  const description=element('desc',{});description.textContent='Two original four-ring drawings of twelve voice tunings. Both use a shared radial scale. The complete measured trajectories accompany this image as SVG metadata.';root.append(description);
  const metadata=element('metadata',{});metadata.textContent=JSON.stringify({format:'palimpsest-paired-reply',version:1,created_utc:new Date().toISOString(),sample_fractions:[.1,.37,.64,.91],comparison});root.append(metadata);
  root.append(element('rect',{width:1400,height:1050,fill:'#ede8da'}));
  const text=(value,x,y,size,attributes={})=>{const node=element('text',{x,y,'font-size':size,fill:'#293c3e',...attributes});node.textContent=value;root.append(node);return node;};
  text('PALIMPSEST',95,139,91,{'font-family':'Georgia, serif','letter-spacing':'-4'});
  text('Two replies to one phrase',100,188,24,{'font-family':'Georgia, serif'});
  text('AN INSTRUMENT BY CODEX',1300,98,11,{'text-anchor':'end','letter-spacing':'1.2'});
  text('GESTURES BY ITS PLAYER',1300,120,11,{'text-anchor':'end','letter-spacing':'1.2'});
  root.append(element('line',{x1:100,x2:1300,y1:225,y2:225,stroke:'#c7c2b4','stroke-width':1}));
  const first=element('svg',{x:100,y:273,width:500,height:500,viewBox:'0 0 280 280'});
  const second=element('svg',{x:800,y:273,width:500,height:500,viewBox:'0 0 280 280'});
  drawReplyPair(first,second,comparison);root.append(first,second);
  text('I.  Earlier reply',350,814,18,{'text-anchor':'middle','font-family':'Georgia, serif'});
  text('II.  Most recent reply',1050,814,18,{'text-anchor':'middle','font-family':'Georgia, serif'});
  root.append(element('line',{x1:100,x2:1300,y1:860,y2:860,stroke:'#c7c2b4','stroke-width':1}));
  text(`Difference across the phrase: ${comparison.rms_hz.toFixed(6)} Hz RMS`,100,899,16);
  text(`Shared radial scale: ±${Number(first.dataset.scaleHz).toFixed(3)} Hz`,1300,899,13,{'text-anchor':'end'});
  text('Time runs outward through four rings; each ring follows twelve voices. Faint circles mark the original tuning.',100,935,13,{fill:'#5f6860'});
  text('The answers include the material’s motion and retained fields at the start of each reply.',100,958,13,{fill:'#5f6860'});
  text('A drawing from a material that remembers.',100,1004,15,{'font-family':'Georgia, serif'});
  text('PALIMPSEST / LIVE EDITION / 2026',1300,1004,10,{'text-anchor':'end','letter-spacing':'.9'});
  return new XMLSerializer().serializeToString(root);
}
