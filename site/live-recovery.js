// One bounded recovery copy per browser tab. No history and no network storage.
const KEY='palimpsest-live-recovery-v1',LIMIT=1_500_000;
export class LiveRecovery {
  constructor(storage){
    this.storage=null;this.lastSaved=null;
    try{this.storage=storage===undefined?sessionStorage:storage;}catch{}
  }
  read(){
    if(!this.storage)return null;
    try{
      const text=this.storage.getItem(KEY);if(!text)return null;
      if(text.length>LIMIT)throw new Error('Oversized recovery copy');
      const value=JSON.parse(text);
      if(value?.format!=='palimpsest-tab-copy'||value.version!==1||!value.state||typeof value.saved_utc!=='string')throw new Error('Invalid recovery copy');
      this.lastSaved=value.saved_utc;return value;
    }catch{this.clear();return null;}
  }
  write(state){
    if(!this.storage)return false;
    try{
      const saved_utc=new Date().toISOString();
      const text=JSON.stringify({format:'palimpsest-tab-copy',version:1,saved_utc,state});
      if(text.length>LIMIT)return false;
      this.storage.setItem(KEY,text);this.lastSaved=saved_utc;return true;
    }catch{return false;}
  }
  clear(){try{this.storage?.removeItem(KEY);}catch{}this.lastSaved=null;}
}
