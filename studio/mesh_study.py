"""Controlled look and topology study for the explicitly modelled sheet."""
from pathlib import Path
import argparse
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from studio.mesh_geometry import build_sheet, topology_report
from studio.mesh_render import SheetRenderer
from studio.simulate import source_hashes


def main(args):
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(out/"source")
    fields=np.load("artifacts/studies/performance-002/fields.npy",mmap_mode="r")
    renderer=SheetRenderer(1280,800,shadow_size=2048,nu=192,nv=384)
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",16)
    contact=Image.new("RGB",(1440,3*330),(10,12,14))
    records=[]
    for row,t in enumerate((0,160,358)):
        field=fields[t*24].astype(np.float32)
        mesh=build_sheet(field,nu=192,nv=384)
        report=topology_report(mesh)
        for col,palette in enumerate((0,1,2)):
            settings=dict(turn=.3,palette=palette,samples=12,shadow_softness=1.,
                          lens_radius=.003,camera=(5.4,3.2,5.6))
            frame=renderer.draw(field,mesh=mesh,**settings)
            name=f"state-{t:03d}-palette-{palette}.png"
            im=Image.fromarray(frame)
            im.save(out/name)
            im.thumbnail((480,300),Image.Resampling.LANCZOS)
            contact.paste(im,(col*480,row*330))
            ImageDraw.Draw(contact).text((col*480+12,row*330+305),f"{t:03d}s / palette {palette}",font=font,fill=(210,200,184))
            record={"path":name,"time":t,"settings":settings,
                    "topology":report,"render":renderer.last_stats}
            records.append(record)
            print(json.dumps(record),flush=True)
    contact.save(out/"contact.jpg",quality=86)
    field=fields[160*24].astype(np.float32)
    for diagnostic in (1,2,3):
        frame=renderer.draw(field,samples=4,diagnostic=diagnostic)
        Image.fromarray(frame).save(out/f"diagnostic-{diagnostic}.png")
    renderer.close()
    (out/"manifest.json").write_text(json.dumps({"source_sha256":hashes,"renders":records},indent=2)+"\n")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="artwork/previews/mesh-001")
    main(parser.parse_args())
