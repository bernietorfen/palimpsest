"""Independent saved-array and analytic-geometry checks of spatial refinement."""
import argparse
from datetime import datetime, timezone
from itertools import permutations
import json
import math
from pathlib import Path

import numpy as np
import torch

from studio.material import MaterialConfig, MODE_PAIRS, PalimpsestMaterial
from studio.preserve import sha256
from studio.spatial_study import register_echo


def distances(queries, references):
    query = queries.reshape(120, -1).astype(float)
    reference = references.reshape(120, -1).astype(float)
    result = np.empty((120, 120))
    for begin in range(0, 120, 8):
        delta = query[begin:begin + 8, None] - reference[None]
        result[begin:begin + 8] = np.sqrt(np.mean(delta * delta, axis=-1))
    return result


def geometry():
    result = []
    for size in (128, 256, 512):
        model = register_echo(PalimpsestMaterial(MaterialConfig(size=size, feedback=.08)))
        coord = torch.arange(size, dtype=torch.float64, device='cuda') * (2 * math.pi / size)
        y, x = torch.meshgrid(coord - 2 * math.pi * 18 / 128,
                              coord - 2 * math.pi * 11 / 128, indexing='ij')
        errors = {'echo_modes': 0., 'echo_quadratures': 0.}
        for index, (a, b) in enumerate(MODE_PAIRS):
            phase = index * math.pi * (3 - math.sqrt(5))
            # Directly evaluate the continuous trigonometric expressions at the
            # declared translated coordinates. No array rolls are used here.
            expected = {
                'echo_modes': (torch.cos(a * x + b * y + phase)
                               + .31 * torch.sin((a + 1) * x - (b + 1) * y - phase)
                               + .17 * torch.cos((b + 2) * x + (a + 1) * y + .7 * phase)),
                'echo_quadratures': (-torch.sin(a * x + b * y + phase)
                                     + .31 * torch.cos((a + 1) * x - (b + 1) * y - phase)
                                     - .17 * torch.sin((b + 2) * x + (a + 1) * y + .7 * phase)),
            }
            for name, values in expected.items():
                values -= values.mean()
                values /= values.square().mean().sqrt()
                error = float((values - getattr(model, name)[index].double()).abs().max())
                errors[name] = max(errors[name], error)
        if max(errors.values()) > 2e-5:
            raise ValueError(f'The registered geometry disagrees with its analytic placement: {errors}')
        result.append({'grid': size, 'analytic_double_vs_registered_float32_max_error': errors,
                       'declared_tolerance': 2e-5})
    return result


