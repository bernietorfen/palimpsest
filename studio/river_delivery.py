"""Assemble and verify a film edition on the production host, without frame dumps."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time


def run(command, *, capture=False):
    return subprocess.run(command,check=True,capture_output=capture,text=capture)


def identity(path):
    path=Path(path)
    digest=hashlib.sha256()
    with path.open('rb') as source:
        while block:=source.read(1024*1024): digest.update(block)
    return {'name':path.name,'bytes':path.stat().st_size,'sha256':digest.hexdigest()}


def probe(path):
    return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format',
                           '-of','json',str(path)],capture=True).stdout)


def stream(record,kind):
    return next(item for item in record['streams'] if item['codec_type']==kind)


def checked_video(path,duration):
    record=probe(path)
    video,audio=stream(record,'video'),stream(record,'audio')
    assert abs(float(record['format']['duration'])-duration) <= .05
    assert audio['channels']==2 and audio['sample_rate']=='48000'
    assert video['width']>0 and video['height']>0
    return {'duration':record['format']['duration'],
            'video':{key:video.get(key) for key in ('codec_name','profile','width','height',
                      'pix_fmt','avg_frame_rate','nb_frames','color_range','color_space',
                      'color_transfer','color_primaries')},
            'audio':{key:audio.get(key) for key in ('codec_name','sample_rate','channels','duration')}}


def compact_command(screening,output,*,threads=6,filter_threads=4):
    """The optional bandwidth edition always derives from the screening master."""
    return ['ffmpeg','-hide_banner','-loglevel','error','-xerror','-nostdin','-n',
            '-threads',str(threads),'-filter_threads',str(filter_threads),
            '-i',str(screening),'-map','0:v:0','-map','0:a:0',
            '-vf','scale=1280:720:flags=lanczos','-c:v','libx264',
            '-pix_fmt','yuv420p','-preset','slow','-crf','21','-threads',str(threads),
            '-c:a','copy','-color_range','tv','-color_primaries','bt709',
            '-color_trc','bt709','-colorspace','bt709',
            '-metadata','title=A River Twice','-metadata','artist=Codex',
            '-movflags','+faststart',str(output)]


def main(args):
    output=Path(args.output)
    output.mkdir(parents=True,exist_ok=False)
    began=time.monotonic()
    video,audio=Path(args.video),Path(args.audio)
    source_video,source_audio=probe(video),probe(audio)
    source_stream=stream(source_video,'video')
    assert abs(float(source_video['format']['duration'])-240.) <= .05
    assert abs(float(source_audio['format']['duration'])-240.) <= 1/48000
    assert stream(source_audio,'audio')['channels']==2
    compact=bool(getattr(args,'compact',False))
    if compact:
        if (int(source_stream['width'])*9 != int(source_stream['height'])*16
                or int(source_stream['width'])<1280
                or Fraction(source_stream['avg_frame_rate']) != 24):
            raise ValueError('The compact edition requires a 16:9 source at 24 fps, at least 1280 pixels wide')
    (output/'source').mkdir()
    shutil.copyfile(__file__,output/'source/river_delivery.py')
    inputs={'video':identity(video),'audio':identity(audio)}
    for kind,path in (('render',args.render_receipt),('audio',args.audio_receipt)):
        if path:
            source=Path(path)
            shutil.copyfile(source,output/'source'/f'{kind}-receipt.json')
            inputs[kind+'_receipt']=identity(source)
    base=['ffmpeg','-hide_banner','-loglevel','error','-xerror','-nostdin','-n','-threads','6','-filter_threads','4']
    screening=output/'river-screening.mp4'
    commands=[]
    command=base+['-i',str(video),'-i',str(audio),'-map','0:v:0','-map','1:a:0',
                  '-c:v','copy','-c:a','aac','-b:a','320k','-ar','48000','-t','240',
                  '-metadata','title=A River Twice','-metadata','artist=Codex',
                  '-movflags','+faststart',str(screening)]
    if source_stream['codec_name']=='hevc':
        command[-1:-1]=['-tag:v','hvc1']
    commands.append(command);run(command)
    width=min(int(source_stream['width']),args.width)
    viewing=output/'river-viewing.mp4'
    command=base+['-i',str(screening),'-map','0:v:0','-map','0:a:0',
                  '-vf',f'scale={width}:-2:flags=lanczos','-c:v','libx264',
                  '-pix_fmt','yuv420p','-preset','slow','-crf',str(args.crf),'-threads','6',
                  '-c:a','copy','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709',
                  '-metadata','title=A River Twice','-metadata','artist=Codex',
                  '-movflags','+faststart',str(viewing)]
    commands.append(command);run(command)
    if compact:
        command=compact_command(screening,output/'river-compact.mp4')
        commands.append(command);run(command)
    command=base+['-ss',str(args.poster_time),'-i',str(viewing),'-frames:v','1',
                  '-q:v','2',str(output/'river-poster.jpg')]
    commands.append(command);run(command)
    if args.captions:
        captions=Path(args.captions)
        frozen_captions=output/'source/captions-source.vtt'
        shutil.copyfile(captions,frozen_captions)
        inputs['captions']={**identity(frozen_captions),'name':captions.name}
        command=base+['-i',str(frozen_captions),'-map','0:s:0','-c:s','webvtt',str(output/'river-notes.vtt')]
        commands.append(command);run(command)
    names=['river-screening.mp4','river-viewing.mp4']
    if compact: names.append('river-compact.mp4')
    editions={name:checked_video(output/name,240.) for name in names}
    # Decode every frame/sample in the lightweight edition, once.
    run(base+['-i',str(viewing),'-f','null','-'])
    loudness=run(['ffmpeg','-hide_banner','-nostdin','-i',str(viewing),'-vn',
                  '-af','ebur128=peak=true','-f','null','-'],capture=True).stderr
    (output/'viewing-loudness.txt').write_text(loudness)
    silence=run(['ffmpeg','-hide_banner','-nostdin','-ss','120','-t','1.8','-i',str(viewing),
                 '-vn','-af','astats=metadata=0:reset=0','-f','null','-'],capture=True).stderr
    (output/'viewing-silence.txt').write_text(silence)
    # AAC can smear a boundary by a transform block, so inspect the interior.
    peaks=re.findall(r'Peak level dB: ([-+\w.]+)',silence)
    assert peaks and all(value=='-inf' or float(value)<-100 for value in peaks)
    # Commands contain only artifact paths and public metadata, never credentials.
    (output/'encoding-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    report={'title':'A River Twice','edition':args.edition,'created_utc':datetime.now(timezone.utc).isoformat(),
            'inputs':inputs,'editions':editions,'viewing_decoded_without_error':True,
            'encoded_silence_interior':{'start':120.,'end':121.8,'peak_db':peaks},
            'poster_time':args.poster_time,'elapsed_seconds':time.monotonic()-began,
            'source_sha256':identity(Path(__file__))['sha256'],
            'scope':'Measured encoding and playback-file integrity. No perceptual listening or emotional-quality verdict.',
            'files':{str(p.relative_to(output)):identity(p) for p in sorted(output.rglob('*')) if p.is_file()}}
    if compact:
        report['compact']={'source':report['files']['river-screening.mp4'],
                           'resolution':[1280,720],'fps':24,'video_encoder':'libx264',
                           'pixel_format':'yuv420p','preset':'slow','crf':21,
                           'scale_filter':'lanczos','audio':'packet copy'}
    (output/'delivery.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'output':str(output),'edition':args.edition,'editions':editions,
                      'elapsed_seconds':report['elapsed_seconds']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video',required=True)
    parser.add_argument('--audio',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--render-receipt')
    parser.add_argument('--audio-receipt')
    parser.add_argument('--captions')
    parser.add_argument('--width',type=int,default=1920)
    parser.add_argument('--crf',type=int,default=20)
    parser.add_argument('--compact',action='store_true',
                        help='Also make the 1280x720 H.264 CRF-21 edition from the screening master')
    parser.add_argument('--poster-time',type=float,default=188.)
    parser.add_argument('--edition',choices=('draft','final'),default='draft')
    main(parser.parse_args())
