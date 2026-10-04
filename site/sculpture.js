// A small, purpose-built WebGL2 viewer for the meshes exported by this work.
// glTF 2.0 is used as an interchange format, not as an imported scene system.
const vertexSource = `#version 300 es
precision highp float;
layout(location=0) in vec3 position;
layout(location=1) in vec3 normal;
layout(location=2) in vec2 uv;
uniform mat4 viewProjection;
uniform mat4 lightProjection;
uniform vec3 center;
uniform float scale;
out vec3 world;
out vec3 surfaceNormal;
out vec2 chart;
out vec4 lightPosition;
void main(){
  world=(position-center)*scale;
  surfaceNormal=normal;
  chart=uv;
  lightPosition=lightProjection*vec4(world,1.0);
  gl_Position=viewProjection*vec4(world,1.0);
}`;

const fragmentSource = `#version 300 es
precision highp float;
in vec3 world;
in vec3 surfaceNormal;
in vec2 chart;
in vec4 lightPosition;
uniform sampler2D pigment;
uniform sampler2D shadowMap;
uniform vec3 eye;
out vec4 fragment;
const float PI=3.14159265359;
vec3 linearize(vec3 c){return mix(c/12.92,pow((c+.055)/1.055,vec3(2.4)),step(vec3(.04045),c));}
vec3 encode(vec3 c){return mix(c*12.92,1.055*pow(c,vec3(1.0/2.4))-.055,step(vec3(.0031308),c));}
vec3 aces(vec3 c){return clamp((c*(2.51*c+.03))/(c*(2.43*c+.59)+.14),0.0,1.0);}
float visibility(vec3 n,vec3 l){
  vec3 q=lightPosition.xyz/lightPosition.w*.5+.5;
  if(any(lessThan(q,vec3(0)))||any(greaterThan(q,vec3(1)))) return 1.0;
  float bias=.00045+.0010*(1.0-max(dot(n,l),0.0));
  vec2 texel=1.0/vec2(textureSize(shadowMap,0));
  float visible=0.0;
  for(int y=-1;y<=1;y++) for(int x=-1;x<=1;x++){
    float depth=texture(shadowMap,q.xy+vec2(x,y)*texel*1.1).r;
    visible+=q.z-bias<=depth?1.0:0.0;
  }
  return visible/9.0;
}
vec3 lamp(vec3 albedo,vec3 n,vec3 v,vec3 l,vec3 color){
  vec3 h=normalize(v+l);
  float nl=max(dot(n,l),0.0),nv=max(dot(n,v),.001);
  float nh=max(dot(n,h),0.0),vh=max(dot(v,h),0.0);
  float a=.68*.68,a2=a*a;
  float den=nh*nh*(a2-1.0)+1.0;
  float d=a2/(PI*den*den);
  float k=(.68+1.0)*(.68+1.0)/8.0;
  float g=nv/(nv*(1.0-k)+k)*nl/(nl*(1.0-k)+k);
  vec3 f0=mix(vec3(.04),albedo,.025);
  vec3 f=f0+(1.0-f0)*pow(1.0-vh,5.0);
  vec3 spec=d*g*f/max(4.0*nv*nl,.0001);
  return ((1.0-f)*albedo*.975/PI+spec)*color*nl;
}
void main(){
  vec3 n=normalize(surfaceNormal),v=normalize(eye-world);
  vec3 albedo=linearize(texture(pigment,chart).rgb);
  vec3 key=normalize(vec3(-3.0,5.0,4.0));
  vec3 fill=normalize(vec3(4.0,1.0,-2.0));
  vec3 color=albedo*(.07+.10*max(n.y,0.0));
  color+=lamp(albedo,n,v,key,vec3(3.1,2.85,2.42))*visibility(n,key);
  color+=lamp(albedo,n,v,fill,vec3(.50,.68,.77));
  fragment=vec4(encode(aces(color*.95)),1.0);
}`;

const depthVertex = `#version 300 es
precision highp float;
layout(location=0) in vec3 position;
uniform mat4 lightProjection;
uniform vec3 center;
uniform float scale;
void main(){gl_Position=lightProjection*vec4((position-center)*scale,1.0);}`;
const depthFragment = `#version 300 es
precision highp float;
void main(){}`;

