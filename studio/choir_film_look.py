"""Contact sheet for the original second-act camera score. Run on RunPod."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from studio.choir_render import ChoirRenderer
from studio.choir_film import scene_at,Titles
from studio import choir_cinematography as camera
from studio.preserve import sha256


def main(args):
    source=Path(args.performance);output=Path(args.output);output.mkdir(parents=True,exist_ok=False)
    protocol=json.loads((source/'protocol.json').read_text());fields=np.load(source/'fields.npy',mmap_mode='r')
    with np.load(source/'readouts.npz') as stored:readouts={k:stored[k] for k in ('bridge_u','bridge_v','endpoints','gates')}
    times=(7.,27.,45.,72.,116.,140.,170.,214.,234.,241.,250.,282.)
    sheet=Image.new('RGB',(1200,6*367),'#ede8da');draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
    renderer=ChoirRenderer(1600,900);titles=Titles(1600,900);began=time.monotonic();reports=[]
    try:
        for index,t in enumerate(times):
            objects=scene_at(protocol['scene'],fields,readouts,t,protocol['field_fps'],protocol['readout_hz'],96,144)
            frame=renderer.draw_scene(objects,**camera.camera_at(t),samples=24)
            frame=titles.draw(frame,t);path=output/f'frame-{t:07.3f}.png';Image.fromarray(frame).save(path)
            image=Image.fromarray(frame);image.thumbnail((600,338));x=index%2*600;y=index//2*367;sheet.paste(image,(x,y));draw.text((x+12,y+343),f'{t:03.0f} s / {camera.shot_name(t)}',fill='#283a3a',font=font)
            reports.append({'time':t,'camera':camera.camera_at(t),'file':path.name,'sha256':sha256(path),'render':renderer.last_stats})
    finally:renderer.close()
    sheet.save(output/'review.jpg',quality=87)
    (output/'report.json').write_text(json.dumps({'seconds':time.monotonic()-began,'frames':reports},indent=2)+'\n');print(json.dumps({'output':str(output),'seconds':time.monotonic()-began}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--performance',default='artifacts/studies/choir-performance-001');p.add_argument('--output',default='artwork/choir-film-look-001');main(p.parse_args())
