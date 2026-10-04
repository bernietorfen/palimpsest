"""Independent double precision check of the seven-body JavaScript trajectory."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np
import torch
from studio.choir_material import MaterialChoir, Port, port_footprint
from studio.choir_scene import load_scene, bridge_specs
from studio.material import MaterialConfig


def main(args):
    torch.set_num_threads(2)
    measured=json.loads(Path(args.input).read_text())
    scene=load_scene()
    cfg=MaterialConfig(size=32,dt=1/96,device='cpu',dtype='float64',feedback=.08)
    choir=MaterialChoir(cfg,7,bridge_specs(scene),beads=scene['bridge']['beads'])
    points=[port_footprint(Port(1,.22,.5,.16),32,device='cpu',dtype=torch.float64),
            port_footprint(Port(3,.63,.4,.16),32,device='cpu',dtype=torch.float64)]
    samples={row['step']:row for row in measured['snapshots']}
    drive=torch.zeros((7,12),dtype=torch.float64)
    external=torch.zeros((7,32,32),dtype=torch.float64)
    errors=[]
    for step in range(2304):
        external.zero_()
        if step<480: external[1]=points[0]*1.1
        if 960<=step<1440: external[3]=points[1]*-.8
        if step==1440: choir.set_connections([0.]*12)
        if step==1728:
            choir.wave.reset_motion(choir.material.u)
            choir.set_connections([1.]*12)
        choir.step(drive,contact_force=external)
        if step+1 in samples:
            js=samples[step+1]
            comparisons={'fields':(choir.fields().numpy().astype(np.float32).ravel(),js['fields']),
                         'bridge_u':(choir.wave.u.numpy().ravel(),js['bridgeU']),
                         'bridge_v':(choir.wave.v.numpy().ravel(),js['bridgeV']),
                         'pitch':(choir.readout()['pitch_hz'].numpy(),[r['pitch'] for r in js['readout']])}
            result={'step':step+1}
            for key,(a,b) in comparisons.items():
                result[key]=float(np.max(np.abs(a-np.asarray(b))))
                assert result[key]<2e-7,(step+1,key,result[key])
            errors.append(result)
    report={'verified_utc':datetime.now(timezone.utc).isoformat(),'states':errors,
            'scope':'24 seconds, seven bodies, twelve bridges, opposite-polarity contacts, disconnection, new bridge initialization. Same 32-grid double precision equations; rendered field packets are float32. Not a continuum or perceptual comparison.',
            'javascript_realtime_ratio_on_runpod_cpu':measured['realtime_ratio'],
            'exact_continuation':measured['exact_continuation'],'atomic_rejection':measured['atomic_rejection']}
    output=Path(args.output)
    with output.open('x') as f: json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',default='artifacts/studies/choir-live-001.json')
    parser.add_argument('--output',default='research/choir-live-equations-001.json')
    main(parser.parse_args())
