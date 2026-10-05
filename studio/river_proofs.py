"""Render sparse reviewable frames from the exact film implementation on GPU."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from studio.river_blender import build_scene, set_camera
from studio.river_sequence import frame_state, source_snapshot
from studio.river_geometry import validate_embedding
from studio.river_cinematography import SHOTS, manifest
from studio.river_camera_pickups import pickup_manifest


def main(args):
    folder=Path(args.output)
    if folder.exists(): raise FileExistsError(folder)
    folder.mkdir(parents=True)
    hashes=source_snapshot(folder)
    own=Path(__file__).read_bytes()
    (folder/'source/river_proofs.py').write_bytes(own)
    hashes['river_proofs.py']=hashlib.sha256(own).hexdigest()
    camera_score=manifest()
    if args.camera_revision: camera_score['revision']=pickup_manifest()
    (folder/'camera-score.json').write_text(json.dumps(camera_score,indent=2)+'\n')
    args.shape,args.shot,args.group,args.choreography,args.time='weave','wide',None,False,0.
    args.ten_bit=False
    scene,camera,dynamic,fibres=build_scene(args)
    scene.cycles.seed=4217
    scene.cycles.use_animated_seed=False
    scene.render.image_settings.compression=15
    lights=[(obj,obj.data.energy) for obj in bpy.data.objects if obj.type=='LIGHT']
    if args.times:
        cases=[('shot',float(value)) for value in args.times.split(',')]
    elif args.matched:
        cases=[('local',t) for t in (0.,104.,208.)]+[('wide',t) for t in (0.,104.,208.)]+[('local',120.)]
    else:
        cases=[('shot',(shot.start+shot.end)/2) for shot in SHOTS]+[('shot',0.),('shot',104.),('shot',208.)]
    records=[]
    for number,(kind,seconds) in enumerate(cases):
        began=time.monotonic()
        shot,light,focus=frame_state(scene,camera,dynamic,fibres,args,seconds,lights)
        if kind=='wide':
            set_camera(camera,'wide','weave')
            for _,_,obj,edge in dynamic:
                obj.hide_render=edge.hide_render=False
                for item in (obj,edge):
                    item.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value=1.
            for _,_,_,obj in fibres:
                obj.hide_render=False
                obj.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value=1.
            # Shared canonical light for the controlled whole-view comparison.
            for obj,energy in lights:
                obj.data.energy=energy
                if obj.name=='Blue rim': obj.data.color=(.43,.74,1.)
            effective_focus=0.
        else:
            effective_focus=focus
        name=f'{number:02d}-{kind}-{seconds:07.3f}.png'
        scene.render.filepath=str((folder/name).resolve())
        bpy.ops.render.render(write_still=True)
        records.append({'image':name,'film_time':seconds,'view':kind,'shot':shot,
                        'wall_seconds':time.monotonic()-began,'light':light,
                        'scripted_reference_focus':focus,'effective_reference_focus':effective_focus,
                        'camera_location':list(camera.location),'camera_lens':camera.data.lens,
                        'camera_rotation':list(camera.rotation_euler)})
        print(json.dumps(records[-1]),flush=True)
    (folder/'proof.json').write_text(json.dumps({'frames':records,'source_sha256':hashes,
        'geometry_checks':validate_embedding(),'resolution':[args.width,args.height],
        'scope':'Fresh rendered images; visual quality and pixel comparisons are assessed separately.'},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',required=True)
    p.add_argument('--matched',action='store_true')
    p.add_argument('--times',help='Comma-separated film times for a bounded review')
    p.add_argument('--camera-revision',action='store_true')
    p.add_argument('--width',type=int,default=1280)
    p.add_argument('--height',type=int,default=720)
    p.add_argument('--samples',type=int,default=48)
    p.add_argument('--along',type=int,default=193)
    p.add_argument('--across',type=int,default=33)
    main(p.parse_args(sys.argv[sys.argv.index('--')+1:]))