function normalize(v) { const length = Math.hypot(...v); return v.map((x) => x / length); }
function cross(a, b) { return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]; }
function dot(a, b) { return a.reduce((sum, value, i) => sum + value*b[i], 0); }
function lookAt(eye) {
  const z = normalize(eye), x = normalize(cross([0, 1, 0], z)), y = cross(z, x);
  return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);
}
function multiply(a, b) {
  const result = new Float32Array(16);
  for (let col = 0; col < 4; col++) for (let row = 0; row < 4; row++) {
    for (let k = 0; k < 4; k++) result[col*4+row] += a[k*4+row]*b[col*4+k];
  }
  return result;
}
function perspective(aspect) {
  const f = 1/Math.tan(36*Math.PI/360), near = .1, far = 30;
  return new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,(far+near)/(near-far),-1,0,0,2*far*near/(near-far),0]);
}
function orthographic(radius, near, far) {
  return new Float32Array([1/radius,0,0,0,0,1/radius,0,0,0,0,-2/(far-near),0,0,0,-(far+near)/(far-near),1]);
}

function parseGLB(buffer) {
  const data = new DataView(buffer);
  if (data.byteLength < 20 || data.getUint32(0,true) !== 0x46546c67 || data.getUint32(4,true) !== 2 || data.getUint32(8,true) !== buffer.byteLength) {
    throw new Error('Invalid glTF binary');
  }
  let document, binary;
  for (let offset = 12; offset < buffer.byteLength;) {
    const size = data.getUint32(offset,true), kind = data.getUint32(offset+4,true);
    offset += 8;
    if (offset + size > buffer.byteLength) throw new Error('Invalid glTF chunk');
    if (kind === 0x4e4f534a) document = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer,offset,size)));
    if (kind === 0x004e4942) binary = buffer.slice(offset,offset+size);
    offset += size;
  }
  if (!document || !binary || document.extensionsRequired?.length) throw new Error('Unsupported sculpture encoding');
  // Exported PALIMPSEST states have one mesh, one primitive and baked transforms.
  if (document.meshes.length !== 1 || document.meshes[0].primitives.length !== 1) throw new Error('Unexpected sculpture structure');
  if (document.nodes.some((node) => node.matrix || node.translation || node.rotation || node.scale)) throw new Error('Sculpture transforms must be baked');
  return { document, binary, primitive: document.meshes[0].primitives[0] };
}

export class SculptureViewer {
  constructor(canvas, {background=[11/255,16/255,19/255],distance=4.25,responsiveFit=false}={}) {
    this.canvas = canvas;
    this.background = background;
    this.defaultDistance = distance;
    this.responsiveFit = responsiveFit;
    this.gl = canvas.getContext('webgl2', { alpha:false, antialias:true, powerPreference:'low-power', preserveDrawingBuffer:false });
    if (!this.gl) throw new Error('WebGL2 unavailable');
    this.resources = [];
    this.events = new AbortController();
    this.disposed = false;
    this.loaded = false;
    this.frame = 0;
    this.pointers = new Map();
    this.program = this.programFrom(vertexSource,fragmentSource);
    this.depthProgram = this.programFrom(depthVertex,depthFragment);
    this.lightProjection = multiply(orthographic(1.7,.1,14),lookAt([-3,5,4]));
    this.resizeObserver = new ResizeObserver(() => this.requestDraw());
    this.resizeObserver.observe(canvas);
    this.bindInput();
    this.reset();
  }

  own(kind, value) { this.resources.push([kind,value]); return value; }

  programFrom(vertex, fragment) {
    const gl = this.gl, program = this.own('Program',gl.createProgram());
    for (const [type, source] of [[gl.VERTEX_SHADER,vertex],[gl.FRAGMENT_SHADER,fragment]]) {
      const shader = gl.createShader(type);
      gl.shaderSource(shader,source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) {
        const error = gl.getShaderInfoLog(shader);
        gl.deleteShader(shader);
        throw new Error(`Sculpture shader: ${error}`);
      }
      gl.attachShader(program,shader);
      gl.deleteShader(shader);
    }
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    return program;
  }

