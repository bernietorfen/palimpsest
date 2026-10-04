// Seven spatial voices, each read from the twelve actual material modes.
// No recordings or generated sound assets. Fixed, causal smoothing.
const N=8192,TAU=2*Math.PI,SINE=new Float64Array(N+1);
for(let i=0;i<=N;i++)SINE[i]=Math.sin(i*TAU/N);
const BASE=[110,137.5,146.6666667,165,183.3333333,220,247.5,275,293.3333333,330,366.6666667,440];
class ChoirVoices extends AudioWorkletProcessor {
  constructor(){
    super();this.pitch=new Float64Array(84);this.targetPitch=new Float64Array(84);this.amp=new Float64Array(84);this.targetAmp=new Float64Array(84);this.fatigue=new Float64Array(84);this.phase=new Float64Array(84*4);this.pan=new Float64Array(7);this.targetPan=new Float64Array(7);this.solo=-1;this.last=0;this.samples=0;this.peak=0;
    for(let i=0;i<84;i++){this.pitch[i]=this.targetPitch[i]=BASE[i%12];for(let p=0;p<4;p++)this.phase[i*4+p]=(i*.713*(p+1)%TAU)/TAU*N;}
    this.port.onmessage=({data})=>{
      if(data.type==='quiet')this.targetAmp.fill(0);
      else if(data.type==='control'&&Array.isArray(data.readout)&&data.readout.length===7){
        if(!data.readout.every(r=>['pitch','amplitude','fatigue'].every(k=>Array.isArray(r[k])&&r[k].length===12&&r[k].every(Number.isFinite))))return;
        this.solo=Number.isInteger(data.solo)?data.solo:-1;
        for(let b=0;b<7;b++)for(let m=0;m<12;m++){
          const k=b*12+m,r=data.readout[b];this.targetPitch[k]=Math.max(40,Math.min(1600,r.pitch[m]));
          this.targetAmp[k]=(this.solo===-1||this.solo===b)?Math.max(0,Math.tanh(r.amplitude[m]*3.6)-.000004)*(m<6?.14:.086):0;
          this.fatigue[k]=Math.max(0,Math.min(1,r.fatigue[m]));
        }
        if(Array.isArray(data.pans)&&data.pans.length===7&&data.pans.every(Number.isFinite))for(let b=0;b<7;b++)this.targetPan[b]=Math.max(-.9,Math.min(.9,data.pans[b]));
        this.last=currentTime;
      }
    };
  }
  process(inputs,outputs){
    const out=outputs[0];if(out.length<2)return true;const left=out[0],right=out[1],count=left.length;
    if(currentTime-this.last>.7)this.targetAmp.fill(0);
    const pitchRate=1-Math.exp(-1/(sampleRate*.045)),ampRate=1-Math.exp(-1/(sampleRate*.065));
    for(let b=0;b<7;b++)this.pan[b]+=(this.targetPan[b]-this.pan[b])*(1-Math.exp(-count/(sampleRate*.12)));
    for(let k=0;k<84;k++){
      if(this.amp[k]<1e-7&&this.targetAmp[k]<1e-7)continue;
      const pan=this.pan[Math.floor(k/12)],l=Math.sqrt((1-pan)/2),r=Math.sqrt((1+pan)/2),d=this.fatigue[k];
      const ratios=[1,2.0054,3.0216,2.507],weights=[1,.192*Math.exp(-d*.42),.107*Math.exp(-d*.63),.042];
      for(let i=0;i<count;i++){
        this.pitch[k]+=(this.targetPitch[k]-this.pitch[k])*pitchRate;this.amp[k]+=(this.targetAmp[k]-this.amp[k])*ampRate;
        const inc=this.pitch[k]*N/sampleRate;let wave=0;
        for(let p=0;p<4;p++){const j=k*4+p;let phase=this.phase[j]+inc*ratios[p];phase-=Math.floor(phase/N)*N;this.phase[j]=phase;const at=Math.floor(phase),f=phase-at;wave+=(SINE[at]+(SINE[at+1]-SINE[at])*f)*weights[p];}
        wave*=this.amp[k];left[i]+=wave*l;right[i]+=wave*r;
      }
    }
    for(let i=0;i<count;i++){left[i]=.8*Math.tanh(left[i]/.8);right[i]=.8*Math.tanh(right[i]/.8);this.peak=Math.max(this.peak,Math.abs(left[i]),Math.abs(right[i]));}
    this.samples+=count;if(this.samples>=sampleRate){this.port.postMessage({type:'meter',peak:this.peak});this.samples=0;this.peak=0;}
    return true;
  }
}
registerProcessor('palimpsest-choir',ChoirVoices);
