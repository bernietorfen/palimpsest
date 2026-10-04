// Causal live voice synthesis. All waves are calculated here; no audio assets.
// A sine table avoids millions of transcendental calls per second on a phone.
const TABLE_SIZE=8192, MASK=TABLE_SIZE-1, TAU=2*Math.PI;
const SINE=new Float64Array(TABLE_SIZE+1);
for(let i=0;i<=TABLE_SIZE;i++)SINE[i]=Math.sin(i*TAU/TABLE_SIZE);
const PANS=[-.55,.29,-.12,.58,-.38,.08,.41,-.63,.19,-.23,.68,-.04];
const BASE=[110,137.5,146.6666667,165,183.3333333,220,247.5,275,293.3333333,330,366.6666667,440];
class PalimpsestVoices extends AudioWorkletProcessor {
  constructor(){
    super();
    this.phase=new Float64Array(12*9);
    this.pitch=new Float64Array(BASE);this.targetPitch=new Float64Array(BASE);
    this.amplitude=new Float64Array(12);this.targetAmplitude=new Float64Array(12);
    this.fatigue=new Float64Array(12);this.targetFatigue=new Float64Array(12);
    this.velocity=new Float64Array(12);this.targetVelocity=new Float64Array(12);
    this.shades=new Float64Array(12*9);this.increments=new Float64Array(12*9);
    this.panL=PANS.map(p=>Math.sqrt((1-p)/2));this.panR=PANS.map(p=>Math.sqrt((1+p)/2));
    this.ratios=Array.from({length:8},(_,p)=>(p+1)*(1+.0009*((p+1)**2-1))).concat([2.507]);
    this.weights=Array.from({length:8},(_,p)=>(1/(p+1)**1.9)*(p%2?.72:1)).concat([.075]);
    this.lastControl=0;this.samples=0;this.peak=0;
    for(let v=0;v<12;v++)for(let p=0;p<9;p++)this.phase[v*9+p]=((v*.713*(p+1))%TAU)/TAU*TABLE_SIZE;
    this.port.onmessage=({data})=>{
      if(data.type==='control'){
        const r=data.readout;
        if(!r||!['pitch','amplitude','fatigue','velocity'].every(k=>Array.isArray(r[k])&&r[k].length===12&&r[k].every(Number.isFinite)))return;
        for(let v=0;v<12;v++){
          this.targetPitch[v]=Math.max(40,Math.min(1600,r.pitch[v]));
          this.targetAmplitude[v]=Math.max(0,.78*Math.tanh(r.amplitude[v]*4.4)+.22*Math.tanh((data.drive[v]||0)*3.2)-.000015);
          this.targetFatigue[v]=Math.max(0,Math.min(1,r.fatigue[v]));
          this.targetVelocity[v]=Math.tanh(Math.abs(r.velocity[v])*7);
        }
        this.lastControl=currentTime;
      } else if(data.type==='quiet')this.targetAmplitude.fill(0);
    };
  }
  process(inputs,outputs){
    const output=outputs[0];if(output.length<2)return true;
    const left=output[0],right=output[1],count=left.length;
    if(currentTime-this.lastControl>.6)this.targetAmplitude.fill(0);
    const smooth=1-Math.exp(-count/(sampleRate*.055));
    for(let v=0;v<12;v++){
      this.fatigue[v]+=(this.targetFatigue[v]-this.fatigue[v])*smooth;
      this.velocity[v]+=(this.targetVelocity[v]-this.velocity[v])*smooth;
      for(let p=0;p<9;p++){
        const k=v*9+p;
        this.shades[k]=this.weights[p]*(p===8?this.velocity[v]:Math.exp(-this.fatigue[v]*(p+1)*.21));
      }
    }
    const pitchRate=1-Math.exp(-1/(sampleRate*.035)),ampRate=1-Math.exp(-1/(sampleRate*.045));
    for(let i=0;i<count;i++){
      let l=0,r=0;
      for(let v=0;v<12;v++){
        this.pitch[v]+=(this.targetPitch[v]-this.pitch[v])*pitchRate;
        this.amplitude[v]+=(this.targetAmplitude[v]-this.amplitude[v])*ampRate;
        const increment=this.pitch[v]*TABLE_SIZE/sampleRate;
        let wave=0;
        for(let p=0;p<9;p++){
          const k=v*9+p;
          let phase=this.phase[k]+increment*this.ratios[p];
          phase-=Math.floor(phase/TABLE_SIZE)*TABLE_SIZE;
          this.phase[k]=phase;
          const at=Math.floor(phase)&MASK,f=phase-Math.floor(phase);
          wave+=(SINE[at]+(SINE[at+1]-SINE[at])*f)*this.shades[k];
        }
        wave*=this.amplitude[v]*(v<6?.14:.086);
        l+=wave*this.panL[v];r+=wave*this.panR[v];
      }
      left[i]=.85*Math.tanh(l/.85);right[i]=.85*Math.tanh(r/.85);
      this.peak=Math.max(this.peak,Math.abs(left[i]),Math.abs(right[i]));
    }
    this.samples+=count;
    if(this.samples>=sampleRate){this.port.postMessage({type:'meter',peak:this.peak});this.samples=0;this.peak=0;}
    return true;
  }
}
registerProcessor('palimpsest-voices',PalimpsestVoices);
