"""Inspect an encoded film with bounded decoded-frame storage on RunPod."""
from __future__ import annotations
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont


STORY_TIMES=(0,12,26,50,64,92,104,112,120,128,142,170,188,200,208,218,228,239)
TRANSITION_TIMES=(0,2,5,8,12,19.9,100.5,103,104,106,109,112,
                  118,119.5,120,122.25,123,125,160,164,168,172,176,180,
                  204,206,208,210,216,222,228,234,239)


def sheet(frames,times,path,fps,columns=3):
    width,height=frames[round(times[0]*fps)].size
    cell_h=height+30
    rows=(len(times)+columns-1)//columns
    canvas=Image.new('RGB',(width*columns,cell_h*rows),(15,20,22))
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.load_default(size=15)
    for index,t in enumerate(times):
        key=round(t*fps)
        x=(index%columns)*width;y=(index//columns)*cell_h
        canvas.paste(frames[key],(x,y))
        draw.text((x+10,y+height+6),f'{key/fps:06.2f} s',(220,211,191),font=font)
    canvas.save(path,quality=90)


def main(args):
    source=Path(args.video);output=Path(args.output)
    output.mkdir(parents=True,exist_ok=False)
    record=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams',
                                              '-of','json',str(source)],text=True))
    video=next(item for item in record['streams'] if item['codec_type']=='video')
    fps=float(Fraction(video['avg_frame_rate']))
    width=480;height=round(width*int(video['height'])/int(video['width']))
    needed={round(t*fps) for t in STORY_TIMES+TRANSITION_TIMES}
    size=width*height*3
    command=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-threads','4',
             '-i',str(source),'-an','-vf',f'scale={width}:{height}',
             '-pix_fmt','rgb24','-f','rawvideo','pipe:1']
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    previous=None;frames={};rows=[];index=0
    try:
        while True:
            data=process.stdout.read(size)
            if not data:break
            if len(data)!=size:raise RuntimeError('Incomplete decoded frame')
            pixels=np.frombuffer(data,dtype=np.uint8).reshape(height,width,3)
            mono=pixels.astype(np.float32).mean(axis=2)
            rows.append({'frame':index,'seconds':index/fps,'mean_rgb':float(mono.mean()),
                         'p99_rgb':float(np.percentile(mono,99)),
                         'max_rgb':int(pixels.max()),
                         'dark_fraction':float(np.mean(mono<4)),
                         'mean_absolute_change':None if previous is None else
                             float(np.abs(pixels.astype(np.int16)-previous).mean())})
            if index in needed:frames[index]=Image.fromarray(pixels.copy())
            previous=pixels.astype(np.int16);index+=1
        detail=process.stderr.read().decode('utf8',errors='replace')
        if process.wait():raise RuntimeError(detail)
    finally:
        if process.poll() is None:process.kill();process.wait()
    assert needed.issubset(frames),'The film ends before the review timestamps'
    black=[item for item in rows if 119.6<=item['seconds']<=122.2]
    assert black and max(item['max_rgb'] for item in black)<=2
    unplanned=[item for item in rows if item['p99_rgb']<4
               and not 118<=item['seconds']<=123
               and not (args.titles and item['seconds']>=235)]
    assert not unplanned,'Unexpected near-black images outside the authored withdrawal'
    expected=round(240*fps)
    assert index==expected,(index,expected)
    sheet(frames,STORY_TIMES,output/'story.jpg',fps)
    sheet(frames,TRANSITION_TIMES,output/'transitions.jpg',fps)
    # Only the selected contact sheets and compact per-frame readings persist.
    (output/'frames.json').write_text(json.dumps(rows,separators=(',',':'))+'\n')
    shutil.copyfile(__file__,output/'river_film_review.py')
    review={'input':source.name,'fps':fps,'frames':index,'analysis_resolution':[width,height],
            'blackout':{'frame_count':len(black),'max_rgb':max(item['max_rgb'] for item in black)},
            'unexpected_near_black_frames':len(unplanned),'decoded_without_error':True,
            'authored_closing_title':args.titles,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope':'Encoded-frame brightness and continuity evidence; contact sheets require visual review. No motion-viewing, listening or emotional verdict is implied.',
            'files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in sorted(output.iterdir()) if p.is_file()}}
    (output/'review.json').write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps(review))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--titles',action='store_true')
    main(parser.parse_args())
