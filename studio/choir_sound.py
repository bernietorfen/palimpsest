"""Original spatial additive synthesis of the recorded material choir. RunPod only.

Every audible mode follows recorded pitch, amplitude, fatigue and velocity.
The listening score foregrounds E for the matched opening/returning views.
Continuous carrier phase survives chunks. The room is our procedural first-act
room; no samples, trained models, imitation instruments or external audio.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import time
import numpy as np
from scipy import signal
from scipy.ndimage import gaussian_filter1d
import soundfile as sf
import torch
from studio import choir_cinematography as camera
from studio.preserve import sha256
from studio.sound import make_room

SOURCES=('studio/choir_sound.py','studio/choir_cinematography.py','studio/sound.py')


def main(args):
    torch.set_num_threads(2)
    output=Path(args.output)
    if output.exists():raise FileExistsError(output)
    records=output.with_suffix('');records.mkdir(parents=True,exist_ok=False);hashes={}
    for relative in SOURCES:
        target=records/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(relative,target);hashes[relative]=sha256(Path(relative))
    source=Path(args.performance);protocol=json.loads((source/'protocol.json').read_text())
    with np.load(source/'readouts.npz') as data:
        times=data['time'];raw={k:data[k] for k in ('pitch_hz','amplitude','fatigue','velocity')}
    sr=args.sample_rate;duration=float(times[-1]);samples=round(duration*sr);stereo=np.zeros((samples,2),dtype=np.float32)
    began=time.monotonic();control={}
    for key,value in raw.items():
        smooth=gaussian_filter1d(value.astype(np.float64),2.,axis=0,mode='nearest').reshape(len(times),84).T
        control[key]=torch.tensor(smooth,dtype=torch.float32,device='cuda')
    weights=np.array([camera.listening_weights(t) for t in times],dtype=np.float32)
    positions=np.array([b['position'] for b in protocol['scene']['bodies']]);pans=[]
    for t in times:
        settings=camera.camera_at(float(t));eye=np.asarray(settings['camera']);target=np.asarray(settings['target']);forward=target-eye;forward/=np.linalg.norm(forward)
        right=np.cross(forward,[0,1,0]);right/=np.linalg.norm(right);pans.append(np.clip((positions-target)@right/4.4,-.88,.88))
    pans=np.asarray(pans,dtype=np.float32)
    weights=gaussian_filter1d(weights,6.,axis=0,mode='nearest')
    pans=gaussian_filter1d(pans,12.,axis=0,mode='nearest')
    control['weight']=torch.tensor(np.repeat(weights,12,axis=1).T,device='cuda');control['pan']=torch.tensor(np.repeat(pans,12,axis=1).T,device='cuda')
    phase_end=torch.zeros(84,dtype=torch.float64,device='cuda')
    modes=torch.arange(84,device='cuda')%12;bodies=torch.arange(84,device='cuda')//12
    voice_gain=torch.where(modes<6,.070,.043).to(torch.float32)[:,None]
    offset=(modes*.713+bodies*1.037).to(torch.float64)[:,None]
    rate=protocol['readout_hz'];block=sr*3
    for start in range(0,samples,block):
        end=min(start+block,samples);sample_time=torch.arange(start,end,dtype=torch.float64,device='cuda')/sr
        coordinate=sample_time*rate;left=coordinate.long().clamp(0,len(times)-2);fraction=(coordinate-left).to(torch.float32)[None]
        current={k:v[:,left]*(1-fraction)+v[:,left+1]*fraction for k,v in control.items()}
        phase=torch.cumsum(current['pitch_hz'].to(torch.float64)*(2*np.pi/sr),dim=1)+phase_end[:,None];phase_end=phase[:,-1].clone()
        wave=torch.zeros((84,end-start),device='cuda',dtype=torch.float32)
        for partial in range(1,9):
            ratio=partial*(1+.0009*(partial*partial-1));weight=1/partial**1.9*(1 if partial%2 else .72)
            slow=.014*partial*torch.sin(2*np.pi*sample_time[None]*(.19+modes[:,None]*.007+bodies[:,None]*.002))
            angle=torch.remainder(phase*ratio+offset*partial+slow,2*np.pi).to(torch.float32)
            wave+=weight*torch.exp(-current['fatigue']*partial*.21)*torch.sin(angle)
        ring=torch.sin(torch.remainder(phase*2.507+offset,2*np.pi).to(torch.float32))
        wave+=.075*torch.tanh(current['velocity'].abs()*7)*ring
        amplitude=(torch.tanh(current['amplitude']*4.4)-.000004).clamp_min(0)
        wave*=amplitude*voice_gain*current['weight']
        left_audio=(wave*torch.sqrt((1-current['pan'])/2)).sum(dim=0)
        right_audio=(wave*torch.sqrt((1+current['pan'])/2)).sum(dim=0)
        stereo[start:end]=torch.stack((left_audio,right_audio),dim=1).cpu().numpy()
        if start%(sr*24)==0:print(json.dumps({'time':start/sr,'elapsed':time.monotonic()-began,'peak_so_far':float(np.max(np.abs(stereo[:end])))}),flush=True)
    stereo=signal.sosfilt(signal.butter(2,28,btype='highpass',fs=sr,output='sos'),stereo,axis=0).astype(np.float32)
    room=make_room(sr);mid=stereo.mean(axis=1)
    for channel in range(2):stereo[:,channel]+=signal.fftconvolve(mid,room[:,channel],mode='full')[:samples]*.43
    sample_time=np.arange(samples)/sr;boundary=np.sin(np.clip(sample_time/1.5,0,1)*np.pi/2)**2*np.sin(np.clip((duration-sample_time)/4,0,1)*np.pi/2)**2;stereo*=boundary[:,None]
    assert np.isfinite(stereo).all();peak=float(np.max(np.abs(stereo)));rms=float(np.sqrt(np.mean(stereo.astype(np.float64)**2)))
    sf.write(output,stereo,sr,subtype='FLOAT')
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':hashes,'performance_manifest_sha256':sha256(source/'manifest.json'),
            'sample_rate':sr,'frames':samples,'duration':duration,'channels':2,'subtype':'FLOAT','peak':peak,'rms':rms,'seconds':time.monotonic()-began,
            'source_pitch_ranges_hz':[[float(raw['pitch_hz'][:,b].min()),float(raw['pitch_hz'][:,b].max())] for b in range(7)],
            'listening':camera.manifest()['listener'],'mix_smoothing_sigma_seconds':6/rate,'pan_smoothing_sigma_seconds':12/rate,'output_sha256':sha256(output),
            'scope':'Original additive synthesis, noncausal offline control smoothing, continuous carrier phases, authored observer mix and procedural room. Signal measurements only; no perceptual audition is claimed.'}
    output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--performance',default='artifacts/studies/choir-performance-001');p.add_argument('--output',default='artwork/choir-sound-001.wav');p.add_argument('--sample-rate',type=int,default=48000);main(p.parse_args())
