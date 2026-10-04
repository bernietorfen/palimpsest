// Original live projection of the same twice-rolled sheet used in the film.
// One field texture, one mesh, one shadow texture. No frame accumulation.
const geometry = `
const float PI=3.14159265359;
uniform sampler2D fields;
vec4 field(vec2 q){
  vec2 size=vec2(textureSize(fields,0));
  vec2 p=fract(q)*size, f=fract(p); ivec2 base=ivec2(floor(p));
  ivec2 n=textureSize(fields,0);
  ivec2 a=(base%n+n)%n, b=((base+ivec2(1))%n+n)%n;
  return mix(mix(texelFetch(fields,a,0),texelFetch(fields,ivec2(b.x,a.y),0),f.x),
             mix(texelFetch(fields,ivec2(a.x,b.y),0),texelFetch(fields,b,0),f.x),f.y);
}
vec3 point(vec2 q){
  float s=q.x*2.0-1.0, phi=-PI+q.y*4.0*PI;
  float x=s*(1.34+.055*sin(2.0*phi)), theta=x*2.0*PI/2.8;
  vec4 f=field(vec2(x/2.8+.5,q.y+.25));
  float r=.55+.072*phi+.048*sin(3.0*phi+theta)+.038*cos(4.0*theta+phi)
    +.085*tanh(1.6*f.x)+.13*tanh(2.1*f.y);
  return vec3(x,.22*sin(1.8*x)+r*sin(phi),.13*sin(2.2*x+.4)+r*cos(phi))*.71;
}
vec2 coordinates(vec2 q){
  float phi=-PI+q.y*4.0*PI;
  float x=(q.x*2.0-1.0)*(1.34+.055*sin(2.0*phi));
  return vec2(x/2.8+.5,q.y+.25);
}
bool openWindow(vec2 chart){
  vec4 f=field(chart);
  float theta=(chart.x-.5)*2.0*PI, phi=(chart.y-.5)*4.0*PI;
  float threshold=.56+.30*sin(2.0*theta+4.0*phi)+.16*cos(5.0*theta-phi);
  return f.z>threshold;
}
`;
const vertex = `#version 300 es
precision highp float;
layout(location=0) in vec2 coordinate;
uniform mat4 viewProjection;
uniform mat4 lightProjection;
out vec3 world;
out vec3 surfaceNormal;
out vec2 chart;
out vec4 lightPosition;
${geometry}
void main(){
  world=point(coordinate); chart=coordinates(coordinate);
  float e=.001;
  vec3 dx=point(coordinate+vec2(e,0))-point(coordinate-vec2(e,0));
  vec3 dy=point(coordinate+vec2(0,e))-point(coordinate-vec2(0,e));
  surfaceNormal=normalize(cross(dx,dy));
  lightPosition=lightProjection*vec4(world,1.0);
  gl_Position=viewProjection*vec4(world,1.0);
}`;
const fragment = `#version 300 es
precision highp float;
in vec3 world;
in vec3 surfaceNormal;
in vec2 chart;
in vec4 lightPosition;
uniform sampler2D shadowMap;
uniform vec3 eye;
uniform bool shadowPass;
out vec4 color;
${geometry}
vec3 linearize(vec3 c){return pow(c,vec3(2.2));}
float shadow(vec3 n,vec3 l){
  vec3 q=lightPosition.xyz/lightPosition.w*.5+.5;
  if(any(lessThan(q,vec3(0)))||any(greaterThan(q,vec3(1)))) return 1.0;
  float result=0.0, bias=.0013+.001*(1.0-abs(dot(n,l)));
  vec2 step=1.0/vec2(textureSize(shadowMap,0));
  for(int y=-1;y<=1;y++) for(int x=-1;x<=1;x++) {
    result+=q.z-bias<=texture(shadowMap,q.xy+vec2(x,y)*step).r?1.0:0.0;
  }
  return result/9.0;
}
void main(){
  if(openWindow(chart)) discard;
  if(shadowPass){color=vec4(1);return;}
  vec4 f=field(chart);
  vec3 n=normalize(surfaceNormal)*(gl_FrontFacing?1.0:-1.0);
  vec3 v=normalize(eye-world), l=normalize(vec3(-3,5,4)), fill=normalize(vec3(4,1,-2));
  float ink=smoothstep(.07,.29,abs(f.y))*.89;
  vec3 paper=vec3(.89,.855,.75), pigment=vec3(.12,.23,.245);
  vec3 albedo=mix(paper,pigment,ink);
  float contour=abs(fract(f.y*14.0+.5)-.5);
  float line=1.0-smoothstep(.035,.09,contour);
  albedo=mix(albedo,vec3(.73,.48,.21),line*smoothstep(.02,.075,abs(f.y))*.65);
  float visibility=shadow(n,l), diffuse=max(dot(n,l),0.0), fillLight=max(dot(n,fill),0.0);
  vec3 lit=linearize(albedo)*(vec3(.19,.22,.23)+vec3(1.45,1.26,.95)*diffuse*visibility+vec3(.23,.33,.39)*fillLight);
  float rim=pow(1.0-abs(dot(n,v)),3.0);
  lit+=vec3(.24,.22,.17)*rim*.3;
  vec3 mapped=lit/(lit+vec3(.55));
  color=vec4(pow(mapped,vec3(1.0/2.2)),1);
}`;

