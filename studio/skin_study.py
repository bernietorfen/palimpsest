"""Does a state-driven opening make the material's history visually legible?"""
from pathlib import Path
import json
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from studio.render import SculptureRenderer
from studio.simulate import source_hashes


def main():
    out=Path("artwork/previews/skin-001")
    out.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(out/"source")
    fields=np.load("artifacts/studies/performance-002/fields.npy",mmap_mode="r")
    r=SculptureRenderer(1120,700)
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",16)
    times=(0,35,70,160,245,278,358,420)
    records=[]
    for style in (0,2):
        sheet=Image.new("RGB",(2240,4*734),(10,12,14))
        for i,t in enumerate(times):
            params=dict(design=3,style=style,samples=24,turn=.55,light_angle=.25,aperture=0.)
            began=time.monotonic()
            im=Image.fromarray(r.draw(fields[t*24].astype(np.float32),**params))
            path=f"style-{style}-{t:03d}.png"
            im.save(out/path)
            x=(i%2)*1120;y=(i//2)*734
            sheet.paste(im,(x,y))
            ImageDraw.Draw(sheet).text((x+16,y+705),f"{t:03d} s / windows follow retained fatigue",font=font,fill=(202,185,161))
            records.append({"path":path,"time":t,"settings":params,"seconds":time.monotonic()-began})
        sheet.save(out/f"contact-style-{style}.png")
    # Benchmark the actual master dimensions, without extrapolating from a thumbnail.
    r.close()
    r=SculptureRenderer(3840,2160)
    im=None
    for samples in (8,16,32):
        began=time.monotonic()
        im=r.draw(fields[245*24].astype(np.float32),design=3,style=0,samples=samples,
                  camera=(2.8,1.7,3.1),target=(.35,.1,.1),lens_radius=.016,aperture=0.)
        records.append({"benchmark":"3840x2160 macro","samples":samples,"seconds":time.monotonic()-began})
    Image.fromarray(im).save(out/"master-resolution-macro.png")
    (out/"manifest.json").write_text(json.dumps({"source_sha256":hashes,"renders":records},indent=2)+"\n")
    print(json.dumps(records[-3:],indent=2),flush=True)
    r.close()


if __name__=="__main__":
    main()
