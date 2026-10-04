"""Execute the locked second-act protocol. Run only on RunPod."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time
import numpy as np
import torch
from studio.batched_material import BatchedMaterial
from studio.choir_material import MaterialChoir, Bridge, Port, port_footprint
from studio.material import MaterialConfig
from studio.preserve import sha256
from studio.score import Gesture

SOURCES=('studio/choir_transfer_study.py','studio/choir_material.py','studio/batched_material.py',
         'studio/material.py','studio/score.py','research/CHOIR-PROTOCOL.md')
CONDITIONS=('connected','isolated','second-link-absent','inscription-erased','wear-erased','both-erased')


def chain(offset):
    return (Bridge(Port(offset,.19,.37,.16),Port(offset+1,.71,.53,.16),tension=1.6),
            Bridge(Port(offset+1,.58,.50,.16),Port(offset+2,.71,.53,.16),tension=1.6))


def phrase(index):
    events=[]
    for k,onset in enumerate((2.,8.,15.,22.)):
        amplitude=.65+.07*((index+2*k)%5)
        sign=-1 if (index+3*k)%4==0 else 1
        x=.19+.025*((index+k)%3-1);y=.37+.025*((2*index+k)%3-1)
        events.append((x,y,Gesture(onset,0,amplitude,.7,.8,3.,polarity=sign)))
    return events


def main(args):
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.set_float32_matmul_precision('highest')
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False)
    hashes={}
    for relative in SOURCES:
        target=output/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(relative,target);hashes[relative]=sha256(Path(relative))
    protocol={'created_utc':datetime.now(timezone.utc).isoformat(),'rates':[96,192],
              'phrases':[[{'x':x,'y':y,**asdict(e)} for x,y,e in phrase(j)] for j in range(12)],
              'conditions':CONDITIONS,'source_sha256':hashes,'locked_plan':'research/CHOIR-PROTOCOL.md',
              'write_seconds':30,'probe_seconds':12,'probe_hz':24,'size':64}
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    began=time.monotonic();reports=[]
    for rate in protocol['rates']:
        cfg=MaterialConfig(size=64,dt=1/rate,feedback=.08)
        for case in range(12):
            directory=output/f'rate-{rate:03d}'/f'phrase-{case:02d}';directory.mkdir(parents=True)
            choir=MaterialChoir(cfg,9,tuple(e for offset in (0,3,6) for e in chain(offset)),beads=16)
            choir.set_connections([1,1,0,0,1,0])
            events=phrase(case)
            maps=[port_footprint(Port(0,x,y,.16),64,device='cuda',dtype=torch.float32) for x,y,_ in events]
            contact=torch.zeros_like(choir.material.u);drive=torch.zeros((9,12),device='cuda',dtype=torch.float32)
            for step in range(30*rate):
                contact.zero_()
                for footprint,(_,_,event) in zip(maps,events):
                    strength=event.at(step/rate)
                    if strength:contact[[0,3,6]]+=strength*footprint
                choir.step(drive,contact_force=contact)
                if step%(rate*10)==0 and not choir.diagnostics()['finite']:raise FloatingPointError('Non-finite writing state')
            written=choir.diagnostics();assert written['finite']
            state=choir.state_dict()
            np.savez_compressed(directory/'written-state.npz',
                                **{key:value.numpy() for key,value in state['material'].items()},
                                bridge_u=state['bridge_u'].numpy(),bridge_v=state['bridge_v'].numpy(),gates=state['gates'].numpy(),
                                steps=np.array(state['steps']),index=np.array(state['index']))
            # All probe materials are unlinked. These are field interventions on
            # one written state, not independently re-simulated writing histories.
            probe=BatchedMaterial(cfg,18)
            for condition,source in enumerate((0,3,6,0,0,0)):
                probe.p[condition*3:condition*3+3]=choir.material.p[source:source+3]
                probe.z[condition*3:condition*3+3]=choir.material.z[source:source+3]
            probe.p[9:12].zero_();probe.z[12:15].zero_();probe.p[15:18].zero_();probe.z[15:18].zero_()
            probe.reset_transients()
            np.savez_compressed(directory/'probe-initial.npz',p=probe.p.cpu().numpy(),z=probe.z.cpu().numpy())
            question=[Gesture(1,0,.025,.5,.4,1.6),Gesture(4,4,.025,.5,.4,1.6),Gesture(7,8,.025,.5,.4,1.6)]
            receivers=[i for i in range(18) if i%3 in (1,2)]
            excitation=torch.zeros((18,12),device='cuda',dtype=torch.float32)
            pitches=[]
            for step in range(12*rate+1):
                if step%(rate//24)==0:pitches.append(probe.tuning()[2].cpu().numpy())
                if step==12*rate:break
                excitation.zero_()
                for event in question:excitation[receivers,event.voice]=event.at(step/rate)
                probe.step(excitation)
            assert probe.finite()
            pitches=np.asarray(pitches).reshape(-1,6,3,12)
            np.savez_compressed(directory/'probe-readouts.npz',time=np.arange(289)/24,pitch_hz=pitches,conditions=np.array(CONDITIONS))
            outcomes=[]
            for receiver in (1,2):
                baseline=pitches[:,1,receiver].astype(np.float64)
                rms={name:float(np.sqrt(np.mean((pitches[:,i,receiver]-baseline)**2))) for i,name in enumerate(CONDITIONS)}
                erased=float(np.max(np.abs(pitches[:,5,receiver]-baseline)))
                broken=float(np.max(np.abs(pitches[:,2,receiver]-baseline))) if receiver==2 else None
                outcomes.append({'receiver':receiver,'rms_hz':rms,'both_erased_max_hz':erased,'broken_second_link_max_hz':broken,
                                 'written_memory_rms':written['memory_rms'][receiver],'written_wear_mean':written['fatigue_mean'][receiver],
                                 'admitted':rms['connected']>.01 and written['memory_rms'][receiver]>0 and written['fatigue_mean'][receiver]>0 and erased<=1e-6 and (broken is None or broken<=1e-6)})
            report={'rate':rate,'phrase':case,'config':asdict(cfg),'written_diagnostics':written,'outcomes':outcomes,'all_finite':True}
            (directory/'report.json').write_text(json.dumps(report,indent=2)+'\n');reports.append(report)
            print(json.dumps({'rate':rate,'phrase':case,'outcomes':outcomes,'seconds':time.monotonic()-began}),flush=True)
    sensitivity=[]
    for case in range(12):
        a,b=reports[case],reports[case+12]
        sensitivity.append({'phrase':case,'relative_primary_difference':[abs(a['outcomes'][r]['rms_hz']['connected']-b['outcomes'][r]['rms_hz']['connected'])/b['outcomes'][r]['rms_hz']['connected'] for r in (0,1)]})
    summary={'finished_utc':datetime.now(timezone.utc).isoformat(),'seconds':time.monotonic()-began,
             'all_admitted':all(o['admitted'] for r in reports for o in r['outcomes']),
             'primary_ranges_hz':{str(rate):[{key:float(fn([r['outcomes'][receiver]['rms_hz']['connected'] for r in reports if r['rate']==rate])) for key,fn in [('minimum',np.min),('median',np.median),('maximum',np.max)]} for receiver in (0,1)] for rate in (96,192)},
             'timestep_sensitivity':sensitivity,'maximum_relative_timestep_discrepancy':max(x for row in sensitivity for x in row['relative_primary_difference'])}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    inventory=[{'path':str(path.relative_to(output)),'bytes':path.stat().st_size,'sha256':sha256(path)} for path in sorted(output.rglob('*')) if path.is_file()]
    (output/'manifest.json').write_text(json.dumps({'files':inventory,'source_sha256':hashes},indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='artifacts/studies/choir-transfer-001');main(parser.parse_args())
