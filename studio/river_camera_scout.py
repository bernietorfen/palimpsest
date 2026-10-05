"""Bounded geometric visibility survey for a connecting-fibre camera passage.

This does not render or judge an image. It ranks camera offsets using direct
scene rays, and leaves lighting, composition and continuous motion to review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from studio.river_blender import build_scene, aim
from studio.river_sequence import frame_state
from studio.river_geometry import phases, woven_relations
from studio.river_cinematography import model_time


def main(args):
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    args.shape, args.shot, args.group, args.choreography, args.time = 'weave', 'wide', None, False, 0.
    args.ten_bit, args.camera_revision = False, False
    scene, camera, dynamic, fibres = build_scene(args)
    lights = [(obj, obj.data.energy) for obj in bpy.data.objects if obj.type == 'LIGHT']
    offsets = []
    for azimuth in range(-180, 180, 30):
        for elevation in (-20, 0, 20, 40, 60):
            for radius in (2.2, 3.4, 5.):
                az, el = math.radians(azimuth), math.radians(elevation)
                offsets.append((radius * math.cos(el) * math.cos(az),
                                radius * math.cos(el) * math.sin(az), radius * math.sin(el)))
    sections = ((136., 142., 147.9), (160., 166., 171.9), (172., 176., 179.9))
    pairs = ((0, 1), (1, 2), (2, 3), (3, 0), (0, 2))
    started = time.monotonic()
    report = {'scope': __doc__, 'sections': [], 'candidate_offsets_per_relation': len(offsets),
              'rays_per_candidate_time': 30, 'camera_lens': 58, 'rendered_frames': 0}
    for times in sections:
        candidates = {(pair, index): {'relation': pair, 'offset': offset, 'times': []}
                      for pair in pairs for index, offset in enumerate(offsets)}
        for seconds in times:
            frame_state(scene, camera, dynamic, fibres, args, seconds, lights)
            dependency = bpy.context.evaluated_depsgraph_get()
            for pair in pairs:
                paths = np.asarray(woven_relations(phases(model_time(seconds)), *pair))
                target = np.mean(paths[:, 96], axis=0)
                points = paths[::3][:, [29, 58, 96, 134, 163]].reshape(-1, 3)
                expected = f'Relation {pair[0]}.{pair[1]}'
                for index, offset in enumerate(offsets):
                    location = target + np.asarray(offset)
                    sample = {'seconds': seconds, 'visible_fraction': 0., 'inside_fraction': 0.,
                              'span': 0., 'location': location.tolist(), 'target': target.tolist()}
                    if location[2] > .2:
                        camera.location = location
                        camera.data.lens = 58
                        aim(camera, target)
                        bpy.context.view_layer.update()
                        visible, inside = 0, 0
                        projected = []
                        for point in points:
                            pixel = world_to_camera_view(scene, camera, Vector(point))
                            projected.append((pixel.x, pixel.y))
                            in_frame = .03 < pixel.x < .97 and .03 < pixel.y < .97 and pixel.z > 0
                            inside += in_frame
                            direction = Vector(point) - camera.location
                            distance = direction.length
                            hit, _, _, _, obj, _ = scene.ray_cast(dependency, camera.location,
                                direction.normalized(), distance=distance + .01)
                            visible += in_frame and hit and obj.name == expected
                        xy = np.asarray(projected)
                        sample.update(visible_fraction=visible / len(points), inside_fraction=inside / len(points),
                                      span=float(np.max(np.ptp(xy, axis=0))))
                    candidates[(pair, index)]['times'].append(sample)
        ranked = []
        for candidate in candidates.values():
            views = candidate['times']
            least_visibility = min(item['visible_fraction'] for item in views)
            mean_visibility = float(np.mean([item['visible_fraction'] for item in views]))
            least_inside = min(item['inside_fraction'] for item in views)
            span_fit = float(np.mean([math.exp(-((item['span'] - .6) / .5) ** 2) for item in views]))
            candidate['score'] = .60 * least_visibility + .20 * mean_visibility + .10 * least_inside + .10 * span_fit
            candidate['minimum_visibility'] = least_visibility
            ranked.append(candidate)
        ranked.sort(key=lambda item: item['score'], reverse=True)
        by_relation = [next(item for item in ranked if item['relation'] == pair) for pair in pairs]
        report['sections'].append({'times': times, 'top_candidates': ranked[:8], 'best_per_relation': by_relation})
        print(json.dumps({'times': times, 'best': ranked[0]}), flush=True)
    own = Path(__file__).read_bytes()
    (output / 'river_camera_scout.py').write_bytes(own)
    report.update(elapsed_seconds=time.monotonic() - started, source_sha256=hashlib.sha256(own).hexdigest())
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    parser.add_argument('--samples', type=int, default=8)
    parser.add_argument('--along', type=int, default=193)
    parser.add_argument('--across', type=int, default=33)
    main(parser.parse_args(sys.argv[sys.argv.index('--') + 1:]))
