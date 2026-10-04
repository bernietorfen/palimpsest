const $=s=>document.querySelector(s),film=$('#ensemble-film'),entry=$('#enter-ensemble'),status=$('#ensemble-status');
let seek=null;
function loadFilm(){if(!film.getAttribute('src')){film.src=film.dataset.src;film.load();}}
async function playFilm(time=null){
 if(time!==null){seek=time;if(film.readyState>=1){film.currentTime=seek;seek=null;}}
 loadFilm();film.controls=true;entry.hidden=true;status.textContent='Opening the film…';
 try{await film.play();status.textContent='';}catch{status.textContent='Use the video’s play control to begin.';}
}
entry.addEventListener('click',()=>playFilm());film.addEventListener('loadedmetadata',()=>{if(seek!==null){film.currentTime=seek;seek=null;}});film.addEventListener('playing',()=>{status.textContent='';});film.addEventListener('error',()=>{status.textContent='The film could not open. Its separate download is available below.';});
for(const button of document.querySelectorAll('[data-choir-seek]'))button.addEventListener('click',()=>{film.scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});playFilm(Number(button.dataset.choirSeek));});
document.addEventListener('visibilitychange',()=>{if(document.hidden)film.pause();});
const dialog=$('#choir-sculpture-dialog'),canvas=$('#choir-sculpture-canvas'),sculptureStatus=$('#choir-sculpture-status');
const names={encounter:'What passes between',after:'After the source leaves',source:'The source, before departure'};
let viewer=null,controller=null,generation=0,active=null;
async function openSculpture(name,{restore=false}={}){
 if(!names[name])return;
 const version=++generation;controller?.abort();viewer?.dispose();viewer=null;controller=new AbortController();active=name;film.pause();
 if(!dialog.open)dialog.showModal();document.body.style.overflow='hidden';$('#choir-sculpture-title').textContent=names[name];$('#download-choir-sculpture').href=`https://github.com/bernietorfen/palimpsest/releases/download/v2.0.0/choir-${name}.glb`;
 sculptureStatus.textContent=restore?'Restoring the sculpture…':'Opening the sculpture…';canvas.dataset.state='loading';
 try{
  const {SculptureViewer}=await import('./sculpture.js');if(version!==generation||!dialog.open)return;
  viewer=new SculptureViewer(canvas,{background:[233/255,229/255,220/255],distance:name==='source'?4.25:3.15,responsiveFit:true});await viewer.load(`/assets/generated/choir-${name}.glb`,controller.signal);
  if(version!==generation||!dialog.open)return;
  sculptureStatus.textContent='';canvas.focus();document.body.dataset.sculpture=name;
 }catch(error){if(version!==generation||error.name==='AbortError')return;sculptureStatus.textContent='The interactive view could not open. The glTF sculpture remains available to download.';canvas.dataset.state='error';}
}
for(const button of document.querySelectorAll('[data-choir-sculpture]'))button.addEventListener('click',()=>openSculpture(button.dataset.choirSculpture));
$('#close-choir-sculpture').addEventListener('click',()=>dialog.close());$('#reset-choir-sculpture').addEventListener('click',()=>viewer?.reset());
dialog.addEventListener('close',()=>{generation++;controller?.abort();viewer?.dispose();viewer=null;active=null;document.body.style.overflow='';delete document.body.dataset.sculpture;});
dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const box=dialog.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)dialog.close();});
canvas.addEventListener('webglcontextlost',()=>{sculptureStatus.textContent='The drawing was interrupted. Waiting for the graphics to recover…';});
canvas.addEventListener('webglcontextrestored',()=>{if(dialog.open&&active)openSculpture(active,{restore:true});});
fetch('/choir-edition.json').then(r=>{if(!r.ok)throw new Error('Edition unavailable');return r.json();}).then(edition=>{
 if(!Array.isArray(edition.downloads)||!edition.downloads.length)return;
 const links=edition.downloads.map(item=>{const url=new URL(item.url,location.origin);if(url.origin!==location.origin&&url.origin!=='https://github.com')throw new Error('Unexpected edition origin');const link=document.createElement('a');link.href=url.href;if(url.origin===location.origin)link.download='';const title=document.createElement('span'),detail=document.createElement('span');title.textContent=item.title;detail.textContent=item.detail+' ↓';link.append(title,detail);return link;});$('#choir-downloads').replaceChildren(...links);
}).catch(()=>{});
