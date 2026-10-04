"""Review soft shadows at actual master resolution before rendering motion."""
from pathlib import Path
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from studio.mesh_geometry import build_sheet
from studio.mesh_render import SheetRenderer
from studio.sheet_direction import sheet_camera
from studio.simulate import source_hashes


def main():
    out=Path("artwork/previews/lighting-001")
    out.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(out/"source")
    fields=np.load("artifacts/studies/performance-002/fields.npy",mmap_mode="r")
    renderer=SheetRenderer(3840,2160,shadow_size=4096,nu=256,nv=512)
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",16)
    contact=Image.new("RGB",(1600,3*485),(10,12,14))
    field=fields[165*24].astype(np.float32)
    mesh=build_sheet(field,nu=256,nv=512)
    records=[]
    variants=((False,64,1.),(True,64,1.),(True,128,1.),(True,256,1.),(True,128,1.5),(True,128,.6))
    for i,(area,samples,softness) in enumerate(variants):
        settings=sheet_camera(165)
        settings.update(area_shadow=area,samples=samples,shadow_softness=softness)
        frame=renderer.draw(field,mesh=mesh,**settings)
        im=Image.fromarray(frame)
        im.save(out/f"variant-{i}.png")
        crop=im.crop((1120,630,2720,1530))
        crop.save(out/f"crop-{i}.jpg",quality=95)
        crop.thumbnail((800,450),Image.Resampling.LANCZOS)
        x,y=(i%2)*800,(i//2)*485
        contact.paste(crop,(x,y))
        ImageDraw.Draw(contact).text((x+12,y+458),f"area={area} / {samples} samples / radius scale {softness}",font=font,fill=(210,200,184))
        records.append({"settings":settings,"render":renderer.last_stats})
        print(json.dumps(records[-1]),flush=True)
    contact.save(out/"contact.jpg",quality=89)
    renderer.close()
    (out/"manifest.json").write_text(json.dumps({"source_sha256":hashes,"renders":records},indent=2)+"\n")


if __name__=="__main__":
    main()
