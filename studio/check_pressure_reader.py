"""Check the reader's algebra against direct least squares on RunPod."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.linalg import lstsq

from studio.pressure_reading import DIMENSION, RCOND, corrected_reading, fit_reader
from studio.preserve import sha256


def main(args):
    rng = np.random.Generator(np.random.PCG64(9017))
    jacobians = np.empty((120, DIMENSION, 5))
    for history in range(120):
        q, _ = np.linalg.qr(rng.normal(size=(DIMENSION, 5)))
        values = [3, 1, 0, 0, 0] if history < 2 else [3, 1, .5, .1, .02]
        jacobians[history] = q * np.array(values)[None]
    reader = fit_reader(jacobians)
    assert reader['ranks'].tolist() == [2, 2] + [5] * 118
    canonical = 200 + rng.normal(0, 2, size=(120, 336, 12))
    truth = np.array([0, 1, 37, 63, 119])
    adjustments = rng.uniform(-.1, .1, (len(truth), 5))
    adjustments[:2, 2:] = 0
    centers = canonical.reshape(120, DIMENSION) / math.sqrt(DIMENSION)
    queries = np.stack([centers[h] + jacobians[h] @ adjustments[i] for i, h in enumerate(truth)])
    predicted, residuals, estimated = corrected_reading(queries.reshape(-1, 336, 12) * math.sqrt(DIMENSION), canonical, reader)
    assert np.array_equal(predicted, truth)
    assert np.max(np.abs(estimated - adjustments)) < 1e-10
    direct = np.empty_like(residuals)
    for history in range(120):
        difference = (queries - centers[history]).T
        coefficients = lstsq(jacobians[history], difference, cond=RCOND, lapack_driver='gelsd')[0]
        direct[:, history] = np.linalg.norm(difference - jacobians[history] @ coefficients, axis=0)
    error = float(np.abs(direct - residuals).max())
    if error > 2e-7:
        raise ValueError('Projection residuals disagree with direct least squares')
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    result = {'source_sha256': sha256(Path('studio/pressure_reading.py')),
              'synthetic_queries': len(truth), 'candidate_histories_per_query': 120,
              'rank_deficient_and_full_rank_cases': True, 'expected_labels_exact': True,
              'injected_pressure_adjustments_recovered_max_error': float(np.abs(estimated - adjustments).max()),
              'direct_least_squares_max_residual_difference_hz': error,
              'scope': 'Algebra check on constructed affine responses; not evidence about the real material or evaluation accuracy.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='research/pressure-reader-algebra-001.json')
    main(parser.parse_args())
