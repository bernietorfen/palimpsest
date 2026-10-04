"""Inspect the complete buckling study with one fixed camera and lighting."""
from pathlib import Path
import json
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from studio.render import SculptureRenderer
from studio.simulate import source_hashes


def main():
    root=Path("artifacts/studies/buckling-001")
    out=Path("artwork/previews/buckling-look-001")
    out.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(out/"source")
    r=SculptureRenderer(800,500)
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",15)
    cases=sorted(p for p in root.iterdir() if p.name.startswith("b") and p.is_dir())
    records=[]
    for second in (160,278,420):
        sheet=Image.new("RGB",(1600,4*530),(10,12,14))
        for i,case in enumerate(cases):
            field=np.load(case/f"field-{second:03d}.npy")
            start=time.monotonic()
            im=Image.fromarray(r.draw(field,samples=8))
            im.save(out/f"{case.name}-{second:03d}.png")
            x=(i%2)*800;y=(i//2)*530
            sheet.paste(im,(x,y))
            ImageDraw.Draw(sheet).text((x+16,y+503),f"{case.name} / {second} seconds",font=font,fill=(196,181,160))
            records.append({"case":case.name,"time":second,"seconds":time.monotonic()-start})
        sheet.save(out/f"contact-{second:03d}.png")
    (out/"manifest.json").write_text(json.dumps({"source_sha256":hashes,"renders":records},indent=2)+"\n")
    r.close()
    print(json.dumps({"complete":True,"output":str(out)}),flush=True)


if __name__=="__main__":
    main()
