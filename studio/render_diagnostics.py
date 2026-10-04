"""Separate simulation texture from numerical renderer effects."""
from pathlib import Path
import argparse
import json

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from studio.render import SculptureRenderer


def main(args):
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    data=np.load("artifacts/studies/material-001/field-0060.0.npy")
    x=np.arange(128)*2*np.pi/128
    y,x=np.meshgrid(x,x,indexing="ij")
    analytic=np.zeros_like(data)
    analytic[:,:,0]=np.sin(x*3+y)*.3
    analytic[:,:,1]=np.cos(x*2-y*2)*.2
    variants={"zero":np.zeros_like(data),"analytic":analytic,"actual":data,
              "filtered":gaussian_filter(data,(1.7,1.7,0),mode="wrap")}
    r=SculptureRenderer(960,600)
    sheet=Image.new("RGB",(1920,1240),(10,12,14))
    for i,(name,field) in enumerate(variants.items()):
        im=Image.fromarray(r.draw(field,samples=8,diagnostic=2))
        im.save(out/f"{name}.png")
        xx=(i%2)*960;yy=(i//2)*620
        sheet.paste(im,(xx,yy))
        ImageDraw.Draw(sheet).text((xx+16,yy+603),name,fill=(220,210,180))
    sheet.save(out/"contact.png")
    power={}
    freq=np.fft.fftfreq(128)*128
    ky,kx=np.meshgrid(freq,freq,indexing="ij")
    high=np.hypot(kx,ky)>16
    for c,name in enumerate(("u","p","z","v")):
        f=np.fft.fft2(data[:,:,c]);p=np.abs(f)**2;p[0,0]=0
        power[name]={"high_frequency_power_fraction":float(p[high].sum()/p.sum()),
                     "minimum":float(data[:,:,c].min()),"maximum":float(data[:,:,c].max())}
    (out/"spatial-spectrum.json").write_text(json.dumps(power,indent=2)+"\n")
    print(json.dumps(power,indent=2),flush=True)
    r.close()


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="artwork/previews/field-ablation-002")
    main(parser.parse_args())
