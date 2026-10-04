"""Small authored form studies before the multi-body second-act scene.

Render on RunPod. The contact sheet is the only image needed for local review.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from studio.choir_geometry import ListenerShape, build_listener
from studio.mesh_geometry import topology_report
from studio.mesh_render import SheetRenderer
from studio.preserve import sha256


def main(args):
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    field = np.load(args.input)['fields'][args.body]
    candidates = (
        ('The listening shell', ListenerShape(), 0, .8),
        ('The open fan', ListenerShape(opening=.64, flare=1.06, height=.90, twist=.18), 0, 1.2),
        ('The folded vessel', ListenerShape(opening=.95, flare=.75, height=1.35, pleats=9, twist=.75), 1, .3),
        ('The deep shell', ListenerShape(opening=.82, flare=1.1, height=.85, pleats=5, twist=.62), 2, 1.),
    )
    renderer = SheetRenderer(1000, 800, shadow_size=2048)
    contact = Image.new('RGB', (1200, 1030), '#ede8da')
    draw = ImageDraw.Draw(contact)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
    records = []
    began = time.monotonic()
    try:
        for index, (title, shape, palette, turn) in enumerate(candidates):
            mesh = build_listener(field, 160, 224, shape)
            frame = renderer.draw(field, mesh=mesh, camera=(5.5, 4.5, 6.4), target=(.2, .1, 0),
                                  turn=turn, samples=32, area_shadow=True, palette=palette,
                                  exposure=1.35, focal_length=1.85, light_angle=.45, shadow_softness=.85)
            image = Image.fromarray(frame)
            path = output / f'form-{index:02d}.png'
            image.save(path)
            image.thumbnail((600, 480))
            x, y = (index % 2) * 600, (index // 2) * 515
            contact.paste(image, (x, y))
            draw.text((x + 18, y + 485), title, fill='#182426', font=font)
            records.append({'name': title, 'shape': asdict(shape), 'palette': palette, 'turn': turn,
                            'image': path.name, 'sha256': sha256(path), 'topology': topology_report(mesh),
                            'renderer': renderer.last_stats})
        contact.save(output / 'review.jpg', quality=88)
    finally:
        renderer.close()
    report = {'input': args.input, 'input_sha256': sha256(Path(args.input)), 'body': args.body,
              'scope': 'Exploratory forms rendered from an actual written receiver field. Not a final scene.',
              'source_sha256': {p: sha256(Path(p)) for p in ('studio/choir_geometry.py', 'studio/choir_look.py')},
              'seconds': time.monotonic() - began, 'candidates': records}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'seconds': report['seconds'], 'candidates': len(records),
                      'all_closed': all(r['topology']['watertight_edges'] for r in records)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='artifacts/studies/choir-exploration-002/case-02/written.npz')
    parser.add_argument('--body', type=int, default=1)
    parser.add_argument('--output', default='artwork/choir-look-001')
    main(parser.parse_args())
