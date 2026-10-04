"""Cross-language equation check and bounded benchmark. Run on the compute host."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import time

import numpy as np
import torch

from studio.material import MaterialConfig, PalimpsestMaterial


def check(size,dt,node):
    result=subprocess.run([node,'studio/live_material_check.mjs',str(size),str(dt)],
                          check=True,capture_output=True,text=True)
    measured=json.loads(result.stdout)
    material=PalimpsestMaterial(MaterialConfig(size=size,dt=dt,device='cpu',dtype='float64'))
    force=torch.zeros(12,dtype=torch.float64)
    started=time.perf_counter()
    for step in range(round(24/dt)):
        t=step*dt
        for m in range(12):
            local=t-m*.81
            force[m]=.26*math.sin(math.pi*local/5)**2 if 0<local<5 else 0
        material.step(force,forgetting=.075 if t>17 else .0008)
    errors={}
    for name,jsname in [('u','u'),('v','v'),('p','p'),('z','z'),('delay','delay'),('echo_phase','phase')]:
        reference=getattr(material,name).numpy().ravel()
        actual=np.asarray(measured['state'][jsname])
        errors[name]={'max_abs':float(np.max(np.abs(reference-actual))),
                      'rms':float(np.sqrt(np.mean((reference-actual)**2)))}
    assert all(x['max_abs']<1e-8 for x in errors.values()),errors
    assert measured['state']['steps']==material.steps
    assert measured['state']['index']==material.index
    return {'size':size,'dt':dt,'duration':24,'configuration':asdict(material.cfg),
            'field_errors':errors,'javascript_ms':measured['elapsed_ms'],
            'javascript_steps_per_second':measured['steps_per_second'],
            'python_ms':(time.perf_counter()-started)*1000,
            'javascript_invariants':{key:measured[key] for key in ('checkpoint_exact','invalid_import_atomic','silence_exact')},
            'diagnostics':material.diagnostics()}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--node',default='.tools/node/bin/node')
    parser.add_argument('--output',default='artifacts/analysis/live-material-001.json')
    args=parser.parse_args()
    torch.set_num_threads(2)
    results=[check(64,1/96,args.node),check(64,1/192,args.node),check(128,1/96,args.node)]
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'cases':results,
            'scope':'Same grid and equations, double-precision reference, 24-second forcing and forgetting. This is not a continuum or perceptual equivalence claim.'}
    target=Path(args.output)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
