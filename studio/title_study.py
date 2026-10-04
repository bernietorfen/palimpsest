"""Inspect typography against the actual opening, chapters and closing frames."""
from pathlib import Path
import argparse
import json

import numpy as np
from PIL import Image,ImageDraw

from studio.mesh_render import SheetRenderer
from studio.sheet_direction import sheet_camera
from studio.film import Lettering
from studio.simulate import source_hashes


def main(args):
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(out/"source")
    fields=np.load("artifacts/studies/performance-002/fields.npy",mmap_mode="r")
    renderer=SheetRenderer(1280,720)
    lettering=Lettering(1280,720)
    contact=Image.new("RGB",(1280,3*384),(10,12,14))
    records=[]
    for i,t in enumerate((5,12,75,219,363,427)):
        settings={**sheet_camera(t),"samples":64,"area_shadow":True}
        frame=renderer.draw(fields[t*24].astype(np.float32),**settings)
        frame=lettering.draw(frame,t)
        image=Image.fromarray(frame)
        image.save(out/f"frame-{t:03d}.png")
        image.thumbnail((640,360))
        x,y=(i%2)*640,(i//2)*384
        contact.paste(image,(x,y))
        ImageDraw.Draw(contact).text((x+8,y+364),f"{t}s",fill=(210,200,184))
        records.append({"time":t,"settings":settings,"render":renderer.last_stats})
    contact.save(out/"contact.jpg",quality=90)
    renderer.close()
    (out/"manifest.json").write_text(json.dumps({"source_sha256":hashes,"renders":records},indent=2)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="artwork/previews/title-003")
    main(parser.parse_args())