const normalize=a=>{const n=Math.hypot(...a);return a.map(v=>v/n);};
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
function lookAt(eye){
  const z=normalize(eye),x=normalize(cross([0,1,0],z)),y=cross(z,x);
  const dot=a=>a.reduce((s,v,i)=>s+v*eye[i],0);
  return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x),-dot(y),-dot(z),1]);
}
function multiply(a,b){
  const out=new Float32Array(16);
  for(let col=0;col<4;col++) for(let row=0;row<4;row++) for(let k=0;k<4;k++) out[col*4+row]+=a[k*4+row]*b[col*4+k];
  return out;
}
function perspective(aspect){
  const f=1/Math.tan(36*Math.PI/360),near=.1,far=30;
  return new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,(far+near)/(near-far),-1,0,0,2*far*near/(near-far),0]);
}

export class LiveRenderer {
  constructor(canvas,onLost){
    this.canvas=canvas;
    this.gl=canvas.getContext('webgl2',{alpha:false,antialias:true,powerPreference:'low-power'});
    if(!this.gl) throw new Error('This browser cannot show the live sculpture. The film and atlas remain available.');
    this.resources=[];this.events=new AbortController();this.pointers=new Map();this.frame=0;
    const gl=this.gl;
    this.program=this.makeProgram(vertex,fragment);
    this.uniforms=Object.fromEntries(['fields','shadowMap','viewProjection','lightProjection','shadowPass','eye'].map(n=>[n,gl.getUniformLocation(this.program,n)]));
    this.vao=this.own('VertexArray',gl.createVertexArray());gl.bindVertexArray(this.vao);
    const nx=112,ny=224,coords=new Float32Array((nx+1)*(ny+1)*2),indices=new Uint32Array(nx*ny*6);
    for(let y=0;y<=ny;y++)for(let x=0;x<=nx;x++){const k=(y*(nx+1)+x)*2;coords[k]=x/nx;coords[k+1]=y/ny;}
    let k=0;
    for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){const a=y*(nx+1)+x,b=a+1,c=a+nx+1,d=c+1;indices.set([a,b,c,b,d,c],k);k+=6;}
    this.count=indices.length;
    gl.bindBuffer(gl.ARRAY_BUFFER,this.own('Buffer',gl.createBuffer()));gl.bufferData(gl.ARRAY_BUFFER,coords,gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,2,gl.FLOAT,false,0,0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,this.own('Buffer',gl.createBuffer()));gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,indices,gl.STATIC_DRAW);
    this.fieldTexture=this.texture(64,gl.RGBA32F,gl.RGBA,gl.FLOAT,new Float32Array(64*64*4));
    this.shadowSize=1024;
    this.shadowTexture=this.texture(this.shadowSize,gl.DEPTH_COMPONENT24,gl.DEPTH_COMPONENT,gl.UNSIGNED_INT,null);
    this.shadowBuffer=this.own('Framebuffer',gl.createFramebuffer());gl.bindFramebuffer(gl.FRAMEBUFFER,this.shadowBuffer);
    gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.TEXTURE_2D,this.shadowTexture,0);gl.drawBuffers([gl.NONE]);gl.readBuffer(gl.NONE);
    if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw new Error('The live sculpture could not initialize its light');
    const r=1.65,near=.1,far=14;
    this.lightProjection=multiply(new Float32Array([1/r,0,0,0,0,1/r,0,0,0,0,-2/(far-near),0,0,0,-(far+near)/(far-near),1]),lookAt([-3,5,4]));
    this.shadowDirty=true;this.reset();
    this.resize=new ResizeObserver(()=>this.requestDraw());this.resize.observe(canvas);
    this.bindInput();
    canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();this.lost=true;onLost();},{signal:this.events.signal});
    canvas.dataset.state='ready';
  }

  own(kind,value){this.resources.push([kind,value]);return value;}
  makeProgram(v,f){
    const gl=this.gl,p=this.own('Program',gl.createProgram());
    for(const [type,source]of[[gl.VERTEX_SHADER,v],[gl.FRAGMENT_SHADER,f]]){
      const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);
      if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS)){const info=gl.getShaderInfoLog(shader);gl.deleteShader(shader);throw new Error(info);}
      gl.attachShader(p,shader);gl.deleteShader(shader);
    }
    gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p));return p;
  }
  texture(size,internal,format,type,data){
    const gl=this.gl,t=this.own('Texture',gl.createTexture());gl.bindTexture(gl.TEXTURE_2D,t);
    gl.texImage2D(gl.TEXTURE_2D,0,internal,size,size,0,format,type,data);
    for(const name of [gl.TEXTURE_MIN_FILTER,gl.TEXTURE_MAG_FILTER])gl.texParameteri(gl.TEXTURE_2D,name,gl.NEAREST);
    for(const name of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T])gl.texParameteri(gl.TEXTURE_2D,name,gl.CLAMP_TO_EDGE);
    return t;
  }
  update(fields){
    if(this.lost)return;
    const gl=this.gl;gl.bindTexture(gl.TEXTURE_2D,this.fieldTexture);
    gl.texSubImage2D(gl.TEXTURE_2D,0,0,0,64,64,gl.RGBA,gl.FLOAT,fields);
    this.shadowDirty=true;this.requestDraw();
  }
  reset(){this.yaw=.61;this.pitch=.22;this.distance=4.5;this.requestDraw();}
  requestDraw(){if(this.frame||this.lost||document.hidden)return;this.frame=requestAnimationFrame(()=>{this.frame=0;this.draw();});}
  draw(){
    if(this.lost)return;
    const gl=this.gl,c=this.canvas,w0=c.clientWidth,h0=c.clientHeight;if(!w0||!h0)return;
    const ratio=Math.min(devicePixelRatio||1,1.5,1500/Math.max(w0,h0));
    const w=Math.max(1,Math.round(w0*ratio)),h=Math.max(1,Math.round(h0*ratio));
    if(c.width!==w||c.height!==h){c.width=w;c.height=h;}
    gl.useProgram(this.program);gl.bindVertexArray(this.vao);gl.enable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE);
    gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,this.fieldTexture);gl.uniform1i(this.uniforms.fields,0);
    gl.uniformMatrix4fv(this.uniforms.lightProjection,false,this.lightProjection);
    if(this.shadowDirty){
      // Never bind the depth attachment as an input while drawing into it.
      gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,this.fieldTexture);gl.uniform1i(this.uniforms.shadowMap,1);
      gl.bindFramebuffer(gl.FRAMEBUFFER,this.shadowBuffer);gl.viewport(0,0,this.shadowSize,this.shadowSize);gl.clear(gl.DEPTH_BUFFER_BIT);
      gl.uniform1i(this.uniforms.shadowPass,1);gl.uniformMatrix4fv(this.uniforms.viewProjection,false,this.lightProjection);
      gl.drawElements(gl.TRIANGLES,this.count,gl.UNSIGNED_INT,0);this.shadowDirty=false;
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.viewport(0,0,w,h);gl.clearColor(11/255,16/255,19/255,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
    const eye=[this.distance*Math.cos(this.pitch)*Math.sin(this.yaw),this.distance*Math.sin(this.pitch),this.distance*Math.cos(this.pitch)*Math.cos(this.yaw)];
    gl.uniformMatrix4fv(this.uniforms.viewProjection,false,multiply(perspective(w/h),lookAt(eye)));gl.uniform3fv(this.uniforms.eye,eye);gl.uniform1i(this.uniforms.shadowPass,0);
    gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,this.shadowTexture);gl.uniform1i(this.uniforms.shadowMap,1);
    gl.drawElements(gl.TRIANGLES,this.count,gl.UNSIGNED_INT,0);
  }
  bindInput(){
    const c=this.canvas,o={signal:this.events.signal};
    const limit=()=>{this.pitch=Math.max(-1.4,Math.min(1.4,this.pitch));this.distance=Math.max(2.7,Math.min(8,this.distance));this.requestDraw();};
    c.addEventListener('pointerdown',e=>{c.setPointerCapture(e.pointerId);this.pointers.set(e.pointerId,[e.clientX,e.clientY]);c.focus();},o);
    c.addEventListener('pointermove',e=>{const prev=this.pointers.get(e.pointerId);if(!prev)return;const now=[e.clientX,e.clientY];
      if(this.pointers.size===1){this.yaw-=(now[0]-prev[0])*.006;this.pitch+=(now[1]-prev[1])*.006;}
      else{const other=[...this.pointers.entries()].find(([id])=>id!==e.pointerId)[1];const before=Math.hypot(prev[0]-other[0],prev[1]-other[1]),after=Math.hypot(now[0]-other[0],now[1]-other[1]);if(before>1&&after>1)this.distance*=before/after;}
      this.pointers.set(e.pointerId,now);limit();},o);
    for(const name of ['pointerup','pointercancel','lostpointercapture'])c.addEventListener(name,e=>this.pointers.delete(e.pointerId),o);
    c.addEventListener('wheel',e=>{e.preventDefault();this.distance*=Math.exp(Math.max(-150,Math.min(150,e.deltaY))*.0015);limit();},{...o,passive:false});
    c.addEventListener('keydown',e=>{const actions={ArrowLeft:()=>this.yaw-=.1,ArrowRight:()=>this.yaw+=.1,ArrowUp:()=>this.pitch+=.1,ArrowDown:()=>this.pitch-=.1,'+':()=>this.distance*=.9,'=':()=>this.distance*=.9,'-':()=>this.distance*=1.1,Home:()=>this.reset()};if(actions[e.key]){e.preventDefault();actions[e.key]();limit();}},o);
  }
  dispose(){this.events.abort();this.resize.disconnect();cancelAnimationFrame(this.frame);for(const [kind,value]of this.resources.reverse())this.gl[`delete${kind}`](value);this.resources=[];this.lost=true;}
}
