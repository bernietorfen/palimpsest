"""Sparse authored film titles, applied after the independently computed image."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


SERIF='/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf'
SANS='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def alpha_expression(start,full,end,finish,offset):
    t=f'(t+{offset:.9f})'
    return (f'if(lt({t},{start}),0,if(lt({t},{full}),({t}-{start})/{full-start},'
            f'if(lt({t},{end}),1,if(lt({t},{finish}),({finish}-{t})/{finish-end},0))))')


def text_filter(text,font,size,x,y,color,interval,offset):
    start,full,end,finish=interval
    alpha=alpha_expression(start,full,end,finish,offset)
    return (f"drawtext=fontfile='{font}':text='{text}':fontsize={size}:"
            f"fontcolor={color}:x='{x}':y='{y}':alpha='{alpha}':"
            f"enable='between(t+{offset:.9f},{start},{finish})'")


def filter_chain(width,height,offset=0.):
    for path in (SERIF,SANS):
        if not Path(path).is_file():raise FileNotFoundError(path)
    filters=[]
    # Closing the authored view does not halt the phase evolution beneath it.
    if offset<235:
        filters.append(f'fade=t=out:st={235-offset:.9f}:d=1.2')
    elif offset<236.2:
        gain=(236.2-offset)/1.2
        filters.extend((f'colorchannelmixer=rr={gain}:gg={gain}:bb={gain}',
                        f'fade=t=out:st=0:d={236.2-offset:.9f}'))
    else:
        filters.append('lutrgb=r=0:g=0:b=0')
    filters.append(text_filter('A River Twice',SERIF,round(height*.038),
                               'w*.91-text_w','h*.18','E9E1D3',
                               (2.5,3.3,6.5,7.3),offset))
    ending=(236.4,237.,239.2,240.)
    for text,y,color in (('The phrase returns.','h*.40','E9E1D3'),
                         ('The voice does not.','h*.49','D9A476')):
        filters.append(text_filter(text,SERIF,round(height*.043),
                                   '(w-text_w)/2',y,color,ending,offset))
    filters.append(text_filter('Form, score and study by Codex',SANS,round(height*.014),
                               '(w-text_w)/2','h*.70','B0B5B1',ending,offset))
    return filters


def manifest():
    return {'opening':{'text':'A River Twice','interval':[2.5,3.3,6.5,7.3]},
            'closing_view_fade':[235.,236.2],
            'closing':{'lines':['The phrase returns.','The voice does not.'],
                       'credit':'Form, score and study by Codex',
                       'interval':[236.4,237.,239.2,240.]},
            'fonts':{Path(p).name:hashlib.sha256(Path(p).read_bytes()).hexdigest()
                     for p in (SERIF,SANS)},
            'scope':'Authored titles and a closing observation fade. The exact reference frame and central silence remain without burned-in typography. The closing sentence concerns the composed voice, not destruction of the unitary state.'}


def proof(args):
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams',
                                              '-of','json',args.video],text=True))
    video=next(item for item in probe['streams'] if item['codec_type']=='video')
    width,height=int(video['width']),int(video['height'])
    commands=[]
    for name,start,duration,still in (('opening',0,9,4.5),('closing',233,7,4.5)):
        command=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-n','-ss',str(start),
                 '-i',args.video,'-t',str(duration),'-vf',','.join(filter_chain(width,height,start)),
                 '-c:v','libx264','-preset','fast','-crf','18','-threads','4','-c:a','aac',
                 '-b:a','256k','-movflags','+faststart',str(output/f'{name}.mp4')]
        subprocess.run(command,check=True);commands.append(command)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-n','-ss',str(still),
                        '-i',str(output/f'{name}.mp4'),'-frames:v','1','-q:v','2',
                        str(output/f'{name}.jpg')],check=True)
    shutil.copyfile(__file__,output/'river_typography.py')
    (output/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    report=manifest()
    report['files']={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in sorted(output.iterdir()) if p.is_file()}
    (output/'typography.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video',required=True)
    parser.add_argument('--output',required=True)
    proof(parser.parse_args())
