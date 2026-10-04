"""Prepare a bounded, self-contained exhibition asset set on RunPod."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess

import numpy as np
from PIL import Image
from fontTools.ttLib import TTFont
from pypdf import PdfReader

from studio.mesh_render import SheetRenderer
from studio.preserve import sha256
from studio.simulate import source_hashes


def encode(source, output, *, start=None, duration=None, width=1920, crf=24):
    command=["ffmpeg","-hide_banner","-loglevel","warning","-nostdin","-n",
             "-threads","2","-filter_threads","2"]
    if start is not None:
        command += ["-ss",str(start)]
    command += ["-i",str(source)]
    if duration is not None:
        command += ["-t",str(duration)]
    command += ["-map","0:v:0","-map","0:a:0","-vf",f"scale={width}:-2:flags=lanczos",
                "-c:v","libx264","-preset","slow","-crf",str(crf),"-threads","6",
                "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k",
                "-color_primaries","bt709","-color_trc","bt709","-colorspace","bt709",
                "-movflags","+faststart",str(output)]
    subprocess.run(command,check=True)


def poster(source, destination, time):
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-n",
                    "-threads","2","-filter_threads","2","-ss",str(time),"-i",str(source),
                    "-frames:v","1","-vf","scale=1920:-2:flags=lanczos","-q:v","2",str(destination)],check=True)


def main(args):
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    hashes=source_hashes(out/"source")
    film=Path(args.film)
    fields=np.load("artifacts/studies/performance-002/fields.npy",mmap_mode="r")
    renderer=SheetRenderer(1200,1500,shadow_size=4096,nu=256,nv=512)
    render_records=[]
    for t in (0,165,358):
        settings=dict(camera=(5.6,3.25,5.9),turn=.55,samples=128,area_shadow=True,
                      light_angle=.25,exposure=1.1,lens_radius=.003)
        frame=renderer.draw(fields[t*24].astype(np.float32),**settings)
        Image.fromarray(frame).save(out/f"state-{t:03d}.jpg",quality=91)
        shutil.copy2(f"artwork/sculptures/state-{t:03d}/palimpsest.glb",out/f"state-{t:03d}.glb")
        render_records.append({"time":t,"settings":settings,"render":renderer.last_stats})
    renderer.close()
    for file,t in (("film-poster",165),("first-poster",30),("return-poster",382)):
        poster(film,out/f"{file}.jpg",t)
    for name,file in (("serif","DejaVuSerif.ttf"),("sans","DejaVuSans.ttf")):
        font=TTFont(f"/usr/share/fonts/truetype/dejavu/{file}")
        font.flavor="woff2"
        font.save(out/f"{name}.woff2")
    shutil.copy2("/usr/share/doc/fonts-dejavu-core/copyright",out/"font-license.txt")
    shutil.copy2(args.notebook,out/"palimpsest-notebook.pdf")
    subprocess.run(["pdftoppm","-f","5","-l","5","-singlefile","-scale-to","1200",
                    "-jpeg","-jpegopt","quality=90",args.notebook,str(out/"notebook-spread")],check=True)
    for name,start in (("phrase-first",18),("phrase-return",370)):
        encode(film,out/f"{name}.mp4",start=start,duration=46,width=960,crf=23)
    if args.viewing_copy:
        shutil.copy2(args.viewing_copy,out/"palimpsest-viewing.mp4")
    else:
        encode(film,out/"palimpsest-viewing.mp4",crf=args.crf)
    poster_image=Image.open(args.atlas_poster)
    poster_image.thumbnail((1000,1400),Image.Resampling.LANCZOS)
    poster_image.convert("RGB").save(out/"120-possible-pasts.jpg",quality=88)
    notebook_pages=len(PdfReader(args.notebook).pages)
    downloads=[{"title":"Viewing film","detail":"1080p / MP4","url":"/assets/generated/palimpsest-viewing.mp4"},
               {"title":"Artist’s notebook","detail":f"{notebook_pages} pages / PDF","url":"/assets/generated/palimpsest-notebook.pdf"},
               {"title":"Inscription sculpture","detail":"glTF","url":"/assets/generated/state-165.glb"}]
    (out/"edition.json").write_text(json.dumps({"downloads":downloads},indent=2)+"\n")
    inventory=[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha256(p)} for p in sorted(out.iterdir()) if p.is_file()]
    report={"source_sha256":hashes,"film_sha256":sha256(film),"notebook_sha256":sha256(Path(args.notebook)),
            "prepared_viewing_copy":args.viewing_copy,"viewing_crf":args.crf,
            "sculpture_renders":render_records,"files":inventory,"total_asset_bytes":sum(p["bytes"] for p in inventory)}
    (out/"manifest.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"output":str(out),"asset_bytes":report["total_asset_bytes"],"files":len(inventory)}),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--film",default="artwork/masters/palimpsest-film-4k-001.mp4")
    parser.add_argument("--notebook",default="artwork/masters/palimpsest-notebook.pdf")
    parser.add_argument("--output",default="artwork/exhibition-001")
    parser.add_argument("--crf",type=int,default=24)
    parser.add_argument("--viewing-copy")
    parser.add_argument("--atlas-poster",default="artwork/analysis/history-atlas-002/120-possible-pasts.png")
    main(parser.parse_args())
