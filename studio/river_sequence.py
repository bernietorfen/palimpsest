"""Render a bounded, streamed cinematic sequence on the production GPU.

Only one temporary frame is stored. Checkpoint images are sparse, and all
compiled source/score inputs are frozen before rendering begins.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import bpy
from mathutils import Vector
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from studio.river_blender import build_scene, aim
from studio.river_geometry import membrane, phases, woven_relations, woven_internal_relations, validate_embedding
from studio.river_cinematography import camera_at, model_time, observation_light, reference_focus, manifest, smooth
from studio.river_camera_pickups import pickup_camera_at, pickup_manifest
from studio.river_typography import filter_chain as typography_filters, manifest as typography_manifest, SERIF, SANS


DETAIL_SHOTS={'The crossing','Inside the current','An ascending line','The space between',
              'A returning edge','A remaining strand','The answer elsewhere','Along what remains',
              'An answer held between','The thread takes the phrase','A relation opens outward'}


def update_curve(obj, paths):
    for spline, path in zip(obj.data.splines, paths):
        xyzw=np.column_stack((path,np.ones(len(path)))).astype(np.float32)
        spline.points.foreach_set('co',xyzw.ravel())
    obj.data.update_tag()


def frame_state(scene,camera,dynamic,fibres,args,seconds,light_energy):
    state=phases(model_time(seconds))
    focus=reference_focus(seconds)
    alpha=1-focus
    for g,r,obj,edge in dynamic:
        grid,_,_=membrane(state,g,r,along=args.along,across=args.across,shape='weave')
        obj.data.vertices.foreach_set('co',grid.astype(np.float32).ravel())
        obj.data.update()
        update_curve(edge,[grid[:,0],grid[:,-1]])
        hidden=(g != 0 and alpha < 1e-8)
        obj.hide_render=edge.hide_render=hidden
        for item in (obj,edge):
            item.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value=(1. if g==0 else alpha)
    for kind,first,second,obj in fibres:
        paths=(woven_internal_relations(state,first,second) if kind=='within'
               else woven_relations(state,first,second))
        update_curve(obj,paths)
        obj.hide_render=kind=='between' and alpha < 1e-8
        # Reference stitches keep a separate shared material from outer fibres.
        obj.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value=(1. if kind=='within' else alpha)
    camera_state=(pickup_camera_at(seconds) if getattr(args,'camera_revision',False)
                  else camera_at(seconds))
    scene.cycles.samples=args.samples
    if getattr(args,'detail_sampling',False):
        if focus>=1.-1e-8:
            scene.cycles.samples=2*args.samples
        elif camera_state['shot'] in DETAIL_SHOTS:
            scene.cycles.samples=(4*args.samples+2)//3
    camera.location=camera_state['location']
    aim(camera,camera_state['target'])
    camera.data.lens=camera_state['lens']
    camera.data.dof.aperture_fstop=camera_state['aperture']
    camera.data.dof.focus_distance=(Vector(camera_state['target'])-camera.location).length
    amount=observation_light(seconds)
    for obj,energy in light_energy:
        obj.data.energy=energy*amount
        if obj.name=='Blue rim':
            warmth=smooth((seconds-156)/40)*(1-focus)
            obj.data.color=tuple((1-warmth)*a+warmth*b for a,b in zip((.43,.74,1.),(.97,.68,.40)))
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.13*amount
    for _,_,_,obj in fibres:
        obj.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=.045*amount
    scene.render.image_settings.color_depth='16' if args.ten_bit else '8'
    bpy.context.view_layer.update()
    return camera_state['shot'],float(amount),float(focus)


def source_snapshot(folder):
    target=folder/'source'
    target.mkdir()
    hashes={}
    for name in ('river_geometry.py','river_blender.py','river_cinematography.py','river_camera_pickups.py','river_sequence.py','river_typography.py'):
        data=Path(__file__).with_name(name).read_bytes()
        (target/name).write_bytes(data)
        hashes[name]=hashlib.sha256(data).hexdigest()
    return hashes


def main(args):
    folder=Path(args.output)
    if folder.exists():
        raise FileExistsError(folder)
    folder.mkdir(parents=True)
    source_hashes=source_snapshot(folder)
    titles=typography_manifest() if args.titles else None
    if titles:
        font_folder=folder/'source/fonts'
        font_folder.mkdir()
        for path in (SERIF,SANS):
            shutil.copyfile(path,font_folder/Path(path).name)
        for package in ('fonts-liberation','fonts-dejavu-core'):
            shutil.copyfile(f'/usr/share/doc/{package}/copyright',font_folder/f'{package}-copyright.txt')
        (folder/'typography.json').write_text(json.dumps(titles,indent=2)+'\n')
    camera_score=manifest()
    if getattr(args,'camera_revision',False): camera_score['revision']=pickup_manifest()
    (folder/'camera-score.json').write_text(json.dumps(camera_score,indent=2)+'\n')
    (folder/'embedding-check.json').write_text(json.dumps(validate_embedding(),indent=2)+'\n')
    args.time=model_time(args.start)
    args.shape='weave'
    args.shot='wide'
    args.group=None
    args.choreography=False
    scene,camera,dynamic,fibres=build_scene(args)
    if args.full_frame:
        scene.cycles.use_auto_tile=False
    scene.cycles.seed=4217
    scene.cycles.use_animated_seed=False
    scene.render.image_settings.compression=12
    light_energy=[(obj,obj.data.energy) for obj in bpy.data.objects if obj.type=='LIGHT']
    scene.render.fps=args.fps
    suffix='tiff' if args.frame_format=='tiff' else 'png'
    if suffix=='tiff':
        scene.render.image_settings.file_format='TIFF'
        scene.render.image_settings.tiff_codec='NONE'
    temporary=folder/f'.current-frame.{suffix}'
    scene.render.filepath=str(temporary.resolve())
    filename='river-silent-10bit.mp4' if args.ten_bit else 'river-silent.mp4'
    output=folder/filename
    encoding=['-c:v','libx265','-pix_fmt','yuv420p10le','-crf',str(args.crf),
              '-preset',args.encode_preset,'-x265-params',f'pools={args.encode_threads}:frame-threads=2:log-level=error'] if args.ten_bit else [
              '-c:v','libx264','-pix_fmt','yuv420p','-crf',str(args.crf),'-preset',args.encode_preset,'-threads',str(args.encode_threads)]
    if args.hardware_encode:
        encoding=['-c:v','hevc_nvenc' if args.ten_bit else 'h264_nvenc',
                  '-pix_fmt','p010le' if args.ten_bit else 'yuv420p',
                  '-preset','p7','-tune','hq','-rc','vbr','-cq',str(args.crf),
                  '-b:v','0','-multipass','fullres','-spatial_aq','1',
                  '-temporal_aq','1','-aq-strength','8','-rc-lookahead','20','-bf','3']
    encoding+=['-g',str(args.fps*2)]
    if args.segmented:
        encoding+=['-force_key_frames','expr:gte(t,n_forced*12)','-flags','+cgop']
        if args.ten_bit and not args.hardware_encode:
            value=encoding.index('-x265-params')+1
            encoding[value]+=':open-gop=0'
        if args.hardware_encode:
            encoding+=['-forced-idr','1']
    # RGB image values use full range; explicitly select the video matrix.
    # The display-referred AgX image is preserved, with BT.709 primaries.
    mux=['-movflags','+faststart',str(output)]
    if args.segmented:
        (folder/'chunks').mkdir()
        mux=['-f','segment','-segment_time','12','-reset_timestamps','1',
             '-segment_format','mp4','-segment_format_options','movflags=+faststart',
             str(folder/'chunks/part-%03d.mp4')]
    filters=['scale=in_range=full:out_range=tv:out_color_matrix=bt709']
    if titles:
        filters.extend(typography_filters(args.width,args.height,args.start))
    command=['ffmpeg','-hide_banner','-loglevel','error','-threads','6',
             '-f','image2pipe','-vcodec','tiff' if suffix=='tiff' else 'png',
             '-framerate',str(args.fps),'-i','pipe:0','-an',*encoding,
             '-vf',','.join(filters),
             '-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709',*mux]
    count=round(args.duration*args.fps)
    progress=folder/'frames.jsonl'
    began=time.monotonic()
    encoder=None
    frame_bytes=None
    checkpoints=folder/'checkpoints'
    checkpoints.mkdir()
    try:
        with progress.open('w') as log:
            for index in range(count):
                wall=time.monotonic()
                seconds=args.start+index/args.fps
                shot,light,focus=frame_state(scene,camera,dynamic,fibres,args,seconds,light_energy)
                prepared=time.monotonic()
                bpy.ops.render.render(write_still=True)
                rendered=time.monotonic()
                data=temporary.read_bytes()
                read=time.monotonic()
                if encoder is None:
                    if suffix=='tiff':
                        # Uncompressed TIFF needs an explicit packet boundary:
                        # unlike PNG, this pipe demuxer cannot discover it.
                        frame_bytes=len(data)
                        position=command.index('-i')
                        command[position:position]=['-frame_size',str(frame_bytes)]
                    encoder=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
                if frame_bytes is not None and len(data)!=frame_bytes:
                    raise RuntimeError('Uncompressed TIFF packet size changed')
                encoder.stdin.write(data)
                written=time.monotonic()
                if index==0 or index==count-1 or index % round(12*args.fps)==0:
                    shutil.copyfile(temporary,checkpoints/f'{seconds:08.3f}.{suffix}')
                item={'frame':index,'film_time':seconds,'model_time':model_time(seconds),
                      'shot':shot,'seconds':time.monotonic()-wall,'light':light,'reference_focus':focus,
                      'sample_limit':scene.cycles.samples,
                      'camera_location':list(camera.location),'camera_lens':camera.data.lens,
                      'camera_rotation':list(camera.rotation_euler),
                      'stages':{'prepare':prepared-wall,'render_and_save':rendered-prepared,
                                'read':read-rendered,'encoder_write':written-read}}
                log.write(json.dumps(item)+'\n')
                if index % max(1,round(args.fps))==0:
                    log.flush()
                    print(json.dumps({'progress':index,'frames':count,'elapsed':time.monotonic()-began,
                                      'film_time':seconds,'shot':shot}),flush=True)
        encoder.stdin.close()
        error=encoder.stderr.read().decode('utf-8',errors='replace')
        if encoder.wait()!=0:
            raise RuntimeError('Video encoding failed: '+error[-1000:])
    except BrokenPipeError as error:
        encoder.wait()
        detail=encoder.stderr.read().decode('utf-8',errors='replace')
        raise RuntimeError('Video encoder stopped: '+detail[-2000:]) from error
    except BaseException:
        if encoder is not None:
            encoder.kill()
            encoder.wait()
        raise
    finally:
        if temporary.exists(): temporary.unlink()
    chunks=[]
    if args.segmented:
        pieces=sorted((folder/'chunks').glob('part-*.mp4'))
        concat=folder/'chunks.concat.txt'
        concat.write_text(''.join(f"file 'chunks/{path.name}'\n" for path in pieces))
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','concat',
                        '-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',
                        str(output)],check=True)
        for path in pieces:
            digest=hashlib.sha256()
            with path.open('rb') as source:
                while block:=source.read(1024*1024): digest.update(block)
            chunks.append({'file':str(path.relative_to(folder)),'bytes':path.stat().st_size,
                           'sha256':digest.hexdigest()})
    encoded=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams',
                                                '-show_format','-of','json',str(output)],text=True))
    video_stream=next(item for item in encoded['streams'] if item['codec_type']=='video')
    assert int(video_stream['nb_frames'])==count
    assert abs(float(video_stream['duration'])-count/args.fps)<1e-4
    assert abs(float(video_stream.get('start_time',0.)))<1e-6
    assert abs(float(encoded['format']['duration'])-count/args.fps)<.002
    report={'title':'A River Twice','start':args.start,'duration':args.duration,'fps':args.fps,
            'frames':count,'resolution':[args.width,args.height],'samples':args.samples,
            'sampling_policy':{'base':args.samples,'intimate_views':(4*args.samples+2)//3,
                               'isolated_reference':2*args.samples,'detail_shots':sorted(DETAIL_SHOTS)}
                               if args.detail_sampling else {'uniform_limit':args.samples},
            'render_seconds':time.monotonic()-began,'renderer':bpy.app.version_string,
            'frame_format':args.frame_format,'hardware_encode':args.hardware_encode,
            'encode_preset':args.encode_preset,'encode_threads':args.encode_threads,
            'full_frame':args.full_frame,'encoder_command':command,
            'typography':titles,
            'camera_revision':pickup_manifest() if getattr(args,'camera_revision',False) else None,
            'encoded_timeline':{key:video_stream.get(key) for key in
                                ('codec_name','pix_fmt','nb_frames','avg_frame_rate','start_time','duration')},
            'chunks':chunks,'chunk_policy':'Complete twelve-second chunks remain playable if a later render is interrupted.' if args.segmented else None,
            'source_sha256':source_hashes,'video':filename,'bytes':output.stat().st_size,
            'single_temporary_frame_removed':not temporary.exists(),
            'checkpoint_policy':'first,last,and one every12 seconds',
            'scope':'Original computed phase geometry, authored camera/light/observation cuts. Sound is composed separately; any encoded typography is explicitly recorded.'}
    (folder/'render.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',required=True)
    p.add_argument('--start',type=float,default=0.)
    p.add_argument('--duration',type=float,default=20.)
    p.add_argument('--fps',type=int,default=24)
    p.add_argument('--width',type=int,default=1280)
    p.add_argument('--height',type=int,default=720)
    p.add_argument('--samples',type=int,default=24)
    p.add_argument('--along',type=int,default=193)
    p.add_argument('--across',type=int,default=33)
    p.add_argument('--crf',type=float,default=18)
    p.add_argument('--ten-bit',action='store_true')
    p.add_argument('--frame-format',choices=('png','tiff'),default='png')
    p.add_argument('--hardware-encode',action='store_true')
    p.add_argument('--encode-preset',choices=('slow','medium','fast','veryfast'),default='medium')
    p.add_argument('--encode-threads',type=int,default=6)
    p.add_argument('--full-frame',action='store_true')
    p.add_argument('--segmented',action='store_true')
    p.add_argument('--titles',action='store_true')
    p.add_argument('--detail-sampling',action='store_true')
    p.add_argument('--camera-revision',action='store_true')
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    a=p.parse_args(argv)
    if a.start<0 or a.duration<=0 or a.start+a.duration>240+1e-8:
        p.error('Select a positive interval inside the240-second score')
    main(a)
