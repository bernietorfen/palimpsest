"""Large original print plates and a matched first/return diptych."""
from pathlib import Path
import argparse
import json

import numpy as np
from PIL import Image,ImageDraw,ImageFont

from studio.mesh_render import SheetRenderer
from studio.sheet_direction import sheet_camera
from studio.simulate import source_hashes
from studio.preserve import sha256


def main(args):
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(out/"source")
    fields=np.load("artifacts/studies/performance-002/fields.npy",mmap_mode="r")
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",17)
    records=[]
    renderer=None if args.only_diptych else SheetRenderer(8000,10000,shadow_size=4096,nu=384,nv=768)
    print_states=() if args.only_diptych else ((30,"01-impression",.55),(165,"02-inscription",.3),(358,"03-remnant",.55))
    for t,name,turn in print_states:
        settings=dict(camera=(5.6,3.25,5.9),turn=turn,samples=128,area_shadow=True,
                      light_angle=.25,exposure=1.1,lens_radius=.003)
        frame=renderer.draw(fields[t*24].astype(np.float32),**settings)
        im=Image.fromarray(frame)
        path=out/f"{name}.png"
        im.save(path,dpi=(300,300))
        im.crop((3000,4000,4600,4900)).save(out/f"{name}-crop.jpg",quality=94)
        im.thumbnail((1440,1800),Image.Resampling.LANCZOS)
        im.save(out/f"{name}-view.jpg",quality=91)
        records.append({"time":t,"name":name,"settings":settings,"render":renderer.last_stats,
                        "bytes":path.stat().st_size,"sha256":sha256(path)})
        print(json.dumps(records[-1]),flush=True)
    if renderer is not None:
        renderer.close()
    renderer=SheetRenderer(3200,4000,shadow_size=4096,nu=256,nv=512)
    for t,name in ((30,"question-first"),(382,"question-return")):
        settings=sheet_camera(t)
        # Equal framing in the portrait pair, with room around the full outline.
        settings["focal_length"]*=.88
        settings.update(samples=128,area_shadow=True)
        frame=renderer.draw(fields[t*24].astype(np.float32),**settings)
        im=Image.fromarray(frame)
        path=out/f"{name}.png"
        im.save(path,dpi=(300,300))
        im.thumbnail((1200,1500),Image.Resampling.LANCZOS)
        im.save(out/f"{name}-view.jpg",quality=91)
        records.append({"time":t,"name":name,"settings":settings,"render":renderer.last_stats,
                        "bytes":path.stat().st_size,"sha256":sha256(path)})
    renderer.close()
    columns=min(3,len(records))
    rows=(len(records)+columns-1)//columns
    contact=Image.new("RGB",(columns*500,rows*650),(10,12,14))
    for i,record in enumerate(records):
        im=Image.open(out/f"{record['name']}-view.jpg")
        im.thumbnail((500,610),Image.Resampling.LANCZOS)
        x,y=(i%columns)*500,(i//columns)*650
        contact.paste(im,(x+(500-im.width)//2,y))
        ImageDraw.Draw(contact).text((x+12,y+618),f"{record['name']} / {record['time']} s",font=font,fill=(210,200,184))
    contact.save(out/"contact.jpg",quality=88)
    (out/"manifest.json").write_text(json.dumps({"source_sha256":hashes,"plates":records,
        "scope":"Original renderings of the recorded material; RGB raster prints, 300 dpi metadata. The question diptych reuses an identical camera and light path."},indent=2)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="artwork/masters/plates-001")
    parser.add_argument("--only-diptych",action="store_true")
    main(parser.parse_args())