  async load(url, signal) {
    const response = await fetch(url,{signal});
    if (!response.ok) throw new Error('Sculpture download failed');
    const parsed = parseGLB(await response.arrayBuffer());
    if (this.disposed || signal.aborted) throw new DOMException('Closed','AbortError');
    const {document: doc,binary,primitive} = parsed;
    if ((primitive.mode ?? 4) !== 4) throw new Error('Expected triangles');
    const position = doc.accessors[primitive.attributes.POSITION];
    if (!position.min || !position.max) throw new Error('Missing sculpture bounds');
    this.center = position.min.map((x,i) => (x+position.max[i])*.5);
    this.scale = 2/Math.max(...position.max.map((x,i) => x-position.min[i]));
    const material = doc.materials[primitive.material];
    const texture = doc.textures[material.pbrMetallicRoughness.baseColorTexture.index];
    const source = doc.images[texture.source];
    const imageView = doc.bufferViews[source.bufferView];
    const bitmap = await createImageBitmap(new Blob([new Uint8Array(binary,imageView.byteOffset || 0,imageView.byteLength)],{type:source.mimeType}));
    if (this.disposed || signal.aborted) { bitmap.close(); throw new DOMException('Closed','AbortError'); }
    const gl = this.gl;
    this.vao = this.own('VertexArray',gl.createVertexArray());
    gl.bindVertexArray(this.vao);
    const buffers = new Map();
    const attribute = (accessorIndex, location, size) => {
      const accessor = doc.accessors[accessorIndex], view = doc.bufferViews[accessor.bufferView];
      if (accessor.sparse || view.buffer !== 0) throw new Error('Unsupported sculpture attribute');
      let buffer = buffers.get(accessor.bufferView);
      if (!buffer) {
        buffer = this.own('Buffer',gl.createBuffer());
        gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
        gl.bufferData(gl.ARRAY_BUFFER,new Uint8Array(binary,view.byteOffset || 0,view.byteLength),gl.STATIC_DRAW);
        buffers.set(accessor.bufferView,buffer);
      } else gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
      gl.enableVertexAttribArray(location);
      gl.vertexAttribPointer(location,size,accessor.componentType,accessor.normalized || false,view.byteStride || 0,accessor.byteOffset || 0);
    };
    attribute(primitive.attributes.POSITION,0,3);
    attribute(primitive.attributes.NORMAL,1,3);
    attribute(primitive.attributes.TEXCOORD_0,2,2);
    const indices = doc.accessors[primitive.indices], indexView = doc.bufferViews[indices.bufferView];
    const indexBuffer = this.own('Buffer',gl.createBuffer());
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,indexBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint8Array(binary,indexView.byteOffset || 0,indexView.byteLength),gl.STATIC_DRAW);
    this.indexCount = indices.count;
    this.indexType = indices.componentType;
    this.indexOffset = indices.byteOffset || 0;
    this.pigment = this.own('Texture',gl.createTexture());
    gl.bindTexture(gl.TEXTURE_2D,this.pigment);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,bitmap);
    bitmap.close();
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    gl.generateMipmap(gl.TEXTURE_2D);
    this.makeShadow();
    this.loaded = true;
    this.canvas.dataset.state = 'ready';
    this.canvas.dataset.triangles = String(this.indexCount/3);
    this.draw();
  }

  use(program) {
    const gl = this.gl;
    gl.useProgram(program);
    gl.uniform3fv(gl.getUniformLocation(program,'center'),this.center);
    gl.uniform1f(gl.getUniformLocation(program,'scale'),this.scale);
    gl.uniformMatrix4fv(gl.getUniformLocation(program,'lightProjection'),false,this.lightProjection);
    gl.bindVertexArray(this.vao);
  }

  triangles() { this.gl.drawElements(this.gl.TRIANGLES,this.indexCount,this.indexType,this.indexOffset); }

  makeShadow() {
    const gl = this.gl, size = Math.min(2048,gl.getParameter(gl.MAX_TEXTURE_SIZE));
    this.shadow = this.own('Texture',gl.createTexture());
    gl.bindTexture(gl.TEXTURE_2D,this.shadow);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.DEPTH_COMPONENT24,size,size,0,gl.DEPTH_COMPONENT,gl.UNSIGNED_INT,null);
    for (const pname of [gl.TEXTURE_MIN_FILTER,gl.TEXTURE_MAG_FILTER]) gl.texParameteri(gl.TEXTURE_2D,pname,gl.NEAREST);
    for (const pname of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T]) gl.texParameteri(gl.TEXTURE_2D,pname,gl.CLAMP_TO_EDGE);
    const framebuffer = this.own('Framebuffer',gl.createFramebuffer());
    gl.bindFramebuffer(gl.FRAMEBUFFER,framebuffer);
    gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.TEXTURE_2D,this.shadow,0);
    gl.drawBuffers([gl.NONE]);
    gl.readBuffer(gl.NONE);
    if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) throw new Error('Shadow framebuffer unavailable');
    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE);
    gl.cullFace(gl.BACK);
    gl.viewport(0,0,size,size);
    gl.clear(gl.DEPTH_BUFFER_BIT);
    this.use(this.depthProgram);
    this.triangles();
    gl.bindFramebuffer(gl.FRAMEBUFFER,null);
  }

  reset() { this.yaw=.61; this.pitch=.22; this.distance=this.defaultDistance; this.requestDraw(); }

  requestDraw() {
    if (this.disposed || this.frame || document.hidden) return;
    this.frame = requestAnimationFrame(() => { this.frame=0; this.draw(); });
  }

  draw() {
    if (!this.loaded || this.disposed) return;
    const gl = this.gl, canvas = this.canvas;
    const width = canvas.clientWidth, height = canvas.clientHeight;
    if (!width || !height) return;
    const ratio = Math.min(window.devicePixelRatio || 1,1.75,1800/Math.max(width,height));
    const w = Math.max(1,Math.round(width*ratio)), h = Math.max(1,Math.round(height*ratio));
    if (canvas.width !== w || canvas.height !== h) { canvas.width=w; canvas.height=h; }
    gl.bindFramebuffer(gl.FRAMEBUFFER,null);
    gl.viewport(0,0,w,h);
    gl.clearColor(...this.background,1);
    gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
    this.use(this.program);
    const distance=this.distance*(this.responsiveFit?Math.max(1,1.25*h/w):1);
    const eye = [distance*Math.cos(this.pitch)*Math.sin(this.yaw),distance*Math.sin(this.pitch),distance*Math.cos(this.pitch)*Math.cos(this.yaw)];
    gl.uniformMatrix4fv(gl.getUniformLocation(this.program,'viewProjection'),false,multiply(perspective(w/h),lookAt(eye)));
    gl.uniform3fv(gl.getUniformLocation(this.program,'eye'),eye);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D,this.pigment);
    gl.uniform1i(gl.getUniformLocation(this.program,'pigment'),0);
    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D,this.shadow);
    gl.uniform1i(gl.getUniformLocation(this.program,'shadowMap'),1);
    this.triangles();
  }

  bindInput() {
    const canvas = this.canvas, options = {signal:this.events.signal};
    const limit = () => { this.pitch=Math.max(-1.4,Math.min(1.4,this.pitch)); this.distance=Math.max(2,Math.min(8,this.distance)); this.requestDraw(); };
    canvas.addEventListener('pointerdown',(event) => { canvas.setPointerCapture(event.pointerId); this.pointers.set(event.pointerId,[event.clientX,event.clientY]); canvas.focus(); },options);
    canvas.addEventListener('pointermove',(event) => {
      const previous = this.pointers.get(event.pointerId);
      if (!previous) return;
      const current = [event.clientX,event.clientY];
      if (this.pointers.size === 1) { this.yaw-=(current[0]-previous[0])*.007; this.pitch+=(current[1]-previous[1])*.007; }
      else {
        const other = [...this.pointers.entries()].find(([id]) => id !== event.pointerId)[1];
        const before = Math.hypot(previous[0]-other[0],previous[1]-other[1]);
        const after = Math.hypot(current[0]-other[0],current[1]-other[1]);
        if (before>1 && after>1) this.distance*=before/after;
      }
      this.pointers.set(event.pointerId,current);
      limit();
    },options);
    for (const eventName of ['pointerup','pointercancel','lostpointercapture']) canvas.addEventListener(eventName,(event) => this.pointers.delete(event.pointerId),options);
    canvas.addEventListener('wheel',(event) => { event.preventDefault(); this.distance*=Math.exp(Math.max(-150,Math.min(150,event.deltaY))*.0015); limit(); },{...options,passive:false});
    canvas.addEventListener('keydown',(event) => {
      const actions = {ArrowLeft:()=>{this.yaw-=.1;},ArrowRight:()=>{this.yaw+=.1;},ArrowUp:()=>{this.pitch+=.1;},ArrowDown:()=>{this.pitch-=.1;},'+':()=>{this.distance*=.9;},'=':()=>{this.distance*=.9;},'-':()=>{this.distance*=1.1;},Home:()=>this.reset()};
      if (actions[event.key]) { event.preventDefault(); actions[event.key](); limit(); }
    },options);
    document.addEventListener('visibilitychange',()=>this.requestDraw(),options);
    canvas.addEventListener('webglcontextlost',(event)=>{ event.preventDefault(); this.loaded=false; this.resources=[]; canvas.dataset.state='context-lost'; },options);
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.events.abort();
    this.resizeObserver.disconnect();
    cancelAnimationFrame(this.frame);
    this.gl.bindVertexArray(null);
    this.gl.bindFramebuffer(this.gl.FRAMEBUFFER,null);
    for (const [kind,resource] of this.resources.reverse()) this.gl[`delete${kind}`](resource);
    this.resources=[];
    this.canvas.dataset.state='closed';
    delete this.canvas.dataset.triangles;
  }
}
