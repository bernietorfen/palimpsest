"""Record the original second-act score. Run on RunPod, preserving exact source."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time
import numpy as np
import torch
from studio.choir_score import ChoirScore
from studio.choir_material import MaterialChoir,Port,port_footprint
from studio.choir_scene import load_scene,bridge_specs
from studio.material import MaterialConfig
from studio.preserve import sha256

SOURCES=('studio/choir_performance.py','studio/choir_score.py','studio/choir_scene.py','studio/choir_material.py',
         'studio/batched_material.py','studio/material.py','studio/score.py','site/choir-scene.json')


def main(args):
    torch.set_num_threads(2);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.set_float32_matmul_precision('highest')
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False);hashes={}
    for relative in SOURCES:
        target=output/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(relative,target);hashes[relative]=sha256(Path(relative))
    scene=load_scene();score=ChoirScore();rate=96;size=64;fps=args.fps;cfg=MaterialConfig(size=size,dt=1/rate,feedback=.08)
    protocol={'created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':hashes,'config':asdict(cfg),'field_fps':fps,'readout_hz':rate,'score':score.manifest(),'scene':scene}
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    choir=MaterialChoir(cfg,7,bridge_specs(scene),beads=16)
    frames=round(score.duration*fps)+1;steps=round(score.duration*rate)
    fields=np.lib.format.open_memmap(output/'fields.npy',mode='w+',dtype=np.float16,shape=(frames,7,size,size,4))
    readouts={key:[] for key in ('time','bridge_u','bridge_v','endpoints','gates','pitch_hz','amplitude','memory','fatigue','position','velocity','drive','contact')}
    maps=[port_footprint(Port(*p,.16),size,device='cuda',dtype=torch.float32) for p in score.contacts]
    force=torch.zeros_like(choir.material.u);diagnostics=[];began=time.monotonic()
    for step in range(steps+1):
        t=step/rate
        if step==242*rate:choir.reset_transients(reset_clock=False)
        choir.set_connections(score.connection_strengths(t))
        if step%(rate//fps)==0:fields[step//(rate//fps)]=choir.fields().cpu().numpy().astype(np.float16)
        reading=choir.readout();excitation=score.excitation(t);contact=score.contact_strengths(t)
        readouts['time'].append(t);readouts['drive'].append(excitation);readouts['contact'].append(contact)
        for name,value in (('bridge_u',choir.wave.u),('bridge_v',choir.wave.v),('endpoints',choir.wave.coordinates(choir.material.u)),('gates',choir.gates)):
            readouts[name].append(value.cpu().numpy().copy())
        for name in ('pitch_hz','amplitude','memory','fatigue','position','velocity'):readouts[name].append(reading[name].cpu().numpy())
        if step%(rate*12)==0:
            d=choir.diagnostics();assert d['finite'];diagnostics.append(d)
            print(json.dumps({'time':t,'memory':d['memory_rms'],'wear':d['fatigue_mean'],'elapsed':time.monotonic()-began}),flush=True)
        if step in (42*rate,96*rate,144*rate,228*rate,242*rate,288*rate):
            state=choir.state_dict()
            np.savez_compressed(output/f'state-{int(t):03d}.npz',**{k:v.numpy() for k,v in state['material'].items()},
                                bridge_u=state['bridge_u'].numpy(),bridge_v=state['bridge_v'].numpy(),gates=state['gates'].numpy(),steps=np.array(state['steps']),index=np.array(state['index']))
        if step==steps:break
        force.zero_()
        for i,p in enumerate(score.contacts):force[p[0]]+=float(contact[i])*maps[i]
        choir.step(torch.from_numpy(excitation).to('cuda'),contact_force=force)
    fields.flush();np.savez_compressed(output/'readouts.npz',**{k:np.asarray(v) for k,v in readouts.items()})
    (output/'diagnostics.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
    # The question is exactly repeated as a force envelope. Report every body's
    # difference; no perceptual or isolated-history attribution is inferred here.
    p=np.asarray(readouts['pitch_hz'],dtype=np.float64)
    a=p[5*rate:45*rate];b=p[248*rate:288*rate]
    comparison={'question_duration':40,'receivers':[0,2,3,4,5,6],'pitch_difference_rms_hz':np.sqrt(np.mean((a-b)**2,axis=(0,2))).tolist(),
                'initial_question_maximum_retained_rms':max(d['memory_rms'][i] for d in diagnostics if d['time']<=48 for i in (0,2,3,4,5,6)),
                'scope':'Composed before/after response; includes the disclosed transient reset and later evolution of retained fields.'}
    (output/'comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
    inventory=[{'path':str(p.relative_to(output)),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(output.rglob('*')) if p.is_file()]
    (output/'manifest.json').write_text(json.dumps({'finished_utc':datetime.now(timezone.utc).isoformat(),'seconds':time.monotonic()-began,'field_fps':fps,'readout_hz':rate,'frames':frames,'files':inventory},indent=2)+'\n')
    print(json.dumps({'finished':str(output),'seconds':time.monotonic()-began,'comparison':comparison}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='artifacts/studies/choir-performance-001');parser.add_argument('--fps',type=int,choices=(12,24),default=24);main(parser.parse_args())
