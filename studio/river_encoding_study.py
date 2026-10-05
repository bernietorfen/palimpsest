"""Compare bounded viewing encodes from completed 4K film sections on RunPod."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from PIL import Image, ImageDraw, ImageFont


def run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True)


def identity(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return {'name': path.name, 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def still(source, seconds, output):
    run(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-threads', '2',
         '-ss', str(seconds), '-i', str(source), '-frames:v', '1', '-vf',
         'scale=1920:1080:flags=lanczos,format=rgb24', '-threads', '1', str(output)])


def main(args):
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    began = time.monotonic()
    sources = [Path(path) for path in args.section]
    report = {'scope': 'Two completed twelve-second sections; SSIM and native-size crops compare codec loss, not artistic merit.',
              'sources': [identity(source) for source in sources], 'encodes': []}
    for index, source in enumerate(sources):
        reference = output / f'section-{index}-reference.png'
        still(source, 5.5, reference)
        images = [('4K source, scaled to 1080p', reference)]
        for crf in (18, 20, 22):
            target = output / f'section-{index}-crf-{crf}.mp4'
            start = time.monotonic()
            run(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-threads', '2',
                 '-filter_threads', '1', '-i', str(source), '-an', '-vf',
                 'scale=1920:1080:flags=lanczos', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                 '-crf', str(crf), '-preset', 'slow', '-threads', '2',
                 '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
                 '-movflags', '+faststart', str(target)])
            elapsed = time.monotonic() - start
            measure = run(['ffmpeg', '-hide_banner', '-nostdin', '-threads', '2', '-i', str(source),
                '-threads', '2', '-i', str(target), '-filter_complex_threads', '1', '-lavfi',
                '[0:v]setpts=PTS-STARTPTS,scale=1920:1080:flags=lanczos,format=yuv420p[r];'
                '[1:v]setpts=PTS-STARTPTS[t];[r][t]ssim', '-an', '-f', 'null', '-'])
            match = re.search(r'SSIM Y:([\d.]+).*?U:([\d.]+).*?V:([\d.]+).*?All:([\d.]+)', measure.stderr)
            if not match:
                raise ValueError('SSIM measurement was not reported')
            sample = output / f'section-{index}-crf-{crf}.png'
            still(target, 5.5, sample)
            images.append((f'Viewing CRF {crf}', sample))
            report['encodes'].append({'source': source.name, 'section': index, 'crf': crf,
                'identity': identity(target), 'encode_seconds': elapsed,
                'ssim': dict(zip(('y', 'u', 'v', 'all'), map(float, match.groups())))})
        # Crops use the same image coordinates and retain one pixel per screen pixel.
        boxes = ((460, 170, 1040, 540), (840, 560, 1420, 930))
        sheet = Image.new('RGB', (1160, 820 * 2), (14, 19, 21))
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.load_default(size=17)
        for row, (label, filename) in enumerate(images):
            with Image.open(filename) as frame:
                for column, box in enumerate(boxes):
                    sheet.paste(frame.crop(box), (column * 580, row * 410 + 32))
            draw.text((12, row * 410 + 8), label, fill=(225, 216, 200), font=font)
        sheet.save(output / f'section-{index}-comparison.jpg', quality=96)
    report.update(elapsed_seconds=time.monotonic() - began,
                  source_code=identity(Path(__file__)),
                  files=[identity(path) for path in sorted(output.iterdir()) if path.is_file()])
    if sum(item['bytes'] for item in report['files']) > 200_000_000:
        raise ValueError('Comparison exceeded its storage bound')
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'encodes': report['encodes'],
                      'elapsed_seconds': report['elapsed_seconds']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--section', action='append', required=True)
    parser.add_argument('--output', required=True)
    main(parser.parse_args())
