"""Predeclared imperfect-pressure experiment for the original material.

Run on RunPod. Independent cases share GPU execution, never material state.
The scalar and original-atlas admission checks precede perturbed trajectories.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from itertools import permutations
import json
import math
from pathlib import Path
import shutil
import time

import numpy as np
from scipy.spatial.distance import cdist
import torch

from studio.assay import excite, relax
from studio.batched_material import BatchedMaterial
from studio.material import MaterialConfig, PalimpsestMaterial
from studio.preserve import sha256
from studio.score import Gesture


VOICES = (0, 4, 2, 7, 3)
ORDERS = list(permutations(range(5)))
LABELS = [''.join('ABCDE'[i] for i in order) for order in ORDERS]
SEVERITIES = (.01, .03, .10)
SEED = 2026100403
SOURCE_FILES = ['studio/pressure_study.py', 'studio/batched_material.py',
                'studio/material.py', 'studio/assay.py', 'studio/score.py',
                'studio/preserve.py', 'studio/simulate.py', 'research/PRESSURE-STUDY.md']


def writing_drives(orders, factors, config):
    steps = round(24 / config.dt)
    envelopes = np.array([[Gesture(i * 4., i, .4, .6, .8, 1.8).at(step * config.dt)
                           for i in range(5)] for step in range(steps)], dtype=np.float32)
    drives = np.zeros((steps, len(orders), 12), dtype=np.float32)
    for row, order in enumerate(orders):
        for position, symbol in enumerate(order):
            drives[:, row, VOICES[symbol]] = envelopes[:, position] * factors[row, position]
    return torch.as_tensor(drives, device=config.device, dtype=getattr(torch, config.dtype))


def probe_drives(config):
    return torch.as_tensor(np.stack([excite(step * config.dt, (1, 5, 2))
                                    for step in range(round(14 / config.dt))]),
                           device=config.device, dtype=getattr(torch, config.dtype))


def state_difference(batch, references):
    result = {}
    for name in ('u', 'v', 'p', 'z', 'delay', 'echo_phase'):
        deltas = []
        raw = []
        for index, reference in enumerate(references):
            actual = batch.delay[:, index] if name == 'delay' else getattr(batch, name)[index]
            difference = actual - getattr(reference, name)
            raw.append(float(difference.abs().max()))
            if name == 'echo_phase':
                difference = torch.remainder(difference + math.pi, 2 * math.pi) - math.pi
            deltas.append(float(difference.abs().max()))
        result[name] = max(deltas)
        if name == 'echo_phase':
            result['echo_phase_raw'] = max(raw)
    return result


def scalar_admission(output):
    selected = ['ABCDE', 'ACBED', 'ABCED', 'DEABC']
    orders = [ORDERS[LABELS.index(label)] for label in selected]
    reports = []
    started = time.monotonic()
    for rate in (96, 192):
        config = MaterialConfig(dt=1 / rate, feedback=.08)
        batch = BatchedMaterial(config, len(orders))
        references = [PalimpsestMaterial(config) for _ in orders]
        drives = writing_drives(orders, np.ones((len(orders), 5), np.float32), config)
        for step in range(len(drives)):
            batch.step(drives[step])
            for index, reference in enumerate(references):
                reference.step(drives[step, index], feedback=.08)
        written = state_difference(batch, references)
        batch.reset_transients()
        for reference in references:
            relax(reference)
        probe = probe_drives(config)
        batch_pitches, reference_pitches = [], []
        for step in range(len(probe)):
            if step % (rate // 24) == 0:
                batch_pitches.append(batch.tuning()[2].cpu().numpy())
                reference_pitches.append(np.stack([m.readout()['pitch_hz'].cpu().numpy() for m in references]))
            batch.step(probe[step].expand(len(orders), -1))
            for reference in references:
                reference.step(probe[step], feedback=.08)
        after = state_difference(batch, references)
        delta = np.asarray(batch_pitches, dtype=float) - np.asarray(reference_pitches, dtype=float)
        admitted = batch.finite() and all(value <= .0002 for state in (written, after)
                                         for name, value in state.items() if name != 'echo_phase_raw')
        report = {'rate': rate, 'histories': selected, 'written_state_max_absolute': written,
                  'probed_state_max_absolute': after, 'probe_pitch_rms_hz': float(np.sqrt(np.mean(delta * delta))),
                  'probe_pitch_max_absolute_hz': float(np.abs(delta).max()), 'admitted': admitted}
        reports.append(report)
        print(json.dumps({'scalar_admission': report, 'elapsed_seconds': time.monotonic() - started}), flush=True)
    report = {'cases': reports, 'state_tolerance': .0002, 'phase_error': 'circular modulo 2*pi',
              'admitted': all(item['admitted'] for item in reports), 'seconds': time.monotonic() - started}
    (output / 'scalar-admission.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    if not report['admitted']:
        raise ValueError('The batch implementation failed the predeclared scalar admission check')
    return report


def run_batch(orders, factors, config):
    material = BatchedMaterial(config, len(orders))
    drives = writing_drives(orders, factors, config)
    for step in range(len(drives)):
        material.step(drives[step])
    if not material.finite():
        raise FloatingPointError('A written material became non-finite')
    retained = {'memory_rms': material.p.square().mean(dim=(-2, -1)).sqrt().cpu().numpy(),
                'fatigue_mean': material.z.mean(dim=(-2, -1)).cpu().numpy()}
    material.reset_transients()
    probe = probe_drives(config)
    stride = round(1 / (24 * config.dt))
    pitches = torch.empty((len(orders), 336, 12), device=material.device, dtype=material.dtype)
    for step in range(len(probe)):
        if step % stride == 0:
            pitches[:, step // stride] = material.tuning()[2]
        material.step(probe[step].expand(len(orders), -1))
    if not material.finite() or not bool(torch.isfinite(pitches).all()):
        raise FloatingPointError('A probed material became non-finite')
    return pitches.cpu().numpy(), retained


def identify(pitches, truth, canonical):
    features = pitches.reshape(len(pitches), -1).astype(np.float64)
    references = canonical.reshape(120, -1).astype(np.float64)
    distances = cdist(features, references, metric='euclidean') / math.sqrt(features.shape[1])
    predicted = distances.argmin(axis=1)
    own = distances[np.arange(len(truth)), truth]
    distances[np.arange(len(truth)), truth] = np.inf
    other = distances.min(axis=1)
    margins = other - own
    confusion = np.zeros((120, 120), np.int32)
    np.add.at(confusion, (truth, predicted), 1)
    per_history = [{'history': label, 'correct': int(confusion[i, i]), 'tested': int(confusion[i].sum())}
                   for i, label in enumerate(LABELS)]
    summary = {'tested': len(truth), 'correct': int(np.count_nonzero(predicted == truth)),
               'fraction_correct': float(np.mean(predicted == truth)),
               'median_correct_history_rms_hz': float(np.median(own)),
               'maximum_correct_history_rms_hz': float(own.max()),
               'minimum_margin_hz': float(margins.min()), 'median_margin_hz': float(np.median(margins)),
               'near_ties_within_1e_minus_9_hz': int(np.count_nonzero(np.abs(margins) <= 1e-9)),
               'per_history': per_history, 'confusion': confusion.tolist()}
    return summary, {'predicted': predicted, 'correct_distance_hz': own, 'other_distance_hz': other,
                     'margin_hz': margins}


def main(args):
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision('highest')
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for relative in SOURCE_FILES:
        path = Path(relative)
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        hashes[relative] = sha256(path)
    began = time.monotonic()
    admission = scalar_admission(output)
    if args.check_only:
        print(json.dumps({'finished': 'scalar admission only', 'seconds': time.monotonic() - began}), flush=True)
        return
    rng = np.random.Generator(np.random.PCG64(SEED))
    errors = rng.uniform(-1, 1, size=(120, 8, 5))
    np.save(output / 'pressure-errors.npy', errors)
    summaries, predictions = {}, {}
    for rate in (96, 192):
        config = MaterialConfig(dt=1 / rate, feedback=.08)
        directory = output / f'rate-{rate}'
        directory.mkdir()
        original = np.load(Path(args.atlas) / f'rate-{rate}' / 'atlas.npz')
        if original['labels'].tolist() != LABELS:
            raise ValueError('Canonical atlas label order differs')
        canonical = original['pitch_hz'].astype(np.float32)
        baseline = []
        for begin in range(0, 120, args.batch_size):
            stop = min(120, begin + args.batch_size)
            pitches, retained = run_batch(ORDERS[begin:stop], np.ones((stop - begin, 5), np.float32), config)
            np.savez_compressed(directory / f'canonical-{begin:03d}.npz', labels=np.array(LABELS[begin:stop]),
                                pitch_hz=pitches, **retained)
            baseline.append(pitches)
            print(json.dumps({'rate': rate, 'canonical_completed': stop, 'seconds': time.monotonic() - began}), flush=True)
        baseline = np.concatenate(baseline)
        delta = baseline.astype(float) - canonical.astype(float)
        same = np.sqrt(np.mean(delta * delta, axis=(1, 2)))
        control, _ = identify(baseline, np.arange(120), canonical)
        baseline_report = {'maximum_same_history_rms_hz': float(same.max()), 'correct': control['correct'],
                           'tested': 120, 'tolerance_rms_hz': .001,
                           'admitted': bool(same.max() <= .001 and control['correct'] == 120)}
        (directory / 'canonical-admission.json').write_text(json.dumps(baseline_report, indent=2) + '\n')
        if not baseline_report['admitted']:
            raise ValueError(f'The {rate} Hz batch controls failed comparison with the original atlas')
        count = 8 if rate == 96 else 1
        summaries[str(rate)] = {'canonical': baseline_report, 'pressures': {}}
        for severity in SEVERITIES:
            factors = (1 + severity * errors[:, :count]).astype(np.float32).reshape(-1, 5)
            truth = np.repeat(np.arange(120), count)
            realizations = np.tile(np.arange(count), 120)
            records = []
            folder = directory / f'pressure-{round(severity * 100):02d}'
            folder.mkdir()
            for begin in range(0, len(truth), args.batch_size):
                stop = min(len(truth), begin + args.batch_size)
                orders = [ORDERS[i] for i in truth[begin:stop]]
                pitches, retained = run_batch(orders, factors[begin:stop], config)
                np.savez_compressed(folder / f'batch-{begin:04d}.npz',
                                    labels=np.array([LABELS[i] for i in truth[begin:stop]]),
                                    realization=realizations[begin:stop], pressure_factors=factors[begin:stop],
                                    pitch_hz=pitches, **retained)
                records.append(pitches)
                print(json.dumps({'rate': rate, 'severity': severity, 'completed': stop,
                                  'of': len(truth), 'seconds': time.monotonic() - began}), flush=True)
            pitches = np.concatenate(records)
            report, detail = identify(pitches, truth, canonical)
            np.savez_compressed(folder / 'identification.npz', truth=truth, realization=realizations,
                                pressure_factors=factors, **detail)
            (folder / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
            summaries[str(rate)]['pressures'][str(severity)] = report
            predictions[(rate, severity)] = detail['predicted'].reshape(120, count)
            print(json.dumps({'rate': rate, 'severity': severity, 'correct': report['correct'],
                              'tested': report['tested'], 'median_margin_hz': report['median_margin_hz']}), flush=True)
    refinement = {}
    for severity in SEVERITIES:
        coarse = predictions[(96, severity)][:, 0]
        fine = predictions[(192, severity)][:, 0]
        refinement[str(severity)] = {'same_predicted_label': int(np.count_nonzero(coarse == fine)),
                                     'tested': 120, 'coarse_correct': int(np.count_nonzero(coarse == np.arange(120))),
                                     'fine_correct': int(np.count_nonzero(fine == np.arange(120)))}
    files = [{'path': str(path.relative_to(output)), 'bytes': path.stat().st_size, 'sha256': sha256(path)}
             for path in sorted(output.rglob('*')) if path.is_file()]
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': hashes,
              'protocol_sha256': hashes['research/PRESSURE-STUDY.md'], 'seed': SEED,
              'config': asdict(MaterialConfig(feedback=.08)), 'rates': [96, 192],
              'severities': SEVERITIES, 'realizations': {'96': 8, '192': 1},
              'scalar_admission': admission, 'summaries': summaries, 'refinement': refinement,
              'files': files, 'seconds': time.monotonic() - began,
              'torch': torch.__version__, 'numpy': np.__version__, 'tf32': False,
              'scope': 'Finite numerical label identification under bounded independent pressure variation. All twelve pitch readouts, including inactive voices. No auditory, timing-noise, continuum, universal robustness or physical-memory capacity claim.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'finished': str(output), 'seconds': report['seconds'], 'refinement': refinement}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='artifacts/studies/pressure-study-001')
    parser.add_argument('--atlas', default='artifacts/studies/history-atlas-001')
    parser.add_argument('--batch-size', type=int, default=64, choices=range(1, 257))
    parser.add_argument('--check-only', action='store_true')
    main(parser.parse_args())
