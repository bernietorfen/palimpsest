"""A controlled listening edition of the performance's two quiet questions.

RunPod only. Four observed bodies, one common synthesis phase and gain. E's
complete recorded controls agree exactly; its two web links deliberately point
to the same encoded sound. This is a view of the composition, not the separate
transfer control experiment.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import numpy as np
from scipy import signal
from scipy.ndimage import gaussian_filter1d
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont
from studio.choir_geometry import ListenerShape, build_listener
from studio.choir_render import ChoirRenderer, SceneObject, floor_object, transform
from studio.reconstruction import periodic_field
from studio.preserve import sha256

BODIES=(4,0,2,6)
NAMES={4:'E',0:'A',2:'C',6:'G'}
SOURCES=('studio/choir_witness.py','studio/choir_geometry.py','studio/choir_render.py',
         'studio/reconstruction.py','studio/shaders/choir.frag','studio/shaders/choir_composite.frag')


def synthesize(control, sr=48000):
    duration=40.;rate=96.;count=round(duration*sr)
    data={key:gaussian_filter1d(value.astype(np.float64),2.,axis=0,mode='nearest') for key,value in control.items()}
    result=np.zeros(count,dtype=np.float64);phase_end=np.zeros(12)
    for start in range(0,count,sr*2):
        end=min(count,start+sr*2);t=np.arange(start,end)/sr;pos=t*rate
        left=np.minimum(pos.astype(int),len(data['pitch_hz'])-2);fraction=(pos-left)[:,None]
        now={k:v[left]*(1-fraction)+v[left+1]*fraction for k,v in data.items()}
        phase=np.cumsum(now['pitch_hz']*(2*np.pi/sr),axis=0)+phase_end
        phase_end=phase[-1].copy();wave=np.zeros_like(phase)
        for partial in range(1,9):
            ratio=partial*(1+.0009*(partial*partial-1));weight=1/partial**1.9*(1 if partial%2 else .72)
            angle=np.remainder(phase*ratio+np.arange(12)[None]*.713*partial,2*np.pi)
            wave+=weight*np.exp(-now['fatigue']*partial*.21)*np.sin(angle)
        amplitude=np.maximum(0,np.tanh(now['amplitude']*4.4)-.000004)
        result[start:end]=(wave*amplitude*np.where(np.arange(12)<6,.070,.043)).sum(axis=1)
    result=signal.sosfilt(signal.butter(2,28,btype='highpass',fs=sr,output='sos'),result)
    t=np.arange(count)/sr
    result*=np.sin(np.clip(t/.12,0,1)*np.pi/2)**2*np.sin(np.clip((duration-t)/.65,0,1)*np.pi/2)**2
    return result.astype(np.float32)


def main(args):
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False)
    web=Path(args.web);web.mkdir(parents=True,exist_ok=False)
    hashes={}
    for relative in SOURCES:
        target=output/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(relative,target);hashes[relative]=sha256(Path(relative))
    source=Path(args.performance);protocol=json.loads((source/'protocol.json').read_text());scene=protocol['scene']
    with np.load(source/'readouts.npz') as recorded:
        windows=[{key:recorded[key][round(t*96):round((t+40)*96)+1] for key in ('pitch_hz','amplitude','fatigue')} for t in (5,248)]
    # Every unwritten listener received the same question with links absent.
    for body in (0,2,3,4,5,6):
        for key in windows[0]:assert np.array_equal(windows[0][key][:,body],windows[0][key][:,4])
    for key in windows[0]:assert np.array_equal(windows[0][key][:,4],windows[1][key][:,4])
    sounds={'before':synthesize({k:v[:,4] for k,v in windows[0].items()})}
    for body in (0,2,6):sounds['after-'+NAMES[body]]=synthesize({k:v[:,body] for k,v in windows[1].items()})
    repeated=synthesize({k:v[:,4] for k,v in windows[1].items()})
    assert np.array_equal(sounds['before'],repeated)
    peak=max(float(np.abs(v).max()) for v in sounds.values());gain=.45/peak
    audio={}
    for name,sound in sounds.items():
        wav=output/(name+'.wav');sf.write(wav,sound*gain,48000,subtype='PCM_24')
        encoded=web/(name+'.m4a')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-i',str(wav),'-c:a','aac','-b:a','72k','-movflags','+faststart',str(encoded)],check=True)
        audio[name]={'source_sha256':sha256(wav),'web_sha256':sha256(encoded),'peak':float(np.max(np.abs(sound*gain))),'rms':float(np.sqrt(np.mean((sound.astype(np.float64)*gain)**2)))}
    fields=np.load(source/'fields.npy',mmap_mode='r');renderer=ChoirRenderer(1440,1200,shadow_size=2048)
    figures={};sheet=Image.new('RGB',(1200,4*272),'#ece7df');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
    for row,body in enumerate(BODIES):
        spec=scene['bodies'][body];shape=ListenerShape(**scene['shapes'][spec['shape']]);name=NAMES[body]
        # A fixed isolated display pose permits a direct comparison of fields.
        model=transform((0,0,0),turn=.18,tilt=.08,lean=0,scale=1)
        for side,t in enumerate((21,264)):
            field=periodic_field(fields[round(t*24),body],256)
            obj=SceneObject(build_listener(field,128,192,shape),field,model)
            camera=(4.6,3.0,6.5) if body==6 else (3.9,2.6,5.5)
            image=Image.fromarray(renderer.draw_scene([obj,floor_object(-1.96)],camera=camera,target=(0,.04,0),focal_length=2.42,samples=40,shadow_extent=4.5,shadow_softness=.75))
            filename=f'{name}-{"before" if side==0 else "after"}.jpg';image.save(web/filename,quality=91)
            thumb=image.copy();thumb.thumbnail((288,240));x=side*300;sheet.paste(thumb,(x,row*272));draw.text((x+8,row*272+242),f'{name} / {"before" if side==0 else "after"}',font=font,fill='#293c3c')
            figures[filename]={'performance_time':t,'sha256':sha256(web/filename),'display_pose':'isolated, common pose and lighting'}
        delta=windows[1]['pitch_hz'][:,body].astype(np.float64)-windows[0]['pitch_hz'][:,body]
        # A legible field of twelve measured tuning trajectories, in hertz.
        x=630;y=row*272+32;w=540;h=190
        for m in range(12):
            values=delta[::8,m];baseline=y+m*h/12
            points=[(x+i/(len(values)-1)*w,baseline-float(v)*2.1) for i,v in enumerate(values)]
            draw.line([(x,baseline),(x+w,baseline)],fill='#d1ccbf',width=1)
            draw.line(points,fill='#315b66' if m%2 else '#986544',width=2)
        draw.text((630,row*272+242),f'pitch difference / RMS {np.sqrt(np.mean(delta[:-1]**2)):.6f} Hz',font=font,fill='#293c3c')
    renderer.close();sheet.save(output/'review.jpg',quality=88)
    body_data=[]
    for body in BODIES:
        name=NAMES[body];delta=windows[1]['pitch_hz'][:,body].astype(np.float64)-windows[0]['pitch_hz'][:,body]
        body_data.append({'id':name,'index':body,'before':'before.m4a','after':'before.m4a' if body==4 else 'after-'+name+'.m4a',
                          'before_image':name+'-before.jpg','after_image':name+'-after.jpg',
                          'pitch_difference_rms_hz':float(np.sqrt(np.mean(delta[:-1]**2))),
                          'pitch_difference_max_hz':float(np.max(np.abs(delta))),
                          'pitch_delta_hz':np.round(delta[::8],5).tolist()})
    document={'format':'palimpsest-choir-witness','version':1,'duration':40,'trajectory_rate':12,'question_starts':[5,248],
              'figure_times':[21,264],'bodies':body_data,'common_gain':gain,
              'scope':'Matched phase, identical synthesis and one common gain applied to the saved before/after controls. E has identical controls and PCM; both E buttons use the same encoded file. Isolated studio portraits show the recorded fields sixteen seconds into each question. This is a finite comparison within the authored performance; see the separate controlled transfer study.'}
    (web/'witness.json').write_text(json.dumps(document,separators=(',',':'))+'\n')
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':hashes,'performance_manifest_sha256':sha256(source/'manifest.json'),
            'same_initial_listener_controls':True,'E_control_and_PCM_exactly_equal':True,'common_gain':gain,'pre_gain_max_peak':peak,'audio':audio,'figures':figures,
            'web_files':{p.name:{'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(web.iterdir())},'bodies':[{k:v for k,v in b.items() if k!='pitch_delta_hz'} for b in body_data],
            'scope':document['scope'],'listening':'Signal generation and numerical equality checks only; no perceptual audition is claimed.'}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--performance',default='artifacts/studies/choir-performance-001');p.add_argument('--output',default='artwork/choir-witness-001');p.add_argument('--web',default='site/assets/generated/choir-witness');main(p.parse_args())
