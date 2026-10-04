"""Render contact sheets on RunPod for actual visual decisions."""
from pathlib import Path
import argparse
import json
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from studio.render import SculptureRenderer


def main(args):
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=True)
    data=np.load(args.fields,mmap_mode="r")
    renderer=SculptureRenderer(960,600)
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",16)
    times=(30,60,110,200,278,358,395,420)
    sheet=Image.new("RGB",(1920,4*644),(10,12,14))
    records=[]
    for i,t in enumerate(times):
        started=time.monotonic()
        field=data[min(round(t*24),len(data)-1)].astype(np.float32)
        frame=Image.fromarray(renderer.draw(field,turn=.4+(i%3)*.7,samples=8))
        path=out/f"moment-{t:03d}.png"
        frame.save(path)
        x=(i%2)*960;y=(i//2)*644
        sheet.paste(frame,(x,y))
        d=ImageDraw.Draw(sheet)
        d.text((x+22,y+613),f"{t:03d} sec  /  material field, memory, fatigue",font=font,fill=(184,176,159))
        records.append({"time":t,"path":str(path),"render_seconds":time.monotonic()-started})
    sheet.save(out/"contact.png")
    field=data[round(60*24)].astype(np.float32)
    for diagnostic in (1,2):
        frame=renderer.draw(field,samples=8,diagnostic=diagnostic)
        Image.fromarray(frame).save(out/f"diagnostic-{diagnostic}.png")
    (out/"renders.json").write_text(json.dumps(records,indent=2)+"\n")
    print(json.dumps(records,indent=2),flush=True)
    renderer.close()


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--fields",default="artifacts/studies/performance-001/fields.npy")
    parser.add_argument("--output",default="artwork/previews/look-003")
    main(parser.parse_args())
