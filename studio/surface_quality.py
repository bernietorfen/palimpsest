"""Separate field precision, normal sampling, ray stepping, and shadow defects."""
from pathlib import Path
import json
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from studio.render import SculptureRenderer
from studio.simulate import source_hashes


def main():
    out=Path("artwork/previews/surface-quality-001")
    out.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(out/"source")
    root=Path("artifacts/studies/performance-002")
    precise=np.load(root/"field-0160.0.npy")
    compact=np.load(root/"fields.npy",mmap_mode="r")[160*24].astype(np.float32)
    r=SculptureRenderer(1280,800)
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",16)
    common=dict(design=4,style=3,samples=48,turn=.3,light_angle=.25,
                camera=(3.1,1.9,3.3),target=(.25,.1,0.),lens_radius=0.)
    variants=(
        ("recorded / soft shadow",compact,{}),
        ("float32 / soft shadow",precise,{}),
        ("float32 / normal step 0.0006",precise,{"normal_step":.0006}),
        ("float32 / slower ray",precise,{"march_scale":.35,"normal_step":.0006}),
        ("float32 / no shadow",precise,{"shadow_mode":0,"normal_step":.0006}),
        ("float32 / diffuse diagnostic",precise,{"diagnostic":2,"normal_step":.0006}),
        ("float32 / traced area light",precise,{"shadow_mode":2,"normal_step":.0006}),
        ("float32 / area light / slower ray",precise,{"shadow_mode":2,"normal_step":.0006,"march_scale":.5}),
    )
    sheet=Image.new("RGB",(2560,4*834),(10,12,14))
    records=[];frames=[]
    for i,(name,field,options) in enumerate(variants):
        began=time.monotonic()
        params={**common,**options}
        frame=r.draw(field,**params)
        frames.append(frame)
        im=Image.fromarray(frame)
        im.save(out/f"variant-{i}.png")
        x=(i%2)*1280;y=(i//2)*834
        sheet.paste(im,(x,y))
        ImageDraw.Draw(sheet).text((x+16,y+805),name,font=font,fill=(202,185,161))
        records.append({"name":name,"settings":params,"seconds":time.monotonic()-began})
    sheet.save(out/"contact.png")
    comparisons=[]
    for a,b in ((0,1),(1,2),(2,3),(6,7)):
        diff=np.abs(frames[a].astype(np.float32)-frames[b].astype(np.float32))
        comparisons.append({"variants":[a,b],"mean_absolute_difference_8bit":float(diff.mean()),
                            "fraction_pixels_difference_over_8":float((diff.max(axis=2)>8).mean())})
    (out/"manifest.json").write_text(json.dumps({"source_sha256":hashes,"renders":records,
                                               "comparisons":comparisons},indent=2)+"\n")
    print(json.dumps(comparisons,indent=2),flush=True)
    r.close()


if __name__=="__main__":
    main()
