"""Declared exploratory coupling sweep, not the final second-act experiment.

Three otherwise identical worlds per tension: linked, isolated, and linked then
fully erased. Only each world's first body is directly written. All connections
are removed and all motion/phase/delay reset before the common receiver probe.
Run on RunPod; record the entire source and parameter boundary before execution.
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

from studio.choir_material import Bridge, MaterialChoir, Port, port_footprint
from studio.material import MaterialConfig
from studio.preserve import sha256
from studio.score import Gesture


SOURCES = ('studio/choir_explore.py', 'studio/choir_material.py', 'studio/batched_material.py',
           'studio/material.py', 'studio/score.py', 'research/SECOND-ACT.md')


def chain(offset, tension, width, alignment):
    outgoing = (.58, .50) if alignment == 'overlap' else (.32, .28)
    return (Bridge(Port(offset, .19, .37, width), Port(offset + 1, .71, .53, width), tension=tension),
            Bridge(Port(offset + 1, *outgoing, width), Port(offset + 2, .63, .68, width), tension=tension))


def main(args):
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision('highest')
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    source_hashes = {}
    for relative in SOURCES:
        source = Path(relative)
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        source_hashes[relative] = sha256(source)
    config = MaterialConfig(size=args.size, dt=1/args.rate, feedback=args.feedback)
    protocol = {'kind': 'exploratory, not confirmatory', 'created_utc': datetime.now(timezone.utc).isoformat(),
                'config': asdict(config), 'tensions': args.tensions, 'write_seconds': 24, 'probe_seconds': 14,
                'drive': args.drive, 'port_width': args.port_width, 'alignment': args.alignment, 'contact_gain': args.contact_gain,
                'worlds': ['linked', 'isolated', 'linked-then-erased'], 'source_sha256': source_hashes,
                'intervention': 'All links zero and all displacement/velocity/phase/delay transients reset before identical receiver probes. Retained fields additionally erased only in the third world.'}
    (output / 'protocol.json').write_text(json.dumps(protocol, indent=2) + '\n')
    gestures = (Gesture(0, 0, .55, .5, 1.1, 2.4), Gesture(5.5, 4, .42, .6, .6, 2.8),
                Gesture(11.5, 2, .52, .8, .6, 2.8), Gesture(17.5, 7, .43, .4, .8, 2.4))
    probes = (Gesture(.5, 1, .30, .7, .8, 2.2), Gesture(5.2, 5, .25, .7, .4, 2.5),
              Gesture(9.4, 2, .24, .5, .3, 2.5))
    began = time.monotonic()
    reports = []
    for case, tension in enumerate(args.tensions):
        directory = output / f'case-{case:02d}'
        directory.mkdir()
        edges = tuple(edge for offset in (0, 3, 6) for edge in chain(offset, tension, args.port_width, args.alignment))
        choir = MaterialChoir(config, 9, edges, beads=16)
        choir.set_connections([1, 1, 0, 0, 1, 1])
        drive = torch.zeros((9, 12), device='cuda', dtype=torch.float32)
        contact = torch.zeros_like(choir.material.u)
        footprint = port_footprint(Port(0, .19, .37, args.port_width), args.size, device='cuda', dtype=torch.float32)
        fields, times, waves, diagnostics = [], [], [], []
        for step in range(round(24 / config.dt)):
            t = step * config.dt
            drive.zero_()
            contact.zero_()
            if args.drive == 'modal':
                for gesture in gestures:
                    drive[[0, 3, 6], gesture.voice] += gesture.at(t)
            else:
                strength = sum(gesture.at(t) for gesture in gestures) * args.contact_gain
                contact[[0, 3, 6]] = strength * footprint
            if step % args.rate == 0:
                fields.append(choir.fields()[:3].cpu().numpy().astype(np.float16))
                waves.append(choir.wave.u[:2].cpu().numpy())
                times.append(t)
                diagnostics.append(choir.diagnostics())
            choir.step(drive, contact_force=contact if args.drive == 'contact' else None)
        written = choir.diagnostics()
        retained = choir.fields().cpu().numpy()
        np.savez_compressed(directory / 'written.npz', fields=retained,
                            bridge_u=choir.wave.u.cpu().numpy(), bridge_v=choir.wave.v.cpu().numpy())
        if not written['finite']:
            raise FloatingPointError('Exploratory choir became non-finite')
        # Verify the erased world really had the same connected history first.
        before_erasure = float((choir.material.p[:3] - choir.material.p[6:]).abs().max())
        choir.set_connections([0] * 6)
        choir.material.p[6:].zero_()
        choir.material.z[6:].zero_()
        choir.reset_transients()
        pitches = []
        for step in range(round(14 / config.dt)):
            t = step * config.dt
            drive.zero_()
            for gesture in probes:
                drive[[1, 2, 4, 5, 7, 8], gesture.voice] += gesture.at(t)
            if step % (args.rate // 24) == 0:
                pitches.append(choir.readout()['pitch_hz'].cpu().numpy())
            choir.step(drive)
        pitches = np.stack(pitches)
        np.savez_compressed(directory / 'probe.npz', pitch_hz=pitches,
                            worlds=np.array(['linked'] * 3 + ['isolated'] * 3 + ['erased'] * 3))
        np.savez_compressed(directory / 'motion-samples.npz', time=np.array(times), fields=np.array(fields), bridge_u=np.array(waves))
        comparisons = []
        for receiver in (1, 2):
            difference = pitches[:, receiver].astype(np.float64) - pitches[:, receiver + 3]
            erased = pitches[:, receiver + 6].astype(np.float64) - pitches[:, receiver + 3]
            comparisons.append({'receiver': receiver, 'linked_minus_isolated_rms_hz': float(np.sqrt(np.mean(difference ** 2))),
                                'maximum_difference_hz': float(np.abs(difference).max()),
                                'erased_minus_isolated_maximum_hz': float(np.abs(erased).max()),
                                'written_memory_rms': written['memory_rms'][receiver],
                                'written_fatigue_mean': written['fatigue_mean'][receiver]})
        report = {'case': case, 'tension': tension, 'written': written, 'after_probe': choir.diagnostics(),
                  'connected_history_copy_error': before_erasure, 'receivers': comparisons,
                  'scope': 'Exploratory finite-model transfer after removing every bridge and resetting all transients. No hearing or physical-material claim.'}
        (directory / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        reports.append(report)
        print(json.dumps({'case': case, 'tension': tension, 'receivers': comparisons,
                          'finite': report['after_probe']['finite'], 'elapsed_seconds': time.monotonic() - began}), flush=True)
    inventory = [{'path': str(path.relative_to(output)), 'bytes': path.stat().st_size, 'sha256': sha256(path)}
                 for path in sorted(output.rglob('*')) if path.is_file()]
    summary = {'finished_utc': datetime.now(timezone.utc).isoformat(), 'seconds': time.monotonic() - began,
               'protocol': protocol, 'cases': reports, 'files': inventory}
    (output / 'manifest.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'completed': str(output), 'seconds': summary['seconds'], 'files': len(inventory)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='artifacts/studies/choir-exploration-001')
    parser.add_argument('--size', type=int, default=64)
    parser.add_argument('--rate', type=int, choices=(96, 192), default=96)
    parser.add_argument('--tensions', type=float, nargs='+', default=[.35, .8, 1.6, 3.])
    parser.add_argument('--drive', choices=('modal', 'contact'), default='modal')
    parser.add_argument('--port-width', type=float, default=.12)
    parser.add_argument('--alignment', choices=('separated', 'overlap'), default='separated')
    parser.add_argument('--contact-gain', type=float, default=1.6)
    parser.add_argument('--feedback', type=float, default=.08)
    main(parser.parse_args())
