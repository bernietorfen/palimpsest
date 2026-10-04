"""A bounded material study: fatigue-triggered buckling, not texture noise."""
from dataclasses import asdict
from pathlib import Path
import json
import time

import numpy as np
import torch

from studio.material import MaterialConfig, PalimpsestMaterial, laplacian
from studio.score import Score
from studio.simulate import source_hashes


def main():
    torch.set_num_threads(2)
    output=Path("artifacts/studies/buckling-001")
    output.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(output/"source")
    score=Score()
    summary=[]
    for buckling,bending in ((0.,.8),(3.,.8),(4.,.8),(5.,.8),(6.,.8),(5.,1.5),(6.,1.5),(7.,1.5)):
        name=f"b{buckling:.1f}-k{bending:.1f}"
        out=output/name
        out.mkdir()
        config=MaterialConfig(size=128,buckling=buckling,bending=bending)
        m=PalimpsestMaterial(config)
        snapshots=(60,110,160,200,240,278,320,358,420)
        stats=[]
        began=time.monotonic()
        for step in range(round(432/config.dt)):
            t=step*config.dt
            m.step(torch.as_tensor(score.excitation(t),device=m.device),**score.controls(t))
            if (step+1) % 96 == 0:
                second=(step+1)//96
                if second in snapshots:
                    np.save(out/f"field-{second:03d}.npy",m.fields().cpu().numpy())
                    info=m.diagnostics()
                    info["laplacian_rms"]=float(laplacian(m.u).square().mean().sqrt())
                    stats.append(info)
                if second%36==0:
                    info=m.diagnostics()
                    print(json.dumps({"case":name,**info}),flush=True)
                    if not info["finite"] or info["max_displacement"]>12:
                        raise FloatingPointError(f"Unstable material {name}")
        record={"name":name,"config":asdict(config),"snapshots":stats,
                "elapsed_seconds":time.monotonic()-began}
        (out/"manifest.json").write_text(json.dumps(record,indent=2)+"\n")
        summary.append(record)
        (output/"summary.json").write_text(json.dumps({"source_sha256":hashes,"cases":summary},indent=2)+"\n")
    print(json.dumps({"complete":True,"cases":len(summary)}),flush=True)


if __name__=="__main__":
    main()
