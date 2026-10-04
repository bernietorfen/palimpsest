export class LiveSound {
  constructor(){this.context=null;this.ready=false;this.level=.65;this.active=false;this.peak=0;}
  async initialize(){
    if(this.ready)return;
    if(this.initializing)return this.initializing;
    const Context=window.AudioContext||window.webkitAudioContext;
    if(!Context)throw new Error('Live sound is unavailable in this browser');
    this.context=new Context({latencyHint:'interactive'});
    const context=this.context;
    const resume=context.resume();
    this.initializing=(async()=>{
      await context.audioWorklet.addModule('/live-audio-worklet.js');
      await resume;
      this.voice=new AudioWorkletNode(context,'palimpsest-voices',{numberOfInputs:0,numberOfOutputs:1,outputChannelCount:[2]});
      this.voice.port.onmessage=({data})=>{if(data.type==='meter')this.peak=data.peak;};
      this.highpass=context.createBiquadFilter();this.highpass.type='highpass';this.highpass.frequency.value=28;this.highpass.Q.value=.707;
      this.voice.connect(this.highpass);
      this.room=context.createConvolver();this.room.normalize=false;
      const seconds=3.2,n=Math.round(context.sampleRate*seconds),impulse=context.createBuffer(2,n,context.sampleRate);
      let seed=20261003;
      const random=()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return(seed>>>0)/4294967296*2-1;};
      for(let channel=0;channel<2;channel++){
        const data=impulse.getChannelData(channel);let low=0,high=0;
        for(let i=0;i<n;i++){
          low+=.42*(random()-low);high+=.028*(low-high);
          data[i]=i<context.sampleRate*.018?0:(low-high)*.0033*Math.exp(-i/(context.sampleRate*.85));
        }
        for(const[delay,amp]of[[.027,.22],[.061,-.15],[.113,.125],[.191,.095],[.337,-.06]])data[Math.round((delay+channel*.0061)*context.sampleRate)]+=amp;
      }
      this.room.buffer=impulse;this.wet=context.createGain();this.wet.gain.value=.47;
      this.highpass.connect(this.room);this.room.connect(this.wet);
      this.limiter=context.createDynamicsCompressor();this.limiter.threshold.value=-5;this.limiter.knee.value=6;this.limiter.ratio.value=12;this.limiter.attack.value=.003;this.limiter.release.value=.18;
      this.highpass.connect(this.limiter);this.wet.connect(this.limiter);
      this.gain=context.createGain();this.gain.gain.value=0;this.limiter.connect(this.gain);this.gain.connect(context.destination);
      this.ready=true;
    })();
    try{await this.initializing;}catch(error){await context.close();this.context=null;this.initializing=null;throw error;}
  }
  async start(){await this.initialize();await this.context.resume();this.active=true;this.gain.gain.setTargetAtTime(this.level,this.context.currentTime,.05);}
  control(readout,drive){if(this.ready)this.voice.port.postMessage({type:'control',readout,drive});}
  volume(value){this.level=Math.max(0,Math.min(1,value));if(this.ready&&this.active)this.gain.gain.setTargetAtTime(this.level,this.context.currentTime,.035);}
  quiet(){if(this.ready){this.active=false;this.voice.port.postMessage({type:'quiet'});this.gain.gain.setTargetAtTime(0,this.context.currentTime,.035);}}
  async suspend(){this.quiet();if(this.context&&this.context.state!=='closed')await this.context.suspend();}
  async dispose(){this.quiet();if(this.context&&this.context.state!=='closed')await this.context.close();this.ready=false;}
}
