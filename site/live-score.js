// Gesture capture is indexed by material steps, never animation frames.
export class LiveScore {
  constructor(dt=1/96){
    this.dt=dt;this.limit=Math.round(24/dt);this.release=Math.round(2/dt);
    this.phrase=null;this.mode='idle';this.begin=0;this.cursor=0;
    this.lastResponse=null;this.previousResponse=null;this.response=[];
  }
  record(step,drive,targets){
    this.mode='recording';this.begin=step;this.cursor=0;this.response=[];this.clearResponses();
    this.building={version:1,dt:this.dt,initial_drive:Array.from(drive),events:[{step:0,values:Array.from(targets)}],duration_steps:0};
  }
  event(step,values){
    if(this.mode!=='recording')return;
    const local=Math.min(this.limit,step-this.begin),events=this.building.events;
    const event={step:local,values:Array.from(values)};
    if(events.at(-1).step===local)events[events.length-1]=event;
    else events.push(event);
  }
  finish(step){
    if(this.mode!=='recording')return false;
    const end=Math.max(1,Math.min(this.limit,step-this.begin));
    this.event(this.begin+end,Array(12).fill(0));
    this.building.duration_steps=end+this.release;
    this.phrase=this.building;this.building=null;this.mode='releasing';
    return true;
  }
  replay(step){
    if(!this.phrase)throw new Error('Write a phrase before asking it again');
    this.mode='replaying';this.begin=step;this.cursor=0;this.response=[];
    return this.phrase.initial_drive;
  }
  beforeStep(step,targets){
    const local=step-this.begin;
    if(this.mode==='recording'&&local>=this.limit){this.finish(step);targets.fill(0);}
    if(this.mode==='replaying'){
      while(this.cursor<this.phrase.events.length&&this.phrase.events[this.cursor].step<=local){
        targets.set(this.phrase.events[this.cursor].values);this.cursor++;
      }
    }
    if((this.mode==='releasing'||this.mode==='replaying')&&local>=this.phrase.duration_steps){
      targets.fill(0);this.previousResponse=this.lastResponse;
      this.lastResponse=this.response;this.response=[];this.mode='idle';return true;
    }
    return false;
  }
  sample(step,pitches){
    if(this.mode==='idle')return;
    const local=step-this.begin;
    if(local%4===0)this.response.push({step:local,pitch:Array.from(pitches)});
  }
  stop(){this.mode='idle';this.building=null;this.response=[];}
  clearResponses(){this.lastResponse=null;this.previousResponse=null;}
  savedResponses(){return [this.previousResponse,this.lastResponse];}
  validateResponses(value,phrase){
    if(value==null)return [null,null];
    if(!Array.isArray(value)||value.length!==2||(!phrase&&value.some(x=>x!==null)))throw new Error('Invalid saved replies');
    if(value[0]&&!value[1])throw new Error('The saved replies are incomplete');
    return value.map(response=>{
      if(response===null)return null;
      if(!Array.isArray(response)||response.length!==Math.floor(phrase.duration_steps/4))throw new Error('Invalid saved reply length');
      return response.map((sample,index)=>{
        if(sample.step!==(index+1)*4||!Array.isArray(sample.pitch)||sample.pitch.length!==12||sample.pitch.some(v=>!Number.isFinite(v)||v<=0||v>1e6))throw new Error('Invalid saved reply sample');
        return {step:sample.step,pitch:[...sample.pitch]};
      });
    });
  }
  describe(step){
    return {mode:this.mode,time:this.mode==='idle'?0:(step-this.begin)*this.dt,
      duration:this.phrase?this.phrase.duration_steps*this.dt:0,hasPhrase:Boolean(this.phrase),
      events:this.phrase?.events.length||0};
  }
  comparison(){
    if(!this.lastResponse||!this.previousResponse||this.lastResponse.length!==this.previousResponse.length)return null;
    let sum=0,count=0;
    for(let i=0;i<this.lastResponse.length;i++){
      if(this.lastResponse[i].step!==this.previousResponse[i].step)return null;
      for(let m=0;m<12;m++){sum+=(this.lastResponse[i].pitch[m]-this.previousResponse[i].pitch[m])**2;count++;}
    }
    return {rms_hz:Math.sqrt(sum/count),samples:this.lastResponse.length,
      previous:this.previousResponse,current:this.lastResponse};
  }
  validate(value){
    if(value==null)return null;
    if(value.version!==1||value.dt!==this.dt||!Number.isInteger(value.duration_steps)||value.duration_steps<=this.release||value.duration_steps>this.limit+this.release)throw new Error('Invalid saved phrase clock');
    const validDrive=a=>Array.isArray(a)&&a.length===12&&a.every(v=>Number.isFinite(v)&&v>=0&&v<=.65);
    if(!validDrive(value.initial_drive)||!Array.isArray(value.events)||!value.events.length||value.events.length>this.limit+1)throw new Error('Invalid saved phrase');
    let prior=-1;
    for(const event of value.events){
      if(!Number.isInteger(event.step)||event.step<=prior||event.step>value.duration_steps-this.release||!validDrive(event.values))throw new Error('Invalid saved gesture');
      prior=event.step;
    }
    if(value.events[0].step!==0||value.events.at(-1).step!==value.duration_steps-this.release||value.events.at(-1).values.some(Boolean))throw new Error('The saved phrase is incomplete');
    return {version:1,dt:this.dt,initial_drive:[...value.initial_drive],duration_steps:value.duration_steps,
      events:value.events.map(event=>({step:event.step,values:[...event.values]}))};
  }
}
