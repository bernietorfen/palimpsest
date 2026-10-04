"""Render the second-act composition directly into FFmpeg on RunPod."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
import time
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from studio.choir_render import ChoirRenderer
from studio.choir_scene import build_scene,load_scene
from studio import choir_cinematography as camera
from studio.preserve import sha256

SOURCES=('studio/choir_film.py','studio/choir_cinematography.py','studio/choir_render.py','studio/choir_scene.py',
         'studio/choir_geometry.py','studio/mesh_geometry.py','studio/mesh_render.py','studio/reconstruction.py',
         'studio/shaders/choir.frag','studio/shaders/choir_composite.frag','studio/shaders/sheet.vert',
         'studio/shaders/sheet_depth.vert','studio/shaders/sheet_depth.frag','studio/shaders/fullscreen.vert')


class Titles:
    def __init__(self,w,h):
        self.w,self.h=w,h;root=Path('/usr/share/fonts/truetype/dejavu')
        self.large=ImageFont.truetype(str(root/'DejaVuSerif.ttf'),max(16,round(h*.040)))
        self.small=ImageFont.truetype(str(root/'DejaVuSans.ttf'),max(9,round(h*.013)))
        self.cache={}
    def layer(self,title,subtitle):
        key=(title,subtitle)
        if key in self.cache:return self.cache[key]
        image=Image.new('RGBA',(self.w,self.h));draw=ImageDraw.Draw(image);color=(35,49,49,255)
        y=.874 if title in ('A choir of absences','The same question') else .090
        draw.text((self.w*.055,self.h*y),title,font=self.large,fill=color,anchor='lm')
        if subtitle:draw.text((self.w*.055,self.h*.933),subtitle,font=self.small,fill=color,anchor='lm')
        self.cache[key]=np.asarray(image,dtype=np.float32)/255
        return self.cache[key]
    def draw(self,frame,t,study=False):
        intervals=((1.5,12.,'A choir of absences','PALIMPSEST / An original work by Codex'),
                   (49.,55.,'A voice enters',''),(145.,150.,'What passes between',''),
                   (230.,236.,'The source leaves',''),(249.,257.,'The same question',''),
                   (276.,283.,'Another answer',''))
        layer=None;strength=0
        for start,end,title,subtitle in intervals:
            if start<=t<end:layer=self.layer(title,subtitle);strength=min(1,(t-start)/1.3,(end-t)/1.3)
        fade=ease((t-.15)/1.5)*ease((288-t)/3.5)
        maximum=65535 if frame.dtype==np.uint16 else 255
        if layer is not None or fade<1:
            value=frame.astype(np.float32)/maximum
            if layer is not None:
                alpha=layer[:,:,3:]*max(0,strength);value=value*(1-alpha)+layer[:,:,:3]*alpha
            paper=np.array([.932,.927,.908],dtype=np.float32)
            value=value*fade+paper*(1-fade);frame=np.clip(value*maximum+.5,0,maximum).astype(frame.dtype)
        if study:
            if frame.dtype!=np.uint8:raise ValueError('Study annotation needs eight bit frames')
            image=Image.fromarray(frame);ImageDraw.Draw(image).text((12,12),f'STUDY / {t:07.3f} s / {camera.shot_name(t)}',font=self.small,fill=(39,48,48));frame=np.asarray(image)
        return frame


def ease(x):return camera.ease(x)


def interpolate(values,position):
    left=min(int(position),len(values)-1);f=position-left
    a=values[left].astype(np.float32)
    return a if f<1e-8 else a*(1-f)+values[min(left+1,len(values)-1)].astype(np.float32)*f


def scene_at(scene,fields,readouts,t,field_fps,readout_hz,nu,nv):
    field=interpolate(fields,t*field_fps)
    values={key:interpolate(readouts[key],t*readout_hz) for key in ('bridge_u','bridge_v','endpoints','gates')}
    return build_scene(scene,field,values['bridge_u'],values['bridge_v'],values['endpoints'],values['gates'],nu=nu,nv=nv,pose_overrides=camera.pose_at(t))


def main(args):
    output=Path(args.output)
    if output.exists():raise FileExistsError(output)
    records=output.with_suffix('');records.mkdir(parents=True,exist_ok=False)
    hashes={}
    for relative in SOURCES:
        target=records/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(relative,target);hashes[relative]=sha256(Path(relative))
    source=Path(args.performance);protocol=json.loads((source/'protocol.json').read_text());scene=protocol['scene']
    fields=np.load(source/'fields.npy',mmap_mode='r')
    with np.load(source/'readouts.npz') as stored:
        readouts={key:stored[key] for key in ('bridge_u','bridge_v','endpoints','gates')}
    duration=args.end-args.start;frames=round(duration*args.fps)
    if duration<=0 or args.start<0 or args.end>288:raise ValueError('Invalid performance interval')
    renderer=ChoirRenderer(args.width,args.height,shadow_size=args.shadow);titles=Titles(args.width,args.height)
    partial=output.with_name(output.stem+'.partial'+output.suffix)
    if partial.exists():raise FileExistsError(partial)
    command=['ffmpeg','-hide_banner','-loglevel','warning','-nostdin','-filter_threads','2','-f','rawvideo','-pixel_format','rgb48le' if args.bits==10 else 'rgb24','-video_size',f'{args.width}x{args.height}','-framerate',str(args.fps),'-i','pipe:0']
    if args.audio:command+=['-ss',str(args.start),'-i',args.audio,'-map','0:v:0','-map','1:a:0','-c:a','aac','-b:a','320k','-t',str(duration)]
    command+=['-c:v','libx265' if args.bits==10 else 'libx264','-preset',args.preset,'-crf',str(args.crf),'-threads','6']
    if args.bits==10:command+=['-x265-params','pools=6:frame-threads=2:log-level=error','-tag:v','hvc1']
    command+=['-vf','scale=in_range=full:out_range=tv:out_color_matrix=bt709','-pix_fmt','yuv420p10le' if args.bits==10 else 'yuv420p','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart',str(partial)]
    began=time.monotonic();metrics=[];previous=None
    with (records/'encoder.log').open('w') as log:
        encoder=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log,stdout=subprocess.DEVNULL)
        try:
            for index in range(frames):
                t=args.start+index/args.fps
                objects=scene_at(scene,fields,readouts,t,protocol['field_fps'],protocol['readout_hz'],args.nu,args.nv)
                frame=renderer.draw_scene(objects,**camera.camera_at(t),samples=args.samples,bit_depth=16 if args.bits==10 else 8)
                frame=titles.draw(frame,t,args.study);encoder.stdin.write(frame.tobytes())
                small=frame[::max(1,args.height//60),::max(1,args.width//100)].astype(np.float32)/(257 if args.bits==10 else 1)
                metrics.append({'time':t,'mean':float(small.mean()),'std':float(small.std()),'change':None if previous is None else float(np.abs(small-previous).mean())});previous=small
                if index%(args.fps*12)==0 or index==frames-1:
                    preview=(frame//257).astype(np.uint8) if args.bits==10 else frame;im=Image.fromarray(preview);im.thumbnail((960,540),Image.Resampling.LANCZOS);im.save(records/f'frame-{t:07.3f}.jpg',quality=84)
                    print(json.dumps({'frame':index+1,'total':frames,'time':t,'elapsed':time.monotonic()-began,'shot':camera.shot_name(t),'triangles':renderer.last_stats['triangles']}),flush=True)
            encoder.stdin.close();code=encoder.wait()
            if code:raise RuntimeError(f'Encoder failed: {code}')
        finally:
            if encoder.poll() is None:encoder.stdin.close();encoder.wait()
            renderer.close()
    partial.rename(output)
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':hashes,'performance_manifest_sha256':sha256(source/'manifest.json'),
            'seconds':time.monotonic()-began,'output_sha256':sha256(output),'frames':frames,'fps':args.fps,'width':args.width,'height':args.height,'bits':args.bits,
            'samples':args.samples,'mesh':[args.nu,args.nv],'area_shadow':True,'cinematography':camera.manifest(),'encoder':command,'metrics':metrics}
    (records/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'finished':str(output),'seconds':report['seconds']}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--performance',default='artifacts/studies/choir-performance-001');p.add_argument('--output',required=True);p.add_argument('--audio');p.add_argument('--start',type=float,default=0);p.add_argument('--end',type=float,default=288);p.add_argument('--width',type=int,default=1280);p.add_argument('--height',type=int,default=720);p.add_argument('--fps',type=int,default=24);p.add_argument('--samples',type=int,default=16);p.add_argument('--nu',type=int,default=96);p.add_argument('--nv',type=int,default=144);p.add_argument('--shadow',type=int,default=2048);p.add_argument('--bits',type=int,choices=(8,10),default=8);p.add_argument('--crf',type=int,default=19);p.add_argument('--preset',default='medium');p.add_argument('--study',action='store_true');main(p.parse_args())
