"""Review the complete camera score against the explicit sheet geometry."""
from pathlib import Path
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from studio.cinematography import camera_at, shot_name
from studio.mesh_render import SheetRenderer
from studio.simulate import source_hashes


def sheet_camera(t):
    settings=camera_at(t)
    for key in ("design","style","aperture"):
        settings.pop(key,None)
    return {**settings,"palette":0,"shadow_softness":1.}


def main():
    out=Path("artwork/previews/sheet-direction-001")
    out.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(out/"source")
    fields=np.load("artifacts/studies/performance-002/fields.npy",mmap_mode="r")
    times=(5,20,55,80,115,135,165,195,225,250,280,308,335,355,380,410,428)
    renderer=SheetRenderer(960,540)
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",13)
    contact=Image.new("RGB",(1600,5*246),(10,12,14))
    records=[]
    for i,t in enumerate(times):
        settings=sheet_camera(t)
        image=Image.fromarray(renderer.draw(fields[t*24].astype(np.float32),samples=16,**settings))
        image.save(out/f"frame-{t:03d}.png")
        image.thumbnail((400,225),Image.Resampling.LANCZOS)
        x,y=(i%4)*400,(i//4)*246
        contact.paste(image,(x,y))
        ImageDraw.Draw(contact).text((x+8,y+228),f"{t:03d}s / {shot_name(t)}",font=font,fill=(210,200,184))
        records.append({"time":t,"settings":settings,"render":renderer.last_stats})
    contact.save(out/"contact.jpg",quality=87)
    renderer.close()
    renderer=SheetRenderer(3840,2160,shadow_size=4096,nu=256,nv=512)
    for t in (20,165,335):
        settings=sheet_camera(t)
        frame=renderer.draw(fields[t*24].astype(np.float32),samples=64,**settings)
        im=Image.fromarray(frame)
        im.save(out/f"4k-{t:03d}.png")
        im.crop((1120,630,2720,1530)).save(out/f"crop-{t:03d}.jpg",quality=94)
        records.append({"time":t,"settings":settings,"render":renderer.last_stats})
        print(json.dumps(records[-1]),flush=True)
    renderer.close()
    (out/"manifest.json").write_text(json.dumps({"source_sha256":hashes,"renders":records},indent=2)+"\n")


if __name__=="__main__":
    main()
