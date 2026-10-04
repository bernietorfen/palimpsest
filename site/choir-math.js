export const add=(a,b)=>a.map((v,i)=>v+b[i]);
export const sub=(a,b)=>a.map((v,i)=>v-b[i]);
export const scale=(a,s)=>a.map(v=>v*s);
export const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
export const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
export const unit=a=>scale(a,1/(Math.hypot(...a)||1));
export const identity=()=>new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);
export function multiply(a,b){const o=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)for(let k=0;k<4;k++)o[c*4+r]+=a[k*4+r]*b[c*4+k];return o;}
export function rotation(a,b,t){const m=identity();m[a*4+a]=m[b*4+b]=Math.cos(t);m[b*4+a]=Math.sin(t);m[a*4+b]=-Math.sin(t);return m;}
export function transform(body){const m=multiply(multiply(rotation(0,2,body.turn),rotation(1,2,body.tilt)),rotation(0,1,body.lean));for(let j=0;j<3;j++)for(let i=0;i<3;i++)m[j*4+i]*=body.scale;for(let i=0;i<3;i++)m[12+i]=body.position[i];return m;}
export function point(m,p){return [0,1,2].map(r=>m[r]*p[0]+m[4+r]*p[1]+m[8+r]*p[2]+m[12+r]);}
export function lookAt(eye,target=[0,0,0]){const z=unit(sub(eye,target)),x=unit(cross([0,1,0],z)),y=cross(z,x);return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);}
export function perspective(f,aspect,near=.05,far=100){return new Float32Array([2*f/aspect,0,0,0,0,2*f,0,0,0,0,-(far+near)/(far-near),-1,0,0,-2*far*near/(far-near),0]);}
export function orthographic(size,near=.1,far=60){const m=identity();m[0]=m[5]=1/size;m[10]=-2/(far-near);m[14]=-(far+near)/(far-near);return m;}
export function fieldSample(field,size,x,y){x=((x%1)+1)%1*size;y=((y%1)+1)%1*size;const a=Math.floor(x),b=Math.floor(y),fx=x-a,fy=y-b;return [0,1,2,3].map(c=>(field[(b*size+a)*4+c]*(1-fx)+field[(b*size+(a+1)%size)*4+c]*fx)*(1-fy)+(field[(((b+1)%size)*size+a)*4+c]*(1-fx)+field[(((b+1)%size)*size+(a+1)%size)*4+c]*fx)*fy);}
export function listenerPoint(s,phi,field,size,shape){const f=fieldSample(field,size,s,phi/(2*Math.PI)+.5),moving=Math.tanh(f[0]*1.8),memory=Math.tanh(f[1]*2.3);const pleat=(.045+.12*Math.max(s,0)**1.5)*Math.sin(shape.pleats*phi+1.6*s);let radius=(.25+1.10*s+.34*s*s+pleat)*shape.flare;radius+=shape.deformation*(.18+.82*s)*(.23*moving+.27*memory);const theta=phi+shape.twist*s+shape.deformation*.24*s*memory;const y=(-.96+2.02*s-.24*s*s)*shape.height+.19*s*s*Math.sin(3*phi+.6)+shape.deformation*s*(.18*moving+.12*memory);return [radius*Math.cos(theta),y,radius*Math.sin(theta)];}
export function listenerAnchor(uv,field,size,shape){const s=uv[0],phi=(uv[1]-.5)*2*Math.PI,p=listenerPoint(s,phi,field,size,shape);const a=sub(listenerPoint(s+.0004,phi,field,size,shape),listenerPoint(s-.0004,phi,field,size,shape)),b=sub(listenerPoint(s,phi+.0006,field,size,shape),listenerPoint(s,phi-.0006,field,size,shape));return add(p,scale(unit(cross(a,b)),shape.thickness));}
// Natural cubic interpolation of equally spaced bridge bead values.
export function naturalSpline(values){
  const n=values.length,m=new Float64Array(n),rhs=new Float64Array(n),upper=new Float64Array(n);
  for(let i=1;i<n-1;i++){const d=4-(i>1?upper[i-1]:0);upper[i]=1/d;rhs[i]=(6*(values[i+1]-2*values[i]+values[i-1])-(i>1?rhs[i-1]:0))/d;}
  for(let i=n-2;i>0;i--)m[i]=rhs[i]-upper[i]*m[i+1];
  return t=>{const p=Math.min(n-1,Math.max(0,t*(n-1))),i=Math.min(n-2,Math.floor(p)),b=p-i,a=1-b;return a*values[i]+b*values[i+1]+((a*a*a-a)*m[i]+(b*b*b-b)*m[i+1])/6;};
}
