"""A bounded film contact sheet and temporal continuity report; RunPod only."""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from studio import choir_cinematography as camera


def main(args):
    source=Path(args.film);output=Path(args.output);output.mkdir(parents=True,exist_ok=False)
    times=(59,60,61,62,108,109,110,111,169,170,171,172,228,231,234,237,239,241,243,245,271,276,280,284)
    image=Image.new('RGB',(1200,6*195),'#ede8da');draw=ImageDraw.Draw(image);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
    for i,t in enumerate(times):
        command=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-ss',str(t),'-i',str(source),'-frames:v','1','-vf','scale=300:169','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
        raw=subprocess.run(command,check=True,capture_output=True).stdout;frame=Image.frombytes('RGB',(300,169),raw);x=i%4*300;y=i//4*195;image.paste(frame,(x,y));draw.text((x+8,y+174),f'{t:03d} s',font=font,fill='#243939')
    image.save(output/'review.jpg',quality=88)
    manifest=json.loads(source.with_suffix('').joinpath('manifest.json').read_text());cuts=camera.manifest()['cuts_seconds']
    metrics=[r for r in manifest['metrics'] if 2<r['time']<284 and all(abs(r['time']-c)>.2 for c in cuts)]
    changes=[r['change'] for r in metrics if r['change'] is not None]
    report={'frames':manifest['frames'],'fps':manifest['fps'],'interior_unchanged_frames':sum(x==0 for x in changes),'change_minimum':min(changes),'change_median':float(np.median(changes)),'change_maximum':max(changes),'frame_std_minimum':min(r['std'] for r in metrics),'intentional_cuts':cuts,'largest_changes':sorted(metrics,key=lambda r:r['change'],reverse=True)[:8],'scope':'Decoded sampled frames and deterministic low-resolution temporal metrics. This does not constitute perceptual viewing of the entire film.'}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--film',default='artwork/choir-film-study-001.mp4');parser.add_argument('--output',default='artwork/choir-motion-review-001');main(parser.parse_args())
