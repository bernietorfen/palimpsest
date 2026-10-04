"""Time-step sensitivity and separate interventions on the two memory fields.

These are deterministic numerical experiments on an authored system. They are
not measurements of matter, confidence intervals, or a novelty proof.
"""
from dataclasses import asdict
from pathlib import Path
import argparse
import json
import time

import numpy as np
import torch

from studio.assay import excite, relax
from studio.material import MaterialConfig, PalimpsestMaterial
from studio.simulate import source_hashes


def record(model,seconds,sequence):
    stride=round(1/(24*model.cfg.dt))
    if abs(stride*model.cfg.dt-1/24)>1e-12:
        raise ValueError("this comparison requires exact 24 Hz readout alignment")
    curves={}
    for step in range(round(seconds/model.cfg.dt)):
        if step%stride==0:
            for name,value in model.readout().items():
                curves.setdefault(name,[]).append(value.cpu().numpy())
        model.step(torch.as_tensor(excite(step*model.cfg.dt,sequence),device=model.device),feedback=.08)
    return {name:np.asarray(values) for name,values in curves.items()}


def difference(a,b):
    result={}
    for key in ("pitch_hz","velocity","memory","fatigue"):
        delta=a[key].astype(np.float64)-b[key].astype(np.float64)
        result[key]={"rms":float(np.sqrt(np.mean(delta*delta))),
                     "max_absolute":float(np.abs(delta).max())}
    return result


def main(args):
    torch.set_num_threads(2)
    output=Path(args.output)
    output.mkdir(parents=True,exist_ok=False)
    source=source_hashes(output/"source")
    began=time.monotonic()
    histories={"forward":(0,4,2,7,3),"reverse":(3,7,2,4,0)}
    trajectories={}
    retained={}
    for rate in (96,192,384):
        config=MaterialConfig(dt=1/rate)
        for name,history in histories.items():
            model=PalimpsestMaterial(config)
            record(model,24.,history)
            if rate==96 and name=="forward":
                retained=model.state_dict()
            relax(model)
            result=record(model,14.,(1,5,2))
            trajectories[(rate,name)]=result
            np.savez_compressed(output/f"dt-{rate}-{name}.npz",**result)
            print(json.dumps({"completed":f"dt-{rate}-{name}","seconds":time.monotonic()-began}),flush=True)
    sensitivity={}
    for rate in (96,192,384):
        sensitivity[str(rate)]={"dt":1/rate,
            "forward_vs_reverse":difference(trajectories[(rate,"forward")],trajectories[(rate,"reverse")])}
    convergence={}
    for coarse,fine in ((96,192),(192,384),(96,384)):
        convergence[f"{coarse}_vs_{fine}"]={name:difference(trajectories[(coarse,name)],trajectories[(fine,name)])
                                              for name in histories}
    interventions={}
    for label in ("intact","erase_p","erase_z","erase_both","fresh"):
        model=PalimpsestMaterial(MaterialConfig())
        if label!="fresh":
            model.load_state_dict(retained)
        if label in ("erase_p","erase_both"):
            model.p.zero_()
        if label in ("erase_z","erase_both"):
            model.z.zero_()
        relax(model)
        np.save(output/f"initial-{label}.npy",model.fields().cpu().numpy())
        result=record(model,14.,(1,5,2))
        interventions[label]=result
        np.savez_compressed(output/f"probe-{label}.npz",**result)
    controls={}
    for a,b in (("intact","erase_p"),("intact","erase_z"),("intact","fresh"),
                ("erase_p","fresh"),("erase_z","fresh"),("erase_both","fresh")):
        controls[f"{a}_vs_{b}"]=difference(interventions[a],interventions[b])
    report={"source_sha256":source,"config":asdict(MaterialConfig()),
            "histories":histories,"history_seconds":24,"probe":[1,5,2],"probe_seconds":14,
            "readout_fps":24,"time_step_sensitivity":sensitivity,"trajectory_differences":convergence,
            "field_interventions":controls,"seconds":time.monotonic()-began,
            "scope":"Fixed 128 x 128 grid. Temporal sensitivity only; no spatial convergence or global stability proof. Reset u=p, v=0, delay=0, echo_phase=0. This is zero local strain, not necessarily spatial equilibrium. Deterministic results, not statistical estimates."}
    (output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="source_sha256"},indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="artifacts/studies/numerical-assay-001")
    main(parser.parse_args())
