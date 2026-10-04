"""Compare the complete history atlas at two integration timesteps."""
from pathlib import Path
import argparse
import json

import numpy as np
from scipy.spatial.distance import cdist
from scipy.stats import spearmanr

from studio.atlas_figures import conditional_distances
from studio.preserve import sha256
from studio.simulate import source_hashes


def main(args):
    root=Path(args.atlas)
    output=Path(args.output)
    output.mkdir(parents=True,exist_ok=False)
    source=source_hashes(output/"source")
    coarse=np.load(root/f"rate-{args.coarse}/atlas.npz")
    fine=np.load(root/f"rate-{args.fine}/atlas.npz")
    case_reports={rate:json.loads((root/f"rate-{rate}/report.json").read_text()) for rate in (args.coarse,args.fine)}
    configs=[{key:value for key,value in case_reports[rate]["config"].items() if key!="dt"}
             for rate in (args.coarse,args.fine)]
    if configs[0]!=configs[1]:
        raise ValueError("configuration differences extend beyond the timestep")
    if not np.array_equal(coarse["labels"],fine["labels"]):
        raise ValueError("atlas histories differ between rates")
    labels=coarse["labels"].tolist()
    a=coarse["pitch_hz"].reshape(len(labels),-1)
    b=fine["pitch_hz"].reshape(len(labels),-1)
    if a.shape!=b.shape:
        raise ValueError("probe shapes differ")
    cross=cdist(b,a)/np.sqrt(a.shape[1])
    predictions=np.argmin(cross,axis=1)
    own=np.diag(cross).copy()
    off=cross.copy()
    np.fill_diagonal(off,np.inf)
    margins=off.min(axis=1)-own
    upper=np.triu_indices(len(labels),1)
    da=coarse["distance_rms_hz"][upper]
    db=fine["distance_rms_hz"][upper]
    conditional={}
    for rate,data in ((args.coarse,coarse),(args.fine,fine)):
        summary,_=conditional_distances(data["labels"],data["distance_rms_hz"])
        conditional[str(rate)]=summary
    report={"source_sha256":source,"atlas_manifests":{
                str(rate):sha256(root/f"rate-{rate}/report.json") for rate in (args.coarse,args.fine)},
            "coarse_rate":args.coarse,"fine_rate":args.fine,"history_count":len(labels),
            "matching":{"procedure":"For each finer-timestep probe trajectory, select the nearest complete coarse-timestep trajectory by RMS pitch difference. No fitted parameters or trained classifier.",
                        "correct":int(np.count_nonzero(predictions==np.arange(len(labels)))),
                        "total":len(labels),"minimum_matching_margin_hz":float(margins.min()),
                        "median_same_history_difference_hz":float(np.median(own)),
                        "maximum_same_history_difference_hz":float(own.max()),
                        "cases":[{"history":label,"nearest_coarse_history":labels[int(predictions[i])],
                                  "own_distance_hz":float(own[i]),"nearest_other_distance_hz":float(off[i].min()),
                                  "margin_hz":float(margins[i])} for i,label in enumerate(labels)]},
            "pair_distances":{"spearman_rank_correlation":float(spearmanr(da,db).statistic),
                              "maximum_absolute_change_hz":float(np.abs(da-db).max()),
                              "maximum_relative_change":float((np.abs(da-db)/db).max())},
            "shared_tail_results":conditional,
            "study_feedback_override":.08,
            "grid_size":configs[0]["size"],
            "scope":"A deterministic comparison of the same exhaustive finite history set on one fixed grid. Template matching assesses this particular timestep change; it does not establish robustness to noise, unseen histories, spatial refinement or human audibility. Margins are observed distances, not rigorous error bounds."}
    np.savez_compressed(output/"comparison.npz",cross_timestep_rms_hz=cross,labels=coarse["labels"],
                        own_distance_hz=own,margin_hz=margins)
    (output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    compact={key:value for key,value in report.items() if key not in ("source_sha256","shared_tail_results")}
    compact["matching"]={key:value for key,value in report["matching"].items() if key!="cases"}
    print(json.dumps(compact,indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--atlas",default="artifacts/studies/history-atlas-001")
    parser.add_argument("--coarse",type=int,default=96)
    parser.add_argument("--fine",type=int,default=192)
    parser.add_argument("--output",default="artwork/analysis/history-refinement-001")
    main(parser.parse_args())