def main(args):
    torch.set_num_threads(2)
    root, original = Path(args.study), Path(args.atlas)
    report = json.loads((root / 'report.json').read_text())
    for item in report['files']:
        path = root / item['path']
        if path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
            raise ValueError(f"Changed study record: {item['path']}")
    if sha256(Path('studio/spatial_study.py')) != report['source_sha256']['studio/spatial_study.py']:
        raise ValueError('The registered geometry implementation differs from generation')
    analytic = geometry()
    labels = [''.join(order) for order in permutations('ABCDE')]
    arrays, pairwise_reports = {}, []
    maximum_error = 0.
    for size in (128, 256, 512):
        for rate in (96, 192):
            folder = root / f'grid-{size}' / f'rate-{rate}'
            with np.load(folder / 'atlas.npz') as data:
                values = data['pitch_hz'].copy()
                if data['labels'].tolist() != labels or values.shape != (120, 336, 12) or not np.isfinite(values).all():
                    raise ValueError('Incomplete, misordered or non-finite atlas')
            records, batch_labels = [], []
            for path in sorted(folder.glob('batch-*.npz')):
                with np.load(path) as batch:
                    records.append(batch['pitch_hz'])
                    batch_labels.extend(batch['labels'].tolist())
            if batch_labels != labels or not np.array_equal(np.concatenate(records), values):
                raise ValueError('Batch checkpoints differ from the combined atlas')
            arrays[(size, rate)] = values
            matrix = distances(values, values)
            error = float(np.abs(matrix - np.load(folder / 'pairwise-rms-hz.npy')).max())
            maximum_error = max(maximum_error, error)
            upper = matrix[np.triu_indices(120, 1)]
            expected = report['summaries'][f'{size}/{rate}']['pairwise']
            if int(np.count_nonzero(upper > 1e-6)) != expected['above_1e_minus_6_hz']:
                raise ValueError('The pairwise separation count differs')
            pairwise_reports.append({'grid': size, 'rate': rate, 'pairs': len(upper),
                                     'above_1e_minus_6_hz': int(np.count_nonzero(upper > 1e-6)),
                                     'minimum_hz': float(upper.min()), 'maximum_distance_error_hz': error})
            for label in ('ABCDE', 'DEABC'):
                with np.load(folder / f'writing-{label}.npz') as field:
                    if str(field['label']) != label:
                        raise ValueError('A retained field was mislabelled')
                    for name, lower, higher in (('inscription', -.8, .8), ('fatigue', 0, 1)):
                        actual = field[name]
                        if actual.shape != (size, size) or not np.isfinite(actual).all() or actual.min() < lower - 1e-7 or actual.max() > higher + 1e-7:
                            raise ValueError('A retained field is invalid')
            if size == 128:
                path = original / f'rate-{rate}/atlas.npz'
                if sha256(path) != report['original_atlas_sha256'][str(rate)]:
                    raise ValueError('The original reference changed')
                with np.load(path) as data:
                    matrix = distances(values, data['pitch_hz'])
                with np.load(folder / 'original-atlas.npz') as saved:
                    maximum_error = max(maximum_error, float(np.abs(matrix - saved['distances_hz']).max()))
                    if not np.array_equal(matrix.argmin(axis=1), np.arange(120)) or np.diag(matrix).max() > .001:
                        raise ValueError('Original-atlas admission failed independently')
    comparisons = []
    for key, expected in report['comparisons'].items():
        parts = key.split('-')
        if parts[0] == 'grid':
            coarse_grid, fine_grid, rate = int(parts[1]), int(parts[2]), int(parts[4])
            coarse_key, fine_key = (coarse_grid, rate), (fine_grid, rate)
        else:
            coarse_key, fine_key = (int(parts[2]), 96), (int(parts[2]), 192)
        matrix = distances(arrays[fine_key], arrays[coarse_key])
        predicted = matrix.argmin(axis=1)
        own = np.diag(matrix).copy()
        other = matrix.copy(); np.fill_diagonal(other, np.inf)
        margins = other.min(axis=1) - own
        with np.load(root / 'comparisons' / f'{key}.npz') as saved:
            error = float(np.abs(matrix - saved['distances_hz']).max())
            maximum_error = max(maximum_error, error)
            if not np.array_equal(saved['predicted'], predicted):
                raise ValueError(f'Predictions differ for {key}')
            if np.max(np.abs(saved['margin_hz'] - margins)) > 2e-12:
                raise ValueError(f'Margins differ for {key}')
        correct = int(np.count_nonzero(predicted == np.arange(120)))
        if correct != expected['correct_nearest_history']:
            raise ValueError(f'Correct count differs for {key}')
        coarse_folder = root / f'grid-{coarse_key[0]}' / f'rate-{coarse_key[1]}'
        fine_folder = root / f'grid-{fine_key[0]}' / f'rate-{fine_key[1]}'
        for label in ('ABCDE', 'DEABC'):
            with np.load(coarse_folder / f'writing-{label}.npz') as coarse, np.load(fine_folder / f'writing-{label}.npz') as fine:
                # Explicit coincident coordinate indexing, independently of the
                # generation-side stride slice.
                indexes = np.arange(coarse_key[0]) * (fine_key[0] // coarse_key[0])
                for name in ('inscription', 'fatigue'):
                    delta = fine[name][np.ix_(indexes, indexes)].astype(float) - coarse[name].astype(float)
                    observed = {'rms': float(np.linalg.norm(delta) / math.sqrt(delta.size)),
                                'max_absolute': float(np.max(np.abs(delta)))}
                    saved = expected['coincident_retained_fields'][label][name]
                    if any(abs(observed[k] - saved[k]) > 1e-12 for k in observed):
                        raise ValueError('The retained-field comparison differs')
        comparisons.append({'comparison': key, 'correct': correct, 'tested': 120,
                            'maximum_own_distance_hz': float(own.max()),
                            'maximum_distance_error_hz': error})
    if maximum_error > 2e-12:
        raise ValueError('Independent RMS distances disagree')
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    result = {'verified_utc': datetime.now(timezone.utc).isoformat(), 'study_report_sha256': sha256(root / 'report.json'),
              'files_verified': len(report['files']), 'analytic_registered_geometry': analytic,
              'full_pairwise_and_cross_matrices_recomputed': True, 'all_batch_checkpoints_match_combined_records': True,
              'all_selected_retained_fields_verified': True, 'maximum_distance_error_hz': maximum_error,
              'pairwise': pairwise_reports, 'comparisons': comparisons}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', default='artifacts/studies/spatial-study-001')
    parser.add_argument('--atlas', default='artifacts/studies/history-atlas-001')
    parser.add_argument('--output', default='research/spatial-verification-001.json')
    main(parser.parse_args())
