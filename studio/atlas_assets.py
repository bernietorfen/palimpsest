"""A browsable, audible edition of the recorded exhaustive history atlas.

Every audio excerpt uses the recorded probe controls, the film's original
synthesizer, and one fixed gain. No runtime simulation or inference is required.
"""
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import subprocess

import numpy as np
from scipy.interpolate import CubicSpline

from studio.assay import excite
from studio.history_atlas import PROBE
from studio.preserve import sha256
from studio.simulate import source_hashes
from studio.sound import synthesize


def glyph_paths(deviations, scale):
    angles=np.linspace(0,2*np.pi,13)
    fine=np.linspace(0,2*np.pi,97)
    paths=[]
    for ring,values in enumerate(deviations):
        radius=.27+.21*ring+.18*CubicSpline(angles,np.r_[values,values[0]],bc_type="periodic")(fine)/scale
        points=np.column_stack((120+radius*np.sin(fine)*96,120-radius*np.cos(fine)*96))
        paths.append("M"+"L".join(f"{x:.2f},{y:.2f}" for x,y in points)+"Z")
    return paths


def main(args):
    source=Path(args.atlas)
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    source_hash=source_hashes(out/"source")
    controls=out/"controls"
    masters=out/"audio-masters"
    public=out/"public"
    for folder in (controls,masters,public):
        folder.mkdir()
    data=np.load(source/"atlas.npz")
    labels=data["labels"].tolist()
    if len(labels)!=120 or len(set(labels))!=120:
        raise ValueError("the edition requires the complete 120-history atlas")
    readings=data["pitch_hz"][:,[0,96,192,288],:]
    center=readings.mean(axis=0)
    deviations=readings-center
    scale=float(np.abs(deviations).max())
    records=[]
    public_cases=[]
    fresh_master=None
    for index,label in enumerate(labels+["fresh","erased"]):
        original=source/f"{label}.npz"
        with np.load(original) as readout:
            selected={key:readout[key] for key in ("pitch_hz","fatigue","amplitude","velocity")}
        count=selected["pitch_hz"].shape[0]
        if count!=336:
            raise ValueError("unexpected probe sample count")
        selected["time"]=np.arange(count,dtype=float)/24
        selected["drive"]=np.stack([excite(t,PROBE) for t in selected["time"]])
        prepared=controls/f"{label}.npz"
        np.savez_compressed(prepared,**selected)
        master=masters/f"{label}.wav"
        with (masters/f"{label}.log").open("w") as log,redirect_stdout(log):
            synthesize(argparse.Namespace(readouts=str(prepared),output=str(master),
                        sample_rate=48000,duration=None,fade_in=.12,fade_out=.8,fixed_gain=2.5))
        if label=="fresh":
            fresh_master=sha256(master)
        elif label=="erased":
            if sha256(master)!=fresh_master:
                raise ValueError("the erased control must reproduce the fresh audio byte for byte")
        else:
            public_cases.append({"label":label,"paths":glyph_paths(deviations[index],scale),
                "position":np.round(data["projection"][index]/np.sqrt(336*12),6).tolist(),
                "audio":f"probe-{label}.m4a"})
        if label!="erased":
            encoded=public/f"probe-{label}.m4a"
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-n",
                "-threads","2","-i",str(master),"-map","0:a:0","-c:a","aac","-b:a","96k",
                "-threads","2","-map_metadata","-1","-movflags","+faststart",str(encoded)],check=True)
        records.append({"label":label,"readout_sha256":sha256(original),
                        "prepared_control_sha256":sha256(prepared),"master_sha256":sha256(master)})
        print(json.dumps({"case":index+1,"of":122,"label":label}),flush=True)
    packet={"version":1,"title":"120 possible pasts","case_count":120,"readout_hz":24,
            "probe_seconds":14,"audio_seconds":335/24,"audio_gain":2.5,
            "glyph_times":[0,4,8,12],"glyph_scale_hz":scale,
            "cases":public_cases,"distances":np.round(data["distance_rms_hz"],7).tolist(),
            "fresh":{"audio":"probe-fresh.m4a","paths":glyph_paths(data["fresh_pitch_hz"][[0,96,192,288]]-center,scale)},
            "definition":"RMS pitch difference across 336 recorded samples and all 12 voices, including voices not currently excited. Numeric distance is not a listening score.",
            "audio_note":"Actual recorded probe readouts rendered with the original film synthesizer. Every case uses the same gain, room and fades. Audio ends at the last available control sample, 13.958333 seconds; no missing endpoint is invented.",
            "glyph_note":"Four periodic cubic splines sampled into 96 line segments each. Directions represent 12 voices; rings represent 0, 4, 8 and 12 seconds. Radial difference is relative to the 120-history mean at the same time. One scale is shared by all histories.",
            "atlas_sha256":sha256(source/"atlas.npz")}
    (public/"histories.json").write_text(json.dumps(packet,separators=(",",":"),allow_nan=False)+"\n")
    inventory=[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha256(p)} for p in sorted(public.iterdir())]
    report={"created_utc":datetime.now(timezone.utc).isoformat(),"source_sha256":source_hash,
            "atlas_sha256":packet["atlas_sha256"],"cases":records,"files":inventory,
            "total_asset_bytes":sum(x["bytes"] for x in inventory),
            "fresh_erased_master_exact_match":True,"audio_seconds":335/24,"fixed_gain":2.5,
            "fade_in_seconds":.12,"fade_out_seconds":.8,"encoding":"AAC stereo, 48 kHz, 96 kbit/s",
            "scope":"Recorded responses of an authored deterministic instrument. No claim that all pairs are audibly distinguishable. Synthesis uses the same room, seed and fixed gain in every case; this archive is not a blinded listening study."}
    (public/"manifest.json").write_text(json.dumps({"files":inventory},indent=2)+"\n")
    (out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"complete":str(out),"public_bytes":report["total_asset_bytes"],
                      "fresh_erased_master_exact_match":True}),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--atlas",default="artifacts/studies/history-atlas-001/rate-96")
    parser.add_argument("--output",default="artwork/atlas-edition-001")
    main(parser.parse_args())
