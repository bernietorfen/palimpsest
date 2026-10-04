"""An exhaustive atlas of all orders of one five-gesture writing multiset.

The material rule is reused unchanged. Every case receives the same later probe
after transient reset. These are deterministic readouts, not perceptual tests.
"""
from dataclasses import asdict
from datetime import datetime,timezone
from itertools import permutations
from pathlib import Path
import argparse
import json
import time

import numpy as np
from scipy.spatial.distance import pdist,squareform
import torch

from studio.assay import relax
from studio.material import MaterialConfig,PalimpsestMaterial
from studio.numerical_assay import record,difference
from studio.preserve import sha256
from studio.simulate import source_hashes


VOICES=(0,4,2,7,3)
SYMBOLS="ABCDE"
PROBE=(1,5,2)


def summarize(trajectories,labels):
    pitches=np.stack([result["pitch_hz"] for result in trajectories]).astype(np.float64)
    features=pitches.reshape(len(labels),-1)
    distances=squareform(pdist(features,metric="euclidean"))/np.sqrt(features.shape[1])
    upper=np.triu_indices(len(labels),1)
    values=distances[upper]
    least=np.argmin(values)
    greatest=np.argmax(values)
    centered=features-features.mean(axis=0)
    u,s,vh=np.linalg.svd(centered,full_matrices=False)
    projection=u[:,:2]*s[:2]
    explained=s[:2]**2/np.sum(s*s)
    nearest=[]
    for i,label in enumerate(labels):
        row=distances[i].copy()
        row[i]=np.inf
        j=int(np.argmin(row))
        nearest.append({"history":label,"nearest":labels[j],"rms_hz":float(row[j])})
    report={"case_count":len(labels),"pair_count":len(values),
            "all_pitch_values_finite":bool(np.isfinite(pitches).all()),
            "minimum_pair_rms_hz":float(values[least]),"maximum_pair_rms_hz":float(values[greatest]),
            "median_pair_rms_hz":float(np.median(values)),
            "minimum_pair":[labels[upper[0][least]],labels[upper[1][least]]],
            "maximum_pair":[labels[upper[0][greatest]],labels[upper[1][greatest]]],
            "pairs_below_1e_minus_6_hz":int(np.count_nonzero(values<1e-6)),
            "projection_variance_fractions":explained.tolist(),"nearest_neighbors":nearest,
            "distance_definition":"RMS frequency difference over 336 probe samples at 24 Hz and all 12 authored voices. Includes readouts of voices not currently excited by the probe.",
            "projection_definition":"Ordinary two-component PCA of the centered full probe pitch trajectories; an overview that loses the remaining variance, not an isometric map."}
    return report,{"pitch_hz":pitches,"distance_rms_hz":distances,"projection":projection,
                   "singular_values":s,"projection_components":vh[:2]}


def main(args):
    torch.set_num_threads(2)
    output=Path(args.output)
    output.mkdir(parents=True,exist_ok=False)
    source=source_hashes(output/"source")
    began=time.monotonic()
    orders=list(permutations(range(5)))
    labels=["".join(SYMBOLS[i] for i in order) for order in orders]
    all_trajectories={}
    reports={}
    for rate in args.rates:
        config=MaterialConfig(size=args.size,dt=1/rate)
        directory=output/f"rate-{rate}"
        directory.mkdir()
        trajectories=[]
        records=[]
        retained_first=None
        for index,(order,label) in enumerate(zip(orders,labels)):
            model=PalimpsestMaterial(config)
            sequence=tuple(VOICES[i] for i in order)
            record(model,24.,sequence)
            p=model.p.cpu().numpy().copy()
            z=model.z.cpu().numpy().copy()
            if retained_first is None:
                retained_first=(p,z)
            relax(model)
            result=record(model,14.,PROBE)
            if not all(np.isfinite(values).all() for values in result.values()):
                raise ValueError(f"non-finite readout at {rate} / {label}")
            path=directory/f"{label}.npz"
            np.savez_compressed(path,**result,retained_p=p,retained_z=z)
            trajectories.append(result)
            records.append({"label":label,"voices":sequence,"sha256":sha256(path),
                            "retained_memory_rms":float(np.sqrt(np.mean(p.astype(float)**2))),
                            "retained_fatigue_mean":float(np.mean(z.astype(float)))})
            print(json.dumps({"rate":rate,"case":index+1,"of":len(orders),"label":label,
                              "seconds":round(time.monotonic()-began,2)}),flush=True)
        fresh=PalimpsestMaterial(config)
        record(fresh,24.,())
        relax(fresh)
        fresh_result=record(fresh,14.,PROBE)
        erased=PalimpsestMaterial(config)
        erased.p=torch.as_tensor(retained_first[0],device=erased.device).clone()
        erased.z=torch.as_tensor(retained_first[1],device=erased.device).clone()
        relax(erased,erase=True)
        erased_result=record(erased,14.,PROBE)
        control=difference(erased_result,fresh_result)
        if any(value["max_absolute"]!=0 for value in control.values()):
            raise ValueError("erased state failed the exact fresh-state control")
        np.savez_compressed(directory/"fresh.npz",**fresh_result)
        np.savez_compressed(directory/"erased.npz",**erased_result)
        summary,arrays=summarize(trajectories,labels)
        arrays["fresh_pitch_hz"]=fresh_result["pitch_hz"]
        arrays["labels"]=np.array(labels)
        np.savez_compressed(directory/"atlas.npz",**arrays)
        report={"config":asdict(config),"cases":records,"summary":summary,"erasure_control":control}
        (directory/"report.json").write_text(json.dumps(report,indent=2)+"\n")
        all_trajectories[rate]=arrays["pitch_hz"]
        reports[str(rate)]=summary
    sensitivity={}
    for coarse,fine in zip(args.rates[:-1],args.rates[1:]):
        delta=all_trajectories[coarse]-all_trajectories[fine]
        rms=np.sqrt(np.mean(delta*delta,axis=(1,2)))
        sensitivity[f"{coarse}_vs_{fine}"]={"case_rms_hz":dict(zip(labels,rms.tolist())),
            "median_case_rms_hz":float(np.median(rms)),"maximum_case_rms_hz":float(rms.max()),
            "scope":"A same-grid timestep comparison. This does not supply an error bound for the continuum or a threshold for human audibility."}
    report={"created_utc":datetime.now(timezone.utc).isoformat(),"source_sha256":source,
            "symbol_to_voice":dict(zip(SYMBOLS,VOICES)),"writing_seconds":24,"probe":PROBE,
            "probe_seconds":14,"readout_hz":24,"rates":args.rates,"size":args.size,
            "summaries":reports,"timestep_sensitivity":sensitivity,
            "elapsed_seconds":time.monotonic()-began,
            "protocol":"Every permutation of the same five writing gestures. Each starts from zero state. Reset u=p, v=0, delay=0, echo phase=0 before the identical probe. Preserve p,z, except in the erased control.",
            "scope":"An exhaustive finite set of authored input histories for this deterministic instrument. Numeric uniqueness does not establish audibility, robust information capacity, physical material behavior, or universal historical novelty. u=p removes local strain but is not necessarily spatial equilibrium."}
    (output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"finished":str(output),"seconds":report["elapsed_seconds"],
                      "summaries":{key:{k:v for k,v in value.items() if k!="nearest_neighbors"} for key,value in reports.items()}},indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="artifacts/studies/history-atlas-001")
    parser.add_argument("--rates",type=int,nargs="+",default=[96,192])
    parser.add_argument("--size",type=int,default=128)
    main(parser.parse_args())
