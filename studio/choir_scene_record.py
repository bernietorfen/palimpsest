"""A 72-second exploratory scene score for seven actually coupled materials.

This is a visual/motion study, not the final composed second-act performance.
Run on RunPod. No existing study directory is overwritten.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time

import numpy as np
import torch

from studio.choir_material import MaterialChoir, Port, port_footprint
from studio.choir_scene import bridge_specs, load_scene
from studio.material import MaterialConfig
from studio.preserve import sha256
from studio.score import Gesture


SOURCES = ('studio/choir_scene_record.py', 'studio/choir_scene.py', 'studio/choir_material.py',
           'studio/batched_material.py', 'studio/material.py', 'studio/score.py', 'site/choir-scene.json')


def main(args):
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision('highest')
    scene = load_scene()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    source_hashes = {}
    for relative in SOURCES:
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(relative, target)
        source_hashes[relative] = sha256(Path(relative))
    size, rate = scene['material']['studio_size'], scene['material']['rate']
    cfg = MaterialConfig(size=size, dt=1/rate, feedback=scene['material']['feedback'])
    choir = MaterialChoir(cfg, len(scene['bodies']), bridge_specs(scene), beads=scene['bridge']['beads'])
    contacts = ((1, .22, .5), (3, .22, .5), (5, .62, .72))
    footprints = [port_footprint(Port(*p, .16), size, device='cuda', dtype=torch.float32) for p in contacts]
    events = [(0, Gesture(t, 0, level, .65, .8, 3.1)) for t, level in ((3., .75), (10., .62), (17., .8))]
    events += [(1, Gesture(t, 0, level, .55, 1., 3., polarity=sign)) for t, level, sign in ((25., .7, 1), (32., .85, -1), (39., .62, 1))]
    events += [(2, Gesture(t, 0, level, .75, .8, 3.2)) for t, level in ((46., .72), (53., .85), (60., .66))]
    protocol = {'kind': 'exploratory scene score', 'created_utc': datetime.now(timezone.utc).isoformat(),
                'duration': 72, 'fps': args.fps, 'config': asdict(cfg), 'scene': scene,
                'contacts': contacts, 'events': [{'contact': i, **asdict(e)} for i, e in events],
                'connections': 'Six spokes active initially; outer ring opens from 24 to 30 s; every bridge fades from 64 to 68 s.',
                'source_sha256': source_hashes}
    (output / 'protocol.json').write_text(json.dumps(protocol, indent=2) + '\n')
    frames = 72 * args.fps + 1
    fields = np.lib.format.open_memmap(output / 'fields.npy', mode='w+', dtype=np.float16,
                                     shape=(frames, choir.bodies, size, size, 4))
    readings = {key: [] for key in ('time', 'bridge_u', 'bridge_v', 'endpoints', 'gates', 'pitch_hz', 'amplitude', 'memory', 'fatigue')}
    diagnostics = []
    drive = torch.zeros((choir.bodies, 12), device='cuda', dtype=torch.float32)
    force = torch.zeros_like(choir.material.u)
    began = time.monotonic()
    for step in range(72 * rate + 1):
        t = step / rate
        fade = 1 - np.clip((t - 64) / 4, 0, 1)
        outer = np.clip((t - 24) / 6, 0, 1)
        choir.set_connections([fade] * 6 + [outer * fade] * 6)
        if step % (rate // args.fps) == 0:
            frame = step // (rate // args.fps)
            fields[frame] = choir.fields().cpu().numpy().astype(np.float16)
            reading = choir.readout()
            readings['time'].append(t)
            for name, value in (('bridge_u', choir.wave.u), ('bridge_v', choir.wave.v),
                                ('endpoints', choir.wave.coordinates(choir.material.u)), ('gates', choir.gates)):
                readings[name].append(value.cpu().numpy().copy())
            for name in ('pitch_hz', 'amplitude', 'memory', 'fatigue'):
                readings[name].append(reading[name].cpu().numpy())
        if step % (rate * 12) == 0:
            record = choir.diagnostics()
            if not record['finite']:
                raise FloatingPointError('The scene material became non-finite')
            diagnostics.append(record)
            print(json.dumps({'time': t, 'memory': record['memory_rms'], 'finite': True,
                              'elapsed_seconds': time.monotonic() - began}), flush=True)
        if step == 72 * rate:
            break
        force.zero_()
        for index, event in events:
            force[contacts[index][0]] += event.at(t) * footprints[index]
        choir.step(drive, contact_force=force)
    fields.flush()
    np.savez_compressed(output / 'readouts.npz', **{key: np.asarray(value) for key, value in readings.items()})
    state = choir.state_dict()
    np.savez_compressed(output / 'final-state.npz', **{key: value.numpy() for key, value in state['material'].items()},
                        bridge_u=state['bridge_u'].numpy(), bridge_v=state['bridge_v'].numpy(), gates=state['gates'].numpy())
    (output / 'diagnostics.json').write_text(json.dumps(diagnostics, indent=2) + '\n')
    inventory = [{'path': str(path.relative_to(output)), 'bytes': path.stat().st_size, 'sha256': sha256(path)}
                 for path in sorted(output.rglob('*')) if path.is_file()]
    report = {'finished_utc': datetime.now(timezone.utc).isoformat(), 'seconds': time.monotonic() - began,
              'frames': frames, 'field_channels': ['displacement', 'inscription', 'fatigue', 'velocity'],
              'files': inventory, 'scope': 'Exploratory seven-body scene record. All bodies and bridges are simulated together.'}
    (output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'finished': str(output), 'frames': frames, 'seconds': report['seconds']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='artifacts/studies/choir-scene-001')
    parser.add_argument('--fps', type=int, choices=(12, 24), default=12)
    main(parser.parse_args())
