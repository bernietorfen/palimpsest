"""Independently reopen and verify the completed pressure study on RunPod."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np

from studio.preserve import sha256


def main(args):
    root, atlas = Path(args.study), Path(args.atlas)
    report = json.loads((root / 'report.json').read_text())
    for item in report['files']:
        path = root / item['path']
        if path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
            raise ValueError(f"Changed scientific record: {item['path']}")
    expected_errors = np.random.Generator(np.random.PCG64(2026100403)).uniform(-1, 1, (120, 8, 5))
    if not np.array_equal(np.load(root / 'pressure-errors.npy'), expected_errors):
        raise ValueError('Pressure realizations differ from the declared seed')
    summaries, labels, maximum_distance_error = [], None, 0.
    for rate, count in ((96, 8), (192, 1)):
        original = np.load(atlas / f'rate-{rate}' / 'atlas.npz')
        labels = original['labels'].tolist()
        reference = original['pitch_hz'].reshape(120, -1).astype(np.float64)
        for severity in (.01, .03, .10):
            folder = root / f'rate-{rate}' / f'pressure-{round(severity * 100):02d}'
            expected_truth = np.repeat(np.arange(120), count)
            expected_trial = np.tile(np.arange(count), 120)
            expected_factors = (1 + severity * expected_errors[:, :count]).astype(np.float32).reshape(-1, 5)
            records, actual_labels, factors, trials = [], [], [], []
            for path in sorted(folder.glob('batch-*.npz')):
                with np.load(path) as data:
                    if data['pitch_hz'].shape[1:] != (336, 12) or not np.isfinite(data['pitch_hz']).all():
                        raise ValueError('Wrong shape or non-finite saved readout')
                    records.append(data['pitch_hz'])
                    actual_labels.extend(data['labels'].tolist())
                    factors.append(data['pressure_factors'])
                    trials.append(data['realization'])
            if actual_labels != [labels[i] for i in expected_truth]:
                raise ValueError('A history is missing, duplicated or mislabelled')
            if not np.array_equal(np.concatenate(factors), expected_factors) or not np.array_equal(np.concatenate(trials), expected_trial):
                raise ValueError('Recorded pressures or realization indexes differ')
            queries = np.concatenate(records).reshape(len(expected_truth), -1).astype(np.float64)
            # Explicit subtraction and averaging are independent of the study's
            # SciPy cdist implementation. Work in bounded blocks on RunPod.
            distances = np.empty((len(queries), 120), np.float64)
            for begin in range(0, len(queries), 8):
                delta = queries[begin:begin + 8, None] - reference[None]
                distances[begin:begin + 8] = np.sqrt(np.mean(delta * delta, axis=-1))
            predicted = distances.argmin(axis=1)
            with np.load(folder / 'identification.npz') as saved:
                if not np.array_equal(saved['truth'], expected_truth) or not np.array_equal(saved['predicted'], predicted):
                    raise ValueError('Recomputed history identities differ')
                error = float(np.abs(saved['correct_distance_hz'] - distances[np.arange(len(queries)), expected_truth]).max())
                maximum_distance_error = max(maximum_distance_error, error)
            confusion = np.zeros((120, 120), int)
            np.add.at(confusion, (expected_truth, predicted), 1)
            summary = json.loads((folder / 'report.json').read_text())
            if not np.array_equal(confusion, np.asarray(summary['confusion'])) or int(np.trace(confusion)) != summary['correct']:
                raise ValueError('Saved confusion matrix or count differs')
            summaries.append({'rate': rate, 'severity': severity, 'correct': int(np.trace(confusion)),
                              'tested': len(queries), 'independent_rms_max_difference_hz': error})
    if maximum_distance_error > 2e-12:
        raise ValueError('Independent RMS calculation disagrees with the saved distances')
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    verified = {'verified_utc': datetime.now(timezone.utc).isoformat(), 'study_report_sha256': sha256(root / 'report.json'),
                'files_verified': len(report['files']), 'exact_seed_and_pressure_factors': True,
                'all_case_labels_and_realizations_verified': True, 'all_predictions_and_confusions_recomputed': True,
                'independent_rms_max_difference_hz': maximum_distance_error, 'cases': summaries}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(verified, indent=2) + '\n')
    print(json.dumps(verified, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', default='artifacts/studies/pressure-study-001')
    parser.add_argument('--atlas', default='artifacts/studies/history-atlas-001')
    parser.add_argument('--output', default='research/pressure-verification-001.json')
    main(parser.parse_args())
