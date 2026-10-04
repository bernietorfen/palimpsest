"""Render the authored film on RunPod, piping frames to a remote encoder."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from studio import cinematography
from studio.render import SculptureRenderer
from studio.mesh_render import SheetRenderer
from studio.simulate import source_hashes


class Lettering:
    def __init__(self,width:int,height:int):
        self.width,self.height=width,height
        fonts=Path("/usr/share/fonts/truetype/dejavu")
        self.title=ImageFont.truetype(str(fonts/"DejaVuSerif.ttf"),round(height*.043))
        self.small=ImageFont.truetype(str(fonts/"DejaVuSans.ttf"),max(11,round(height*.0135)))
        self.chapter=ImageFont.truetype(str(fonts/"DejaVuSerif.ttf"),max(14,round(height*.021)))
        self.cache={}

    def layer(self,key:str):
        if key in self.cache:
            return self.cache[key]
        layer=Image.new("RGBA",(self.width,self.height))
        d=ImageDraw.Draw(layer)
        color=(222,211,187,255)
        if key=="title":
            d.text((self.width*.064,self.height*.875),"PALIMPSEST",font=self.title,fill=color,anchor="lm",stroke_width=0)
            d.text((self.width*.064,self.height*.928),"An instrument that becomes its own score",font=self.small,fill=color,anchor="lm")
        elif key=="end":
            d.text((self.width*.064,self.height*.875),"An original computational work by Codex",font=self.small,fill=color,anchor="lm")
            d.text((self.width*.064,self.height*.925),"3-4 October 2026",font=self.small,fill=color,anchor="lm")
        else:
            d.text((self.width*.064,self.height*.91),key,font=self.chapter,fill=color,anchor="lm",
                   stroke_width=max(1,round(self.height*.0008)),stroke_fill=(5,8,10,160))
        a=np.asarray(layer,dtype=np.float32)/255
        self.cache[key]=a
        return a

    def draw(self,frame:np.ndarray,t:float,annotate:bool=False):
        maximum=65535 if frame.dtype==np.uint16 else 255
        dtype=frame.dtype
        overlay=None
        strength=0.
        if 2<=t<14:
            overlay=self.layer("title")
            strength=min(1.,(t-2)/2,(14-t)/2)
        titles=((72,"II. What is kept"),(144,"III. A reply"),(216,"IV. Too much to hold"),
                (288,"V. What is lost"),(360,"VI. The same question"))
        for start,label in titles:
            if start<=t<start+6:
                overlay=self.layer(label)
                strength=min(1.,t-start,(start+6-t))
        if 425<=t<431:
            overlay=self.layer("end")
            strength=min(1.,t-425,431-t)
        fade=cinematography.fade_at(t)
        if overlay is not None or fade<1:
            value=frame.astype(np.float32)/maximum
            if overlay is not None:
                alpha=overlay[:,:,3:]*max(0.,strength)
                value=value*(1-alpha)+overlay[:,:,:3]*alpha
            frame=np.clip(value*fade*maximum+.5,0,maximum).astype(dtype)
        if annotate:
            im=Image.fromarray(frame)
            ImageDraw.Draw(im).text((16,16),f"STUDY  /  {t:07.3f} s  /  {cinematography.shot_name(t)}",
                                   font=self.small,fill=(230,215,187))
            frame=np.asarray(im)
        return frame


def run(args):
    if args.end<=args.start or args.start<0 or args.end>432:
        raise ValueError("clip must lie inside the 432-second score")
    if args.bit_depth==10 and (args.codec!="h265" or args.renderer!="sheet" or args.annotate):
        raise ValueError("10-bit output requires the sheet renderer, H.265 and no study annotation")
    duration=args.end-args.start
    frame_count=round(duration*args.fps)
    output=Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    records_dir=output.with_suffix("")
    records_dir.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(records_dir/"source")
    fields=np.load(args.fields,mmap_mode="r")
    source_manifest=json.loads((Path(args.fields).parent/"manifest.json").read_text())
    field_fps=source_manifest["fps"]
    partial=output.with_name(output.stem+".partial"+output.suffix)
    command=["ffmpeg","-hide_banner","-loglevel","warning","-y","-filter_threads","2","-f","rawvideo",
             "-pixel_format","rgb48le" if args.bit_depth==10 else "rgb24","-video_size",f"{args.width}x{args.height}",
             "-framerate",str(args.fps),"-i","pipe:0"]
    if args.audio:
        command += ["-ss",str(args.start),"-i",str(args.audio),"-map","0:v:0","-map","1:a:0",
                    "-c:a","aac","-b:a","320k","-t",str(duration)]
    command += ["-c:v","libx265" if args.codec=="h265" else "libx264",
                "-preset",args.preset,"-crf",str(args.crf),"-threads","8"]
    if args.codec=="h265":
        command += ["-x265-params","pools=8:frame-threads=2:log-level=error","-tag:v","hvc1"]
    command += ["-vf","scale=in_range=full:out_range=tv:out_color_matrix=bt709",
                "-pix_fmt","yuv420p10le" if args.bit_depth==10 else "yuv420p",
                "-color_primaries","bt709","-color_trc","bt709",
                "-colorspace","bt709","-movflags","+faststart",str(partial)]
    renderer=(SheetRenderer(args.width,args.height,shadow_size=args.shadow_size,nu=args.mesh_u,nv=args.mesh_v)
              if args.renderer=="sheet" else SculptureRenderer(args.width,args.height))
    lettering=Lettering(args.width,args.height)
    metrics=[]
    began=time.monotonic()
    previous=None
    log=(records_dir/"encoder.log").open("w")
    encoder=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log,stdout=subprocess.DEVNULL)
    try:
        for index in range(frame_count):
            t=args.start+index/args.fps
            coordinate=t*field_fps
            left=int(coordinate)
            alpha=coordinate-left
            field=fields[left].astype(np.float32)
            if alpha>1e-8:
                field=field*(1-alpha)+fields[min(left+1,len(fields)-1)].astype(np.float32)*alpha
            settings=cinematography.camera_at(t)
            if args.renderer=="sheet":
                for key in ("design","style","aperture"):
                    settings.pop(key,None)
                settings.update(area_shadow=args.area_shadow,bit_depth=16 if args.bit_depth==10 else 8)
            frame=renderer.draw(field,**settings,samples=args.samples)
            frame=lettering.draw(frame,t,args.annotate)
            encoder.stdin.write(frame.tobytes())
            small=frame[::max(1,args.height//72),::max(1,args.width//128)].astype(np.float32)
            if args.bit_depth==10:
                small/=257
            change=float(np.mean(np.abs(small-previous))) if previous is not None else None
            metrics.append({"time":t,"mean":float(small.mean()),"std":float(small.std()),"frame_change":change})
            previous=small
            if index%(args.fps*12)==0 or index==frame_count-1:
                preview=(frame//257).astype(np.uint8) if args.bit_depth==10 else frame
                preview=Image.fromarray(preview)
                preview.thumbnail((1280,720),Image.Resampling.LANCZOS)
                preview.save(records_dir/f"frame-{t:07.3f}.jpg",quality=92)
            if index%(args.fps*6)==0 or index==frame_count-1:
                elapsed=time.monotonic()-began
                print(json.dumps({"frame":index+1,"of":frame_count,"time":t,"elapsed":round(elapsed,2),
                                  "fps":round((index+1)/elapsed,2),"shot":cinematography.shot_name(t)}),flush=True)
        encoder.stdin.close()
        code=encoder.wait()
        if code:
            raise RuntimeError(f"ffmpeg failed with {code}; see {records_dir/'encoder.log'}")
    finally:
        if encoder.poll() is None:
            if not encoder.stdin.closed:
                encoder.stdin.close()
            encoder.wait()
        renderer.close()
        log.close()
    partial.rename(output)
    report={"created_utc":datetime.now(timezone.utc).isoformat(),"source_sha256":hashes,
            "fields":str(args.fields),"material_manifest_sha256":hashlib.sha256((Path(args.fields).parent/"manifest.json").read_bytes()).hexdigest(),
            "width":args.width,"height":args.height,"fps":args.fps,"frames":frame_count,
            "start":args.start,"end":args.end,"samples":args.samples,"seconds_to_render":time.monotonic()-began,
            "renderer":args.renderer,"bit_depth":args.bit_depth,"area_shadow":args.area_shadow,
            "mesh_chart":[args.mesh_u,args.mesh_v],"shadow_size":args.shadow_size,
            "metric_scale":"0-255 display code values, including for 10-bit encoded output",
            "encoder_command":command,"cinematography":cinematography.manifest(),"frame_metrics":metrics}
    (records_dir/"manifest.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"complete":True,"output":str(output),"seconds":time.monotonic()-began}),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--fields",default="artifacts/studies/performance-002/fields.npy")
    parser.add_argument("--audio")
    parser.add_argument("--output",required=True)
    parser.add_argument("--start",type=float,default=0.)
    parser.add_argument("--end",type=float,default=432.)
    parser.add_argument("--fps",type=int,default=24)
    parser.add_argument("--width",type=int,default=1280)
    parser.add_argument("--height",type=int,default=720)
    parser.add_argument("--samples",type=int,default=16)
    parser.add_argument("--crf",type=int,default=19)
    parser.add_argument("--preset",default="medium")
    parser.add_argument("--renderer",choices=("sheet","ray"),default="sheet")
    parser.add_argument("--codec",choices=("h264","h265"),default="h264")
    parser.add_argument("--bit-depth",type=int,choices=(8,10),default=8)
    parser.add_argument("--mesh-u",type=int,default=192)
    parser.add_argument("--mesh-v",type=int,default=384)
    parser.add_argument("--shadow-size",type=int,default=2048)
    parser.add_argument("--area-shadow",action="store_true")
    parser.add_argument("--annotate",action="store_true")
    run(parser.parse_args())
