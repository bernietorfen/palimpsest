"""Reconstruct the saved reading experiment through direct least squares."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path

import numpy as np
from scipy.linalg import lstsq

from studio.preserve import sha256


def require_equal(actual, expected, name):
    if not np.array_equal(actual, expected):
        raise ValueError(f'Independent verification failed: {name}')


def main(args):
    root, atlas = Path(args.study), Path(args.atlas)
    report = json.loads((root / 'report.json').read_text())
    for item in report['files']:
        path = root / item['path']
        if path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
            raise ValueError(f"Changed scientific record: {item['path']}")
    errors = np.random.Generator(np.random.PCG64(2026100404)).uniform(-1, 1, (120, 8, 5))
    require_equal(np.load(root / 'evaluation-errors.npy'), errors, 'declared evaluation seed')
    summaries, predictions = [], {}
    for rate, count in ((96, 8), (192, 1)):
        directory = root / f'rate-{rate}'
        with np.load(atlas / f'rate-{rate}' / 'atlas.npz') as original:
            labels = original['labels'].tolist()
            canonical = original['pitch_hz'].astype(np.float32).reshape(120, -1).astype(float)
        dimension = canonical.shape[1]
        reference = canonical / math.sqrt(dimension)
        saved_reader = np.load(directory / 'reader.npz')
        derivatives, metadata = [], {key: [] for key in ('history', 'position', 'sign', 'pressure_factors')}
        for path in sorted((directory / 'derivatives').glob('batch-*.npz')):
            with np.load(path) as batch:
                derivatives.append(batch['pitch_hz'])
                for key in metadata:
                    metadata[key].append(batch[key])
        metadata = {key: np.concatenate(values) for key, values in metadata.items()}
        require_equal(metadata['history'], np.repeat(np.arange(120), 10), 'derivative histories')
        require_equal(metadata['position'], np.tile(np.repeat(np.arange(5), 2), 120), 'derivative positions')
        require_equal(metadata['sign'], np.tile([-1, 1], 600), 'derivative signs')
        expected_factors = np.ones((1200, 5), np.float32)
        expected_factors[np.arange(1200), metadata['position']] += (.002 * metadata['sign']).astype(np.float32)
        require_equal(metadata['pressure_factors'], expected_factors, 'derivative pressures')
        values = np.concatenate(derivatives).reshape(120, 5, 2, dimension).astype(float)
        separation = float(np.float32(1.002)) - float(np.float32(.998))
        jacobians = np.stack([(values[:, position, 1] - values[:, position, 0]) /
                              (separation * math.sqrt(dimension)) for position in range(5)], axis=-1)
        require_equal(jacobians, saved_reader['jacobians'], 'derivatives reconstructed from measurements')
        del values, derivatives
        for severity in (.01, .03, .10):
            folder = directory / f'pressure-{round(severity * 100):02d}'
            truth, trials = np.repeat(np.arange(120), count), np.tile(np.arange(count), 120)
            factors = (1 + severity * errors[:, :count]).astype(np.float32).reshape(-1, 5)
            records, written_labels, recorded_factors, recorded_trials = [], [], [], []
            for path in sorted(folder.glob('batch-*.npz')):
                with np.load(path) as batch:
                    records.append(batch['pitch_hz'])
                    written_labels.extend(batch['labels'].tolist())
                    recorded_factors.append(batch['pressure_factors'])
                    recorded_trials.append(batch['realization'])
            require_equal(written_labels, [labels[i] for i in truth], 'evaluation labels')
            require_equal(np.concatenate(recorded_factors), factors, 'evaluation pressures')
            require_equal(np.concatenate(recorded_trials), trials, 'evaluation trial order')
            queries = np.concatenate(records).reshape(len(truth), dimension).astype(float) / math.sqrt(dimension)
            if not np.isfinite(queries).all():
                raise ValueError('Non-finite measured trajectory')
            saved = np.load(folder / 'identification.npz')
            require_equal(saved['truth'], truth, 'saved truth')
            require_equal(saved['realization'], trials, 'saved trials')
            require_equal(saved['pressure_factors'], factors, 'saved pressures')
            raw, residuals = np.empty((len(truth), 120)), np.empty((len(truth), 120))
            winning = np.empty((len(truth), 5))
            ranks = []
            # Each solve reconstructs the whole residual vector. It does not
            # use the saved basis or subtract two nearly equal squared norms.
            for candidate in range(120):
                delta = (queries - reference[candidate]).T
                coefficients, _, rank, _ = lstsq(jacobians[candidate], delta, cond=1e-6,
                                                 lapack_driver='gelsd', check_finite=True)
                remainder = delta - jacobians[candidate] @ coefficients
                residuals[:, candidate] = np.linalg.norm(remainder, axis=0)
                raw[:, candidate] = np.linalg.norm(delta, axis=0)
                chosen = saved['corrected_predicted'] == candidate
                winning[chosen] = coefficients[:, chosen].T
                ranks.append(rank)
            require_equal(ranks, saved_reader['ranks'], 'independent numerical ranks')
            nearest, corrected = raw.argmin(axis=1), residuals.argmin(axis=1)
            require_equal(nearest, saved['baseline_predicted'], 'nearest predictions')
            require_equal(corrected, saved['corrected_predicted'], 'pressure-aware predictions')
            difference = float(np.abs(residuals - saved['all_corrected_residuals_hz']).max())
            adjustment_error = float(np.abs(winning - saved['winning_pressure_adjustments']).max())
            baseline_error = float(np.abs(raw[np.arange(len(truth)), truth] - saved['baseline_correct_distance_hz']).max())
            if difference > 2e-7 or adjustment_error > 1e-7 or baseline_error > 2e-12:
                raise ValueError(f'Recomputed numeric values disagree: {difference}, {adjustment_error}, {baseline_error}')
            for method, predicted in (('nearest_canonical', nearest), ('pressure_corrected', corrected)):
                confusion = np.zeros((120, 120), int)
                np.add.at(confusion, (truth, predicted), 1)
                summary = report['summaries'][str(rate)]['pressures'][str(severity)][method]
                require_equal(confusion, summary['confusion'], f'{method} confusion matrix')
                require_equal(np.trace(confusion), summary['correct'], f'{method} correct count')
            predictions[(rate, severity)] = (nearest.reshape(120, count), corrected.reshape(120, count))
            result = {'rate': rate, 'severity': severity, 'tested': len(truth),
                      'nearest_correct': int(np.count_nonzero(nearest == truth)),
                      'pressure_corrected': int(np.count_nonzero(corrected == truth)),
                      'full_residual_matrix_max_error_hz': difference,
                      'winning_adjustment_max_error': adjustment_error,
                      'baseline_distance_max_error_hz': baseline_error}
            summaries.append(result)
            print(json.dumps(result), flush=True)
    for severity in (.01, .03, .10):
        for index, method in enumerate(('nearest', 'corrected')):
            coarse = predictions[(96, severity)][index][:, 0]
            fine = predictions[(192, severity)][index][:, 0]
            values = {'same_predicted_label': int(np.count_nonzero(coarse == fine)), 'tested': 120,
                      'coarse_correct': int(np.count_nonzero(coarse == np.arange(120))),
                      'fine_correct': int(np.count_nonzero(fine == np.arange(120)))}
            if values != report['refinement'][str(severity)][method]:
                raise ValueError('Refinement summary disagrees with reconstructed predictions')
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    verified = {'verified_utc': datetime.now(timezone.utc).isoformat(),
                'study_report_sha256': sha256(root / 'report.json'), 'files_verified': len(report['files']),
                'exact_seed_factors_labels_and_derivatives': True,
                'all_residuals_reconstructed_with_direct_least_squares': True,
                'all_predictions_confusions_and_refinement_verified': True, 'cases': summaries}
    output.write_text(json.dumps(verified, indent=2) + '\n')
    print(json.dumps({'verified': str(output)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', default='artifacts/studies/pressure-reading-001')
    parser.add_argument('--atlas', default='artifacts/studies/history-atlas-001')
    parser.add_argument('--output', default='research/pressure-reading-verification-001.json')
    main(parser.parse_args())
