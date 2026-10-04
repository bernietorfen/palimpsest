"""Fixed-state comparisons of material, camera, and depth of field."""
from pathlib import Path
import hashlib
import json
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from studio.render import SculptureRenderer
from studio.simulate import source_hashes


def main():
    out=Path("artwork/previews/direction-001")
    out.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(out/"source")
    field_path=Path("artifacts/studies/performance-001/field-0200.0.npy")
    field=np.load(field_path)
    r=SculptureRenderer(1280,800)
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",17)
    cameras={"portrait":dict(camera=(4.8,2.8,4.8)),
             "interior":dict(camera=(2.1,1.2,2.4),target=(.45,.1,.1),lens_radius=.035),
             "edge":dict(camera=(1.8,1.3,2.1),target=(.68,.19,.35),turn=1.3,lens_radius=.028)}
    records=[]
    for ci,(camera_name,params) in enumerate(cameras.items()):
        sheet=Image.new("RGB",(1280*3,838),(10,12,14))
        for style in (0,1,2):
            settings={"style":style,"samples":32,"light_angle":-.45,**params}
            began=time.monotonic()
            im=Image.fromarray(r.draw(field,**settings))
            name=f"{camera_name}-style-{style}.png"
            im.save(out/name)
            sheet.paste(im,(style*1280,0))
            ImageDraw.Draw(sheet).text((style*1280+18,808),f"{camera_name} / material {style}",font=font,fill=(202,185,161))
            records.append({"path":name,"settings":settings,"seconds":time.monotonic()-began})
        sheet.save(out/f"contact-{camera_name}.png")
    (out/"manifest.json").write_text(json.dumps({"source_sha256":hashes,
        "field_sha256":hashlib.sha256(field_path.read_bytes()).hexdigest(),"renders":records},indent=2)+"\n")
    print(json.dumps(records,indent=2),flush=True)
    r.close()


if __name__=="__main__":
    main()
