"""A declared local-linear pressure correction, evaluated on fresh histories."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import time

import numpy as np
from scipy.spatial.distance import cdist
import torch

from studio.material import MaterialConfig
from studio.preserve import sha256
from studio.pressure_study import LABELS, ORDERS, SEVERITIES, SOURCE_FILES, identify, run_batch


SEED = 2026100404
EPSILON = .002
RCOND = 1e-6
DIMENSION = 336 * 12


def derivatives(directory, config, batch_size, began):
    histories = np.repeat(np.arange(120), 10)
    positions = np.tile(np.repeat(np.arange(5), 2), 120)
    signs = np.tile([-1, 1], 120 * 5)
    factors = np.ones((1200, 5), np.float32)
    factors[np.arange(1200), positions] += (EPSILON * signs).astype(np.float32)
    records = []
    folder = directory / 'derivatives'
    folder.mkdir()
    for begin in range(0, 1200, batch_size):
        stop = min(1200, begin + batch_size)
        pitches, retained = run_batch([ORDERS[i] for i in histories[begin:stop]], factors[begin:stop], config)
        records.append(pitches)
        np.savez_compressed(folder / f'batch-{begin:04d}.npz',
                            history=histories[begin:stop], position=positions[begin:stop], sign=signs[begin:stop],
                            pressure_factors=factors[begin:stop], pitch_hz=pitches, **retained)
        print(json.dumps({'rate': round(1 / config.dt), 'derivatives_completed': stop,
                          'of': 1200, 'seconds': time.monotonic() - began}), flush=True)
    values = np.concatenate(records).astype(np.float64).reshape(120, 5, 2, DIMENSION)
    # Use the actual stored float32 multiplier separation, including rounding.
    separation = float(np.float32(1 + EPSILON)) - float(np.float32(1 - EPSILON))
    jacobians = np.transpose((values[:, :, 1] - values[:, :, 0]) / (separation * math.sqrt(DIMENSION)), (0, 2, 1))
    reader = fit_reader(jacobians)
    path = directory / 'reader.npz'
    np.savez_compressed(path, **reader, actual_multiplier_separation=separation)
    return reader


def fit_reader(jacobians):
    if jacobians.shape != (120, DIMENSION, 5) or not np.isfinite(jacobians).all():
        raise ValueError('Expected five finite response directions for every history')
    basis = np.zeros((120, DIMENSION, 5), np.float64)
    singular_values = np.zeros((120, 5), np.float64)
    right_vectors = np.zeros((120, 5, 5), np.float64)
    ranks = np.zeros(120, np.int32)
    for history in range(120):
        u, s, vh = np.linalg.svd(jacobians[history], full_matrices=False)
        keep = s > s[0] * RCOND
        basis[history][:, keep] = u[:, keep]
        singular_values[history] = s
        right_vectors[history] = vh
        ranks[history] = int(np.count_nonzero(keep))
    return {'jacobians': jacobians, 'basis': basis, 'singular_values': singular_values,
            'right_vectors': right_vectors, 'ranks': ranks}


def corrected_reading(pitches, canonical, reader):
    """No history labels, pressure factors, severities or outcomes are inputs."""
    queries = pitches.reshape(len(pitches), DIMENSION).astype(np.float64) / math.sqrt(DIMENSION)
    centers = canonical.reshape(120, DIMENSION).astype(np.float64) / math.sqrt(DIMENSION)
    bases = reader['basis']
    raw = cdist(queries, centers)
    coordinates = (queries @ bases.transpose(1, 0, 2).reshape(DIMENSION, 600)).reshape(len(queries), 120, 5)
    coordinates -= np.einsum('hd,hdk->hk', centers, bases)[None]
    squared = raw * raw - np.sum(coordinates * coordinates, axis=-1)
    if not np.isfinite(squared).all() or squared.min() < -1e-10:
        raise ValueError('The pressure projection produced an invalid residual')
    residuals = np.sqrt(np.maximum(squared, 0))
    predicted = residuals.argmin(axis=1)
    winning_adjustments = np.zeros((len(queries), 5), np.float64)
    for index, history in enumerate(predicted):
        s = reader['singular_values'][history]
        keep = s > s[0] * RCOND
        coefficients = np.zeros(5)
        coefficients[keep] = coordinates[index, history, keep] / s[keep]
        winning_adjustments[index] = reader['right_vectors'][history].T @ coefficients
    return predicted, residuals, winning_adjustments


def corrected_summary(truth, predicted, residuals, adjustments):
    own = residuals[np.arange(len(truth)), truth].copy()
    other_values = residuals.copy()
    other_values[np.arange(len(truth)), truth] = np.inf
    other = other_values.min(axis=1)
    margin = other - own
    confusion = np.zeros((120, 120), np.int32)
    np.add.at(confusion, (truth, predicted), 1)
    return {'tested': len(truth), 'correct': int(np.count_nonzero(predicted == truth)),
            'fraction_correct': float(np.mean(predicted == truth)),
            'minimum_margin_hz': float(margin.min()), 'median_margin_hz': float(np.median(margin)),
            'median_correct_history_residual_hz': float(np.median(own)),
            'maximum_correct_history_residual_hz': float(own.max()),
            'winning_adjustments_outside_10_percent': int(np.count_nonzero(np.abs(adjustments).max(axis=1) > .1)),
            'confusion': confusion.tolist(),
            'per_history': [{'history': label, 'correct': int(confusion[i, i]), 'tested': int(confusion[i].sum())}
                            for i, label in enumerate(LABELS)]}, own, other, margin


def main(args):
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision('highest')
    algebra = json.loads(Path(args.algebra_report).read_text())
    if algebra['source_sha256'] != sha256(Path('studio/pressure_reading.py')) or not algebra['expected_labels_exact']:
        raise ValueError('Run the algebra check for this exact reader implementation first')
    previous = Path(args.admitted_study)
    admitted = json.loads((previous / 'report.json').read_text())
    if not admitted['scalar_admission']['admitted'] or not all(s['canonical']['admitted'] for s in admitted['summaries'].values()):
        raise ValueError('The upstream batch implementation is not admitted')
    for relative, digest in admitted['source_sha256'].items():
        if sha256(Path(relative)) != digest:
            raise ValueError(f'The admitted implementation changed: {relative}')
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for relative in SOURCE_FILES + ['studio/pressure_reading.py', 'studio/check_pressure_reader.py',
                                  'research/PRESSURE-READING.md', args.algebra_report]:
        path = Path(relative)
        target = output / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        hashes[relative] = sha256(path)
    began = time.monotonic()
    errors = np.random.Generator(np.random.PCG64(SEED)).uniform(-1, 1, (120, 8, 5))
    np.save(output / 'evaluation-errors.npy', errors)
    reports, predictions = {}, {}
    for rate in (96, 192):
        config = MaterialConfig(dt=1 / rate, feedback=.08)
        directory = output / f'rate-{rate}'
        directory.mkdir()
        original = np.load(Path(args.atlas) / f'rate-{rate}' / 'atlas.npz')
        if original['labels'].tolist() != LABELS:
            raise ValueError('Canonical history order changed')
        canonical = original['pitch_hz'].astype(np.float32)
        reader = derivatives(directory, config, args.batch_size, began)
        nominal, _, _ = corrected_reading(canonical, canonical, reader)
        if not np.array_equal(nominal, np.arange(120)):
            raise ValueError('The corrected reader does not identify its canonical histories')
        count = 8 if rate == 96 else 1
        reports[str(rate)] = {'canonical_correct': 120, 'derivative_ranks': reader['ranks'].tolist(),
                              'minimum_singular_value': float(reader['singular_values'].min()),
                              'maximum_singular_value': float(reader['singular_values'].max()), 'pressures': {}}
        for severity in SEVERITIES:
            folder = directory / f'pressure-{round(severity * 100):02d}'
            folder.mkdir()
            factors = (1 + severity * errors[:, :count]).astype(np.float32).reshape(-1, 5)
            truth = np.repeat(np.arange(120), count)
            realizations = np.tile(np.arange(count), 120)
            records = []
            for begin in range(0, len(truth), args.batch_size):
                stop = min(len(truth), begin + args.batch_size)
                pitches, retained = run_batch([ORDERS[i] for i in truth[begin:stop]], factors[begin:stop], config)
                records.append(pitches)
                np.savez_compressed(folder / f'batch-{begin:04d}.npz',
                                    labels=np.array([LABELS[i] for i in truth[begin:stop]]),
                                    realization=realizations[begin:stop], pressure_factors=factors[begin:stop],
                                    pitch_hz=pitches, **retained)
                print(json.dumps({'rate': rate, 'severity': severity, 'evaluation_completed': stop,
                                  'of': len(truth), 'seconds': time.monotonic() - began}), flush=True)
            pitches = np.concatenate(records)
            baseline, baseline_detail = identify(pitches, truth, canonical)
            predicted, residuals, adjustments = corrected_reading(pitches, canonical, reader)
            corrected, own, other, margins = corrected_summary(truth, predicted, residuals, adjustments)
            report = {'nearest_canonical': baseline, 'pressure_corrected': corrected}
            (folder / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
            np.savez_compressed(folder / 'identification.npz', truth=truth, realization=realizations,
                                pressure_factors=factors, baseline_predicted=baseline_detail['predicted'],
                                baseline_correct_distance_hz=baseline_detail['correct_distance_hz'],
                                corrected_predicted=predicted, all_corrected_residuals_hz=residuals,
                                correct_residual_hz=own, other_residual_hz=other, margin_hz=margins,
                                winning_pressure_adjustments=adjustments)
            reports[str(rate)]['pressures'][str(severity)] = report
            predictions[(rate, severity)] = {'nearest': baseline_detail['predicted'].reshape(120, count),
                                             'corrected': predicted.reshape(120, count)}
            print(json.dumps({'rate': rate, 'severity': severity, 'nearest_correct': baseline['correct'],
                              'corrected_correct': corrected['correct'], 'tested': len(truth)}), flush=True)
    refinement = {}
    for severity in SEVERITIES:
        refinement[str(severity)] = {}
        for method in ('nearest', 'corrected'):
            coarse, fine = predictions[(96, severity)][method][:, 0], predictions[(192, severity)][method][:, 0]
            refinement[str(severity)][method] = {'same_predicted_label': int(np.count_nonzero(coarse == fine)),
                                                 'tested': 120, 'coarse_correct': int(np.count_nonzero(coarse == np.arange(120))),
                                                 'fine_correct': int(np.count_nonzero(fine == np.arange(120)))}
    files = [{'path': str(path.relative_to(output)), 'bytes': path.stat().st_size, 'sha256': sha256(path)}
             for path in sorted(output.rglob('*')) if path.is_file()]
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': hashes,
              'algebra_check': algebra,
              'admitted_study_sha256': sha256(previous / 'report.json'), 'seed': SEED,
              'nominal_derivative_offset': EPSILON, 'relative_singular_cutoff': RCOND,
              'severity_is_not_a_reader_input': True, 'rates': [96, 192], 'realizations': {'96': 8, '192': 1},
              'summaries': reports, 'refinement': refinement, 'files': files, 'seconds': time.monotonic() - began,
              'scope': 'New-seed numerical evaluation of a fixed local linear nuisance-response correction. Established linear algebra applied to this authored instrument. No auditory, physical-capacity, global-invertibility or timing-noise claim.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'finished': str(output), 'seconds': report['seconds'], 'refinement': refinement}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='artifacts/studies/pressure-reading-001')
    parser.add_argument('--admitted-study', default='artifacts/studies/pressure-study-001')
    parser.add_argument('--atlas', default='artifacts/studies/history-atlas-001')
    parser.add_argument('--algebra-report', default='research/pressure-reader-algebra-001.json')
    parser.add_argument('--batch-size', type=int, default=64, choices=range(1, 257))
    main(parser.parse_args())
