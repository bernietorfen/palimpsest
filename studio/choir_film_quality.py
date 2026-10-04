"""Full decode and measured delivery checks for the second-act film."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
from studio.preserve import sha256


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))


def main(args):
    film=Path(args.film);output=Path(args.output)
    if output.exists():raise FileExistsError(output)
    data=probe(film);video=next(s for s in data['streams'] if s['codec_type']=='video');audio=next(s for s in data['streams'] if s['codec_type']=='audio')
    assert len(data['streams'])==2
    assert (video['width'],video['height'])==((1920,1080) if args.viewing else (3840,2160))
    assert video['codec_name']==('h264' if args.viewing else 'hevc')
    assert video['pix_fmt']==('yuv420p' if args.viewing else 'yuv420p10le')
    assert video['avg_frame_rate']=='24/1' and int(video['nb_frames'])==6912
    for stream in (video,audio):assert float(stream['start_time'])==0 and abs(float(stream['duration'])-288)<1e-6
    assert audio['sample_rate']=='48000' and audio['channels']==2
    for key in ('color_space','color_transfer','color_primaries'):assert video[key]=='bt709'
    assert video['color_range']=='tv'
    decode=subprocess.run(['ffmpeg','-hide_banner','-nostdin','-v','error','-threads','6','-i',str(film),'-map','0:v:0','-map','0:a:0','-f','null','-'],capture_output=True,text=True)
    assert decode.returncode==0 and not decode.stderr.strip(),decode.stderr
    result={'verified_utc':datetime.now(timezone.utc).isoformat(),'film':str(film),'bytes':film.stat().st_size,'sha256':sha256(film),'full_decode_passed':True,
        'frames':6912,'fps':24,'duration_seconds':288,'video':{k:video[k] for k in ('codec_name','profile','width','height','pix_fmt','color_space','color_range','color_transfer','color_primaries','start_time','duration')},
        'audio':{k:audio[k] for k in ('codec_name','sample_rate','channels','start_time','duration')},'scope':'Complete error-free decode, container/stream timing and encoded color metadata. No perceptual listening claim.'}
    if not args.viewing:
        manifest=film.with_suffix('')/'manifest.json';original=json.loads(manifest.read_text());assert original['output_sha256']==result['sha256']
        result['generation_manifest_sha256']=sha256(manifest)
        result['camera_metadata_correction']={'matched_opening_seconds':[5,28],'matched_return_seconds':[248,271],'interval_convention':'half-open','matched_duration_seconds':23,
            'reason':'The original manifest prose overstated the exact close-camera interval by one second. The opening starts widening at 28 s; the returning close view lasts until 272 s. Source captures and all frames are preserved unchanged. The two widening transitions have different durations.'}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--film',default='artwork/masters/choir-of-absences-4k.mp4');p.add_argument('--output',default='research/choir-master-quality-001.json');p.add_argument('--viewing',action='store_true');main(p.parse_args())
