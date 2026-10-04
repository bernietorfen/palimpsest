"""Sculptural alternative: the material as an open rolled sheet."""
from pathlib import Path
import json
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from studio.render import SculptureRenderer
from studio.simulate import source_hashes


def main():
    out=Path("artwork/previews/folio-001")
    out.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(out/"source")
    fields=np.load("artifacts/studies/performance-002/fields.npy",mmap_mode="r")
    r=SculptureRenderer(1120,700)
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",16)
    times=(0,70,160,245,358,420)
    records=[]
    for turn in (.3,1.6):
        sheet=Image.new("RGB",(2240,3*734),(10,12,14))
        for i,t in enumerate(times):
            params=dict(design=4,style=3,samples=32,turn=turn,light_angle=.25,
                        camera=(5.4,3.2,5.6),lens_radius=.004)
            began=time.monotonic()
            im=Image.fromarray(r.draw(fields[t*24].astype(np.float32),**params))
            path=f"turn-{turn:.1f}-{t:03d}.png"
            im.save(out/path)
            x=(i%2)*1120;y=(i//2)*734
            sheet.paste(im,(x,y))
            ImageDraw.Draw(sheet).text((x+16,y+705),f"{t:03d} s / a continuous rolled chart",font=font,fill=(202,185,161))
            records.append({"path":path,"time":t,"settings":params,"seconds":time.monotonic()-began})
        sheet.save(out/f"contact-turn-{turn:.1f}.png")
    params=dict(design=4,style=3,samples=96,turn=.3,light_angle=.25,
                camera=(3.1,1.9,3.3),target=(.25,.1,0.),lens_radius=.007)
    im=r.draw(fields[160*24].astype(np.float32),**params)
    Image.fromarray(im).save(out/"macro.png")
    (out/"manifest.json").write_text(json.dumps({"source_sha256":hashes,"renders":records},indent=2)+"\n")
    print(json.dumps({"complete":True,"output":str(out)}),flush=True)
    r.close()


if __name__=="__main__":
    main()
