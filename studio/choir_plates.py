"""Three matched installation plates and the absent source's portrait.

Original recorded geometry and authored lighting. RunPod only; no frame dumps.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from studio.choir_film import scene_at
from studio.choir_geometry import ListenerShape,build_listener
from studio.choir_render import ChoirRenderer,SceneObject,floor_object,transform
from studio.reconstruction import periodic_field
from studio.preserve import sha256


def main(args):
    root=Path(args.output);root.mkdir(parents=True,exist_ok=False)
    sources=('studio/choir_plates.py','studio/choir_film.py','studio/choir_geometry.py','studio/choir_scene.py','studio/choir_render.py','studio/choir_cinematography.py','studio/shaders/choir.frag','studio/shaders/choir_composite.frag')
    hashes={}
    for relative in sources:
        target=root/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(relative,target);hashes[relative]=sha256(Path(relative))
    performance=Path(args.performance);protocol=json.loads((performance/'protocol.json').read_text());scene=protocol['scene'];fields=np.load(performance/'fields.npy',mmap_mode='r')
    with np.load(performance/'readouts.npz') as data:readouts={k:data[k] for k in ('bridge_u','bridge_v','endpoints','gates')}
    renderer=ChoirRenderer(7680,4320,shadow_size=4096)
    fonts=Path('/usr/share/fonts/truetype/dejavu');title_font=ImageFont.truetype(str(fonts/'DejaVuSerif.ttf'),116);small_font=ImageFont.truetype(str(fonts/'DejaVuSans.ttf'),38)
    plates=[];contact=Image.new('RGB',(1200,3*280),'#ede8df');contact_draw=ImageDraw.Draw(contact);label_font=ImageFont.truetype(str(fonts/'DejaVuSans.ttf'),14)
    for i,(name,title,t) in enumerate((('01-before','Before an encounter',42.),('02-encounter','What passes between',216.),('03-after','A choir of absences',288.))):
        objects=scene_at(scene,fields,readouts,t,24,96,192,288)
        if t==288:objects.pop(1)
        frame=renderer.draw_scene(objects,camera=(9.8,6.8,12.8),target=(0,.15,0),focal_length=2.35,samples=64,shadow_extent=8.5,shadow_softness=.85,bit_depth=8)
        plate=Image.new('RGB',(8000,5200),'#edeae3');plate.paste(Image.fromarray(frame),(160,150));draw=ImageDraw.Draw(plate)
        draw.text((210,4750),title,font=title_font,fill='#2c3b3a');draw.text((214,4948),'PALIMPSEST / A choir of absences / Codex, 2026',font=small_font,fill='#59645c');draw.text((7785,4950),f'{int(t):03d} seconds / {"Source absent" if t==288 else "Seven bodies"}',font=small_font,fill='#59645c',anchor='ra')
        png=root/(name+'.png');plate.save(png,optimize=False);jpg=root/(name+'-view.jpg');view=plate.copy();view.thumbnail((1600,1040));view.save(jpg,quality=91)
        pdf=root/(name+'.pdf');c=canvas.Canvas(str(pdf),pagesize=(1152,748.8),pageCompression=1);c.setTitle(title+' / A choir of absences');c.setAuthor('Codex');c.drawImage(str(png),0,0,1152,748.8);c.save()
        image=Image.fromarray(frame);image.thumbnail((1600,900));image.save(root/(name+'-scene.jpg'),quality=91)
        small=view.copy();small.thumbnail((425,276));contact.paste(small,(0,i*280));crop=Image.fromarray(frame[:,2560:5120]);crop.thumbnail((485,273));contact.paste(crop,(430,i*280));contact_draw.text((925,i*280+30),f'{int(t):03d} s\n{title}',font=label_font,fill='#2c3b3a')
        plates.append({'name':name,'title':title,'time_seconds':t,'image':[8000,5200],'samples':64,'mesh':[192,288],'source_absent':t==288,'camera':[9.8,6.8,12.8],'target':[0,.15,0]});print(json.dumps(plates[-1]),flush=True)
    renderer.close()
    renderer=ChoirRenderer(1600,2000,shadow_size=2048);field=periodic_field(fields[228*24,1],256);shape=ListenerShape(**scene['shapes']['shell']);obj=SceneObject(build_listener(field,192,288,shape),field,transform((0,0,0),turn=.18,tilt=.08))
    portrait=Image.fromarray(renderer.draw_scene([obj,floor_object(-1.6)],camera=(5.4,3.5,7.5),target=(0,.05,0),focal_length=2.6,samples=48,shadow_extent=4.5,shadow_softness=.75));portrait.save(root/'the-source-view.jpg',quality=92);renderer.close()
    contact.save(root/'review.jpg',quality=88)
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':hashes,'performance_manifest_sha256':sha256(performance/'manifest.json'),'plates':plates,
            'source_portrait':{'body':'B','time_seconds':228,'scope':'Isolated display pose of the source just before disconnection.'},
            'files':[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in sorted(root.iterdir()) if p.is_file()],
            'scope':'Matched authored cameras and light. Actual recorded material fields; B is omitted only from the final visible installation. These images are artistic embeddings, not physical photographs.'}
    (root/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'finished':str(root),'files':len(report['files'])}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--performance',default='artifacts/studies/choir-performance-001');p.add_argument('--output',default='artwork/choir-plates-001');main(p.parse_args())
