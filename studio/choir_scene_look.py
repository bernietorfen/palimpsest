"""Camera and light studies of one recorded seven-body encounter. Run on RunPod."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from studio.choir_render import ChoirRenderer
from studio.choir_scene import build_scene, load_scene
from studio.mesh_geometry import topology_report
from studio.preserve import sha256


def main(args):
    root = Path(args.input)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    protocol = json.loads((root / 'protocol.json').read_text())
    scene = protocol['scene']
    fields = np.load(root / 'fields.npy', mmap_mode='r')
    readings = np.load(root / 'readouts.npz')
    default = scene['camera']
    candidates = (
        ('First contact / 21 s', 21., 1, default['position'], default['target'], default['focal_length']),
        ('Exchange / 55 s', 55., 1, default['position'], default['target'], default['focal_length']),
        ('After the cut / 70 s', 70., 1, default['position'], default['target'], default['focal_length']),
        ('The night room / 55 s', 55., 0, default['position'], default['target'], default['focal_length']),
        ('Through the choir / 55 s', 55., 1, [5.2, 3.2, 5.6], [.1, .4, 0.], 1.7),
        ('A view from above / 55 s', 55., 1, [.4, 13., 7.], [0., 0., 0.], 2.1),
    )
    renderer = ChoirRenderer(args.width, round(args.width * 9 / 16), shadow_size=2048)
    contact = Image.new('RGB', (1200, 1110), '#ede8da')
    draw = ImageDraw.Draw(contact)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
    reports = []
    began = time.monotonic()
    try:
        for index, (name, t, backdrop, camera, target, focal) in enumerate(candidates):
            frame = int(np.argmin(np.abs(readings['time'] - t)))
            objects = build_scene(scene, fields[frame].astype(np.float32), readings['bridge_u'][frame],
                                  readings['bridge_v'][frame], readings['endpoints'][frame], readings['gates'][frame])
            image = renderer.draw_scene(objects, camera=camera, target=target, focal_length=focal,
                                         samples=args.samples, backdrop=backdrop, exposure=1.05)
            path = output / f'scene-{index:02d}.png'
            Image.fromarray(image).save(path)
            preview = Image.fromarray(image)
            preview.thumbnail((600, 338))
            x, y = index % 2 * 600, index // 2 * 370
            contact.paste(preview, (x, y))
            draw.text((x + 16, y + 343), name, fill='#182426', font=font)
            topology = [topology_report(item.mesh) for item in objects if item.kind != 2]
            reports.append({'name': name, 'time': float(readings['time'][frame]), 'camera': camera, 'target': target,
                            'focal_length': focal, 'backdrop': backdrop, 'image': path.name, 'sha256': sha256(path),
                            'renderer': renderer.last_stats, 'all_objects_closed': all(item['watertight_edges'] for item in topology),
                            'all_objects_finite': all(item['finite'] for item in topology)})
            print(json.dumps({'image': path.name, 'render': renderer.last_stats}), flush=True)
        contact.save(output / 'review.jpg', quality=89)
    finally:
        renderer.close()
    report = {'input': str(root), 'manifest_sha256': sha256(root / 'manifest.json'),
              'source_sha256': {name: sha256(Path(name)) for name in ('studio/choir_scene_look.py', 'studio/choir_scene.py',
                  'studio/choir_geometry.py', 'studio/choir_render.py', 'studio/shaders/choir.frag', 'studio/shaders/choir_composite.frag')},
              'seconds': time.monotonic() - began, 'candidates': reports,
              'scope': 'Six exploratory views of one actual coupled scene record; no independent-body duplication.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'finished': str(output), 'seconds': report['seconds']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='artifacts/studies/choir-scene-001')
    parser.add_argument('--output', default='artwork/choir-scene-look-001')
    parser.add_argument('--width', type=int, default=1600)
    parser.add_argument('--samples', type=int, default=24)
    main(parser.parse_args())
