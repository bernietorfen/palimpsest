import {add,sub,scale,cross,unit,identity,multiply,transform,point,lookAt,perspective,orthographic,listenerAnchor,naturalSpline} from './choir-math.js';

export class ChoirRenderer {
  constructor(canvas,scene,sources,callbacks={}){
    this.canvas=canvas;this.scene=scene;this.sources=sources;this.callbacks=callbacks;
    this.gl=canvas.getContext('webgl2',{alpha:false,antialias:true,powerPreference:'low-power'});
    if(!this.gl)throw new Error('This browser cannot display the live choir. The recorded work is still available.');
    this.resources=[];this.events=new AbortController();this.frame=0;this.lost=false;this.mode='touch';this.selected=1;this.pointers=new Map();
    this.size=scene.material.live_size;this.fields=scene.bodies.map(()=>new Float32Array(this.size*this.size*4));this.models=scene.bodies.map(transform);
    this.bridgeU=new Float64Array(scene.connections.length*scene.bridge.beads);this.bridgeV=new Float64Array(this.bridgeU.length);this.endpoints=new Float64Array(scene.connections.length*2);this.gates=new Float64Array(scene.connections.length).fill(1);
    this.initialize();this.reset();this.bindInput();this.resize=new ResizeObserver(()=>this.requestDraw());this.resize.observe(canvas);
    canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();this.lost=true;cancelAnimationFrame(this.frame);this.frame=0;callbacks.lost?.();},{signal:this.events.signal});
    canvas.addEventListener('webglcontextrestored',()=>{this.resources=[];try{this.initialize();this.lost=false;this.updateBridges();this.requestDraw();callbacks.restored?.();}catch(error){callbacks.error?.(error);}},{signal:this.events.signal});
    canvas.dataset.state='ready';
  }
  own(kind,value){this.resources.push([kind,value]);return value;}
  initialize(){
    const gl=this.gl;this.program=this.own('Program',gl.createProgram());
    for(const [kind,source]of [[gl.VERTEX_SHADER,this.sources[0]],[gl.FRAGMENT_SHADER,this.sources[1]]]){const shader=gl.createShader(kind);gl.shaderSource(shader,source);gl.compileShader(shader);if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS)){const error=gl.getShaderInfoLog(shader);gl.deleteShader(shader);throw new Error(error);}gl.attachShader(this.program,shader);gl.deleteShader(shader);}
    gl.linkProgram(this.program);if(!gl.getProgramParameter(this.program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(this.program));
    this.uniform=Object.fromEntries(['fields','shadowMap','model','viewProjection','lightProjection','shape','shape2','kind','pass','bodyId','selected','opening','eye'].map(name=>[name,gl.getUniformLocation(this.program,name)]));
    this.bodyMesh=this.gridMesh(48,72);this.bodyTextures=this.fields.map(f=>this.texture(this.size,this.size,gl.RGBA32F,gl.RGBA,gl.FLOAT,f));
    this.bridges=this.scene.connections.map(()=>({mesh:this.gridMesh(2,80,true),texture:this.texture(2,81,gl.RGBA32F,gl.RGBA,gl.FLOAT,new Float32Array(2*81*4))}));
    const floor=this.scene.floor;
    this.floorMesh=this.mesh(new Float32Array([-60,floor,-60,0,1,0,0,0,-60,floor,60,0,1,0,0,1,60,floor,-60,0,1,0,1,0,60,floor,60,0,1,0,1,1]),new Uint32Array([0,1,2,2,1,3]));
    this.emptyTexture=this.texture(2,2,gl.RGBA32F,gl.RGBA,gl.FLOAT,new Float32Array(16));
    this.shadowSize=1024;this.shadowTexture=this.texture(1024,1024,gl.DEPTH_COMPONENT24,gl.DEPTH_COMPONENT,gl.UNSIGNED_INT,null);
    this.shadowBuffer=this.own('Framebuffer',gl.createFramebuffer());gl.bindFramebuffer(gl.FRAMEBUFFER,this.shadowBuffer);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.TEXTURE_2D,this.shadowTexture,0);gl.drawBuffers([gl.NONE]);gl.readBuffer(gl.NONE);this.checkFramebuffer();
    this.pickBuffer=this.own('Framebuffer',gl.createFramebuffer());this.pickTexture=this.texture(1,1,gl.RGBA8,gl.RGBA,gl.UNSIGNED_BYTE,null);this.pickDepth=this.own('Renderbuffer',gl.createRenderbuffer());
    gl.bindFramebuffer(gl.FRAMEBUFFER,this.pickBuffer);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,this.pickTexture,0);gl.bindRenderbuffer(gl.RENDERBUFFER,this.pickDepth);gl.renderbufferStorage(gl.RENDERBUFFER,gl.DEPTH_COMPONENT16,1,1);gl.framebufferRenderbuffer(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.RENDERBUFFER,this.pickDepth);this.checkFramebuffer();
    this.lightProjection=multiply(orthographic(8.5),lookAt([-8,12,9]));this.shadowDirty=true;this.pickWidth=1;this.pickHeight=1;this.updateBridges();
  }
  checkFramebuffer(){if(this.gl.checkFramebufferStatus(this.gl.FRAMEBUFFER)!==this.gl.FRAMEBUFFER_COMPLETE)throw new Error('The choir could not prepare its drawing surface');}
  texture(w,h,internal,format,type,data){const gl=this.gl,t=this.own('Texture',gl.createTexture());gl.bindTexture(gl.TEXTURE_2D,t);gl.texImage2D(gl.TEXTURE_2D,0,internal,w,h,0,format,type,data);for(const key of [gl.TEXTURE_MIN_FILTER,gl.TEXTURE_MAG_FILTER])gl.texParameteri(gl.TEXTURE_2D,key,gl.NEAREST);for(const key of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T])gl.texParameteri(gl.TEXTURE_2D,key,gl.CLAMP_TO_EDGE);return t;}
  mesh(vertices,indices,dynamic=false){const gl=this.gl,vao=this.own('VertexArray',gl.createVertexArray()),vbo=this.own('Buffer',gl.createBuffer());gl.bindVertexArray(vao);gl.bindBuffer(gl.ARRAY_BUFFER,vbo);gl.bufferData(gl.ARRAY_BUFFER,vertices,dynamic?gl.DYNAMIC_DRAW:gl.STATIC_DRAW);for(const [index,size,offset]of[[0,3,0],[1,3,12],[2,2,24]]){gl.enableVertexAttribArray(index);gl.vertexAttribPointer(index,size,gl.FLOAT,false,32,offset);}gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,this.own('Buffer',gl.createBuffer()));gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,indices,gl.STATIC_DRAW);return {vao,vbo,count:indices.length,vertices};}
  gridMesh(nx,ny,dynamic=false){const v=new Float32Array((nx+1)*(ny+1)*8),indices=new Uint32Array(nx*ny*6);for(let y=0;y<=ny;y++)for(let x=0;x<=nx;x++){const k=(y*(nx+1)+x)*8;v[k+4]=1;v[k+6]=x/nx;v[k+7]=y/ny;}let k=0;for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){const a=y*(nx+1)+x,b=a+1,c=a+nx+1,d=c+1;indices.set([a,b,c,b,d,c],k);k+=6;}return this.mesh(v,indices,dynamic);}
  update(frame){
    const gl=this.gl,count=this.size*this.size*4;
    for(let i=0;i<this.fields.length;i++){this.fields[i].set(frame.fields.subarray(i*count,(i+1)*count));if(!this.lost){gl.bindTexture(gl.TEXTURE_2D,this.bodyTextures[i]);gl.texSubImage2D(gl.TEXTURE_2D,0,0,0,this.size,this.size,gl.RGBA,gl.FLOAT,this.fields[i]);}}
    this.bridgeU.set(frame.bridgeU);this.bridgeV.set(frame.bridgeV);this.endpoints.set(frame.endpoints);this.gates.set(frame.gates);this.selected=frame.selected;
    if(!this.lost){this.updateBridges();this.shadowDirty=true;this.requestDraw();}
  }
  updateBridges(){
    const gl=this.gl,beads=this.scene.bridge.beads;
    this.scene.connections.forEach((edge,e)=>{
      const anchor=p=>point(this.models[p[0]],listenerAnchor(p.slice(1),this.fields[p[0]],this.size,this.scene.shapes[this.scene.bodies[p[0]].shape]));
      const a=anchor(edge.first),b=anchor(edge.second),chord=sub(b,a);let horizontal=cross(chord,[0,1,0]);if(Math.hypot(...horizontal)<.001)horizontal=cross(chord,[0,0,1]);horizontal=unit(horizontal);
      const q=[this.endpoints[e*2],...this.bridgeU.subarray(e*beads,(e+1)*beads),this.endpoints[e*2+1]],wave=naturalSpline(q),velocity=naturalSpline([0,...this.bridgeV.subarray(e*beads,(e+1)*beads),0]);
      const center=t=>{const deviation=wave(t)-((1-t)*q[0]+t*q[q.length-1]);return add(add(add(scale(a,1-t),scale(b,t)),[0,4*t*(1-t)*edge.arch,0]),scale(add([0,.8,0],scale(horizontal,.35)),deviation));};
      const vertices=this.bridges[e].mesh.vertices,tex=new Float32Array(2*81*4);
      for(let i=0;i<=80;i++){
        const t=i/80,c=center(t),tangent=unit(sub(center(Math.min(1,t+.001)),center(Math.max(0,t-.001))));
        const up=unit(cross(tangent,horizontal)),turn=edge.twist*Math.PI*t+.23*Math.tanh(velocity(t));const across=add(scale(up,Math.cos(turn)),scale(cross(tangent,up),Math.sin(turn))),normal=unit(cross(across,tangent));
        const width=.068*Math.max(0,this.gates[e])**.7*(.55+.45*Math.sin(Math.PI*t)**.65);
        for(let x=0;x<3;x++){const k=(i*3+x)*8,p=add(c,scale(across,width*(x-1)));vertices.set(p,k);vertices.set(normal,k+3);}
        const f=[wave(t)-((1-t)*q[0]+t*q[q.length-1]),0,velocity(t)**2,velocity(t)];tex.set(f,i*8);tex.set(f,i*8+4);
      }
      gl.bindBuffer(gl.ARRAY_BUFFER,this.bridges[e].mesh.vbo);gl.bufferSubData(gl.ARRAY_BUFFER,0,vertices);gl.bindTexture(gl.TEXTURE_2D,this.bridges[e].texture);gl.texSubImage2D(gl.TEXTURE_2D,0,0,0,2,81,gl.RGBA,gl.FLOAT,tex);
    });
  }
  reset(){const c=this.scene.camera,p=sub(c.position,c.target);this.distance=Math.hypot(...p);this.yaw=Math.atan2(p[0],p[2]);this.pitch=Math.asin(p[1]/this.distance);this.target=[...c.target];this.requestDraw();}
  resizeCanvas(){const c=this.canvas,w0=c.clientWidth,h0=c.clientHeight;if(!w0||!h0)return;const ratio=Math.min(devicePixelRatio||1,1.5,1500/Math.max(w0,h0)),w=Math.max(1,Math.round(w0*ratio)),h=Math.max(1,Math.round(h0*ratio));if(c.width!==w||c.height!==h){c.width=w;c.height=h;}}
  camera(){const eye=add(this.target,[this.distance*Math.cos(this.pitch)*Math.sin(this.yaw),this.distance*Math.sin(this.pitch),this.distance*Math.cos(this.pitch)*Math.cos(this.yaw)]);const aspect=this.canvas.width/this.canvas.height;const focal=this.scene.camera.focal_length*Math.min(1,aspect/1.65);return {eye,projection:multiply(perspective(focal,aspect),lookAt(eye,this.target))};}
  requestDraw(){if(this.frame||this.lost||document.hidden)return;this.frame=requestAnimationFrame(()=>{this.frame=0;this.draw();});}
  drawObjects(pass,projection,eye){
    const gl=this.gl,u=this.uniform;gl.useProgram(this.program);gl.uniformMatrix4fv(u.viewProjection,false,projection);gl.uniformMatrix4fv(u.lightProjection,false,this.lightProjection);gl.uniform3fv(u.eye,eye);gl.uniform1i(u.fields,0);gl.uniform1i(u.shadowMap,1);gl.uniform1i(u.pass,pass);
    gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,pass===1?this.emptyTexture:this.shadowTexture);gl.activeTexture(gl.TEXTURE0);
    const draw=(mesh,texture,model,kind)=>{gl.bindVertexArray(mesh.vao);gl.bindTexture(gl.TEXTURE_2D,texture);gl.uniformMatrix4fv(u.model,false,model);gl.uniform1i(u.kind,kind);gl.drawElements(gl.TRIANGLES,mesh.count,gl.UNSIGNED_INT,0);};
    this.scene.bodies.forEach((body,i)=>{const shape=this.scene.shapes[body.shape];gl.uniform4f(u.shape,shape.opening,shape.flare,shape.height,shape.pleats);gl.uniform3f(u.shape2,shape.twist,shape.thickness,shape.deformation);gl.uniform1f(u.opening,shape.opening);gl.uniform1i(u.bodyId,i);gl.uniform1i(u.selected,i===this.selected);draw(this.bodyMesh,this.bodyTextures[i],this.models[i],0);});
    this.bridges.forEach((bridge,i)=>{if(this.gates[i]>.005)draw(bridge.mesh,bridge.texture,identity(),1);});
    if(pass!==1)draw(this.floorMesh,this.emptyTexture,identity(),2);
  }
  draw(){
    if(this.lost)return;this.resizeCanvas();const gl=this.gl,c=this.canvas,view=this.camera();gl.enable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE);gl.disable(gl.BLEND);
    if(this.shadowDirty){gl.bindFramebuffer(gl.FRAMEBUFFER,this.shadowBuffer);gl.viewport(0,0,1024,1024);gl.clear(gl.DEPTH_BUFFER_BIT);this.drawObjects(1,this.lightProjection,[-8,12,9]);this.shadowDirty=false;}
    gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.viewport(0,0,c.width,c.height);gl.clearColor(.875,.866,.849,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);this.drawObjects(0,view.projection,view.eye);
    this.callbacks.draw?.(view.projection,c.width,c.height);
  }
  pick(clientX,clientY){
    if(this.lost)return null;this.resizeCanvas();const gl=this.gl,c=this.canvas,rect=c.getBoundingClientRect();
    if(this.pickWidth!==c.width||this.pickHeight!==c.height){gl.bindTexture(gl.TEXTURE_2D,this.pickTexture);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA8,c.width,c.height,0,gl.RGBA,gl.UNSIGNED_BYTE,null);gl.bindRenderbuffer(gl.RENDERBUFFER,this.pickDepth);gl.renderbufferStorage(gl.RENDERBUFFER,gl.DEPTH_COMPONENT16,c.width,c.height);this.pickWidth=c.width;this.pickHeight=c.height;}
    gl.bindFramebuffer(gl.FRAMEBUFFER,this.pickBuffer);gl.viewport(0,0,c.width,c.height);gl.disable(gl.BLEND);gl.disable(gl.DITHER);gl.enable(gl.DEPTH_TEST);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);const view=this.camera();this.drawObjects(2,view.projection,view.eye);
    const pixel=new Uint8Array(4),x=Math.max(0,Math.min(c.width-1,Math.floor((clientX-rect.left)/rect.width*c.width))),y=Math.max(0,Math.min(c.height-1,Math.floor((rect.bottom-clientY)/rect.height*c.height)));
    gl.readPixels(x,y,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);gl.enable(gl.DITHER);gl.bindFramebuffer(gl.FRAMEBUFFER,null);return pixel[0]>0&&pixel[0]<=7?{body:pixel[0]-1,x:Math.min(.999999,pixel[1]/255),y:Math.min(.999999,pixel[2]/255)}:null;
  }
  bindInput(){
    const c=this.canvas,o={signal:this.events.signal};
    const limit=()=>{this.pitch=Math.max(-.3,Math.min(1.45,this.pitch));this.distance=Math.max(7,Math.min(28,this.distance));this.requestDraw();};
    c.addEventListener('pointerdown',e=>{c.setPointerCapture(e.pointerId);c.focus();const hit=this.mode==='touch'&&!e.altKey?this.pick(e.clientX,e.clientY):null;this.pointers.set(e.pointerId,{x:e.clientX,y:e.clientY,touch:hit!==null});if(this.pointers.size>1){this.callbacks.release?.();for(const p of this.pointers.values())p.touch=false;}else if(hit){this.selected=hit.body;this.callbacks.touch?.(hit,e);}},o);
    c.addEventListener('pointermove',e=>{const prev=this.pointers.get(e.pointerId);if(!prev)return;if(this.pointers.size>1){const other=[...this.pointers.entries()].find(([id])=>id!==e.pointerId)[1];const before=Math.hypot(prev.x-other.x,prev.y-other.y),after=Math.hypot(e.clientX-other.x,e.clientY-other.y);if(before>1&&after>1)this.distance*=before/after;this.yaw-=(e.clientX-prev.x)*.003;this.pitch+=(e.clientY-prev.y)*.003;}else if(prev.touch){const hit=this.pick(e.clientX,e.clientY);if(hit)this.callbacks.touch?.(hit,e);else this.callbacks.release?.();}else{this.yaw-=(e.clientX-prev.x)*.006;this.pitch+=(e.clientY-prev.y)*.006;}prev.x=e.clientX;prev.y=e.clientY;limit();},o);
    for(const name of ['pointerup','pointercancel','lostpointercapture'])c.addEventListener(name,e=>{const previous=this.pointers.get(e.pointerId);this.pointers.delete(e.pointerId);if(previous?.touch)this.callbacks.release?.();},o);
    c.addEventListener('wheel',e=>{e.preventDefault();this.distance*=Math.exp(Math.max(-150,Math.min(150,e.deltaY))*.0015);limit();},{...o,passive:false});
    c.addEventListener('keydown',e=>{const actions={ArrowLeft:()=>this.yaw-=.1,ArrowRight:()=>this.yaw+=.1,ArrowUp:()=>this.pitch+=.1,ArrowDown:()=>this.pitch-=.1,'+':()=>this.distance*=.9,'=':()=>this.distance*=.9,'-':()=>this.distance*=1.1,Home:()=>this.reset()};if(actions[e.key]){e.preventDefault();actions[e.key]();limit();}},o);
  }
  dispose(){this.events.abort();this.resize?.disconnect();cancelAnimationFrame(this.frame);if(!this.lost)for(const [kind,value]of this.resources)this.gl['delete'+kind](value);this.resources=[];}
}
