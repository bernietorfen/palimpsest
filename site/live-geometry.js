// Closed geometry for a visitor's own material. Coordinates and aperture rules
// are the authored sheet used by PALIMPSEST; all cut edges receive a wall.
export function sampleField(fields,size,u,v){
  const x=((u%1+1)%1)*size,y=((v%1+1)%1)*size;
  const ix=Math.floor(x),iy=Math.floor(y),fx=x-ix,fy=y-iy;
  const a=(iy*size+ix)*4,b=(iy*size+(ix+1)%size)*4;
  const c=(((iy+1)%size)*size+ix)*4,d=(((iy+1)%size)*size+(ix+1)%size)*4;
  const values=new Float64Array(4);
  for(let k=0;k<4;k++)values[k]=(fields[a+k]*(1-fx)+fields[b+k]*fx)*(1-fy)+(fields[c+k]*(1-fx)+fields[d+k]*fx)*fy;
  return values;
}
export function chartAt(s,phi){
  const x=s*(1.34+.055*Math.sin(2*phi));
  return{x,theta:x*2*Math.PI/2.8,phi,u:x/2.8+.5,v:phi/(4*Math.PI)+.5};
}
export function pointAt(s,phi,fields,size,side=0){
  const q=chartAt(s,phi),f=sampleField(fields,size,q.u,q.v);
  const r=.55+.072*phi+.048*Math.sin(3*phi+q.theta)+.038*Math.cos(4*q.theta+phi)
    +.085*Math.tanh(f[0]*1.6)+.13*Math.tanh(f[1]*2.1)+side*.013;
  return[q.x,.22*Math.sin(1.8*q.x)+r*Math.sin(phi),.13*Math.sin(2.2*q.x+.4)+r*Math.cos(phi)];
}
export function windowAt(s,phi,fields,size){
  const q=chartAt(s,phi),f=sampleField(fields,size,q.u,q.v);
  return f[2]-.56-.30*Math.sin(2*q.theta+4*phi)-.16*Math.cos(5*q.theta-phi);
}
export function buildLiveSheet(fields,size=64,nu=96,nv=192){
  if(fields.length!==size*size*4||![32,64,128].includes(size)||nu<8||nv<8||nu>192||nv>384)throw new Error('Unsupported live sculpture grid');
  for(const value of fields)if(!Number.isFinite(value))throw new Error('The material contains a non-finite field');
  const parameters=[],values=[],front=[],intersections=new Map(),baseCount=nu*nv;
  for(let y=0;y<nv;y++)for(let x=0;x<nu;x++){
    const s=-1+2*x/(nu-1),phi=-Math.PI+4*Math.PI*y/(nv-1);
    parameters.push([s,phi]);values.push(windowAt(s,phi,fields,size));
  }
  const intersection=(a,b)=>{
    if(values[a]===0)return a;if(values[b]===0)return b;
    const lo=Math.min(a,b),hi=Math.max(a,b),key=lo*baseCount+hi;
    if(intersections.has(key))return intersections.get(key);
    const fraction=values[lo]/(values[lo]-values[hi]);
    const p=parameters[lo],q=parameters[hi],index=parameters.length;
    parameters.push([p[0]*(1-fraction)+q[0]*fraction,p[1]*(1-fraction)+q[1]*fraction]);
    intersections.set(key,index);return index;
  };
  const clip=(a,b,c)=>{
    const input=[a,b,c],polygon=[];
    for(let i=0;i<3;i++){
      const start=input[i],end=input[(i+1)%3],inside=values[start]<=0,nextInside=values[end]<=0;
      if(inside)polygon.push(start);
      if(inside!==nextInside)polygon.push(intersection(start,end));
    }
    const unique=polygon.filter((v,i)=>v!==polygon[(i+polygon.length-1)%polygon.length]);
    for(let i=1;i<unique.length-1;i++)front.push([unique[0],unique[i],unique[i+1]]);
  };
  for(let y=0;y<nv-1;y++)for(let x=0;x<nu-1;x++){
    const a=y*nu+x,b=a+1,c=a+nu,d=c+1;clip(a,b,c);clip(b,d,c);
  }
  if(!front.length)throw new Error('This material has no remaining surface at the export resolution');
  const used=new Map();
  for(const triangle of front)for(const vertex of triangle)if(!used.has(vertex))used.set(vertex,used.size);
  const count=used.size,positions=new Float64Array(count*6),triangles=[],edges=new Map();
  for(const [original,index]of used){
    const [s,phi]=parameters[original];positions.set(pointAt(s,phi,fields,size,1),index*3);positions.set(pointAt(s,phi,fields,size,-1),(index+count)*3);
  }
  for(const triangle of front){
    const face=triangle.map(index=>used.get(index));triangles.push(face);
    for(let i=0;i<3;i++){
      const a=face[i],b=face[(i+1)%3],key=Math.min(a,b)*count+Math.max(a,b),edge=edges.get(key);
      if(edge){edge.count++;if(edge.count>2)throw new Error('The clipped chart has a nonmanifold edge');}
      else edges.set(key,{a,b,count:1});
    }
  }
  for(const triangle of front){const[a,b,c]=triangle.map(index=>used.get(index));triangles.push([c+count,b+count,a+count]);}
  let boundary=0;
  for(const edge of edges.values())if(edge.count===1){const{a,b}=edge;triangles.push([b,a,a+count],[b,a+count,b+count]);boundary++;}
  return{positions,triangles:new Uint32Array(triangles.flat()),stats:{nu,nv,vertices:count*2,triangles:triangles.length,boundary_segments:boundary}};
}

export function sculptureSTL(mesh,time=0){
  const {positions,triangles}=mesh,min=[Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity];
  for(let i=0;i<positions.length;i++){
    const axis=i%3;min[axis]=Math.min(min[axis],positions[i]);max[axis]=Math.max(max[axis],positions[i]);
  }
  const scale=200/Math.max(...max.map((v,i)=>v-min[i])),center=min.map((v,i)=>(v+max[i])/2);
  const count=triangles.length/3,buffer=new ArrayBuffer(84+count*50),view=new DataView(buffer);
  const header=new TextEncoder().encode(`PALIMPSEST | live material at ${time.toFixed(3)} s | millimeters | Codex 2026`);
  new Uint8Array(buffer,0,80).set(header.subarray(0,80));view.setUint32(80,count,true);
  let minimumArea=Infinity;
  for(let t=0;t<count;t++){
    const points=[];
    for(let v=0;v<3;v++){const index=triangles[t*3+v]*3;points.push([0,1,2].map(axis=>Math.fround((positions[index+axis]-center[axis])*scale)));}
    const a=points[1].map((v,i)=>v-points[0][i]),b=points[2].map((v,i)=>v-points[0][i]);
    const cross=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],length=Math.hypot(...cross);
    minimumArea=Math.min(minimumArea,length/2);
    if(!Number.isFinite(length)||length<1e-12)throw new Error('The sculpture contains a degenerate face');
    const offset=84+t*50;
    for(let axis=0;axis<3;axis++)view.setFloat32(offset+axis*4,cross[axis]/length,true);
    for(let v=0;v<3;v++)for(let axis=0;axis<3;axis++)view.setFloat32(offset+12+(v*3+axis)*4,points[v][axis],true);
    view.setUint16(offset+48,0,true);
  }
  return{buffer,stats:{...mesh.stats,bytes:buffer.byteLength,maximum_extent_mm:200,minimum_face_area_mm2:minimumArea,
    scope:'Closed chart-derived geometry. Later states can have separate fragments; physical fabrication and self-intersections are not certified.'}};
}
