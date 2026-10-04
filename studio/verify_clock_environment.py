"""Independently review the six saved cases with small 80-digit operators.

Run on the compute host. This verifier imports no generating project module.
It uses the exact stroboscopic four-group subspace and high-precision Hermitian
eigensolvers, rather than the generating record's binary64 full operators.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import mpmath as mp


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def outer(vector):
    return vector * vector.H


def distance(first, second):
    values = mp.eighe(first - second, eigvals_only=True)
    return sum(abs(value) for value in values) / 2


def partial_traces(joint):
    system = mp.matrix(4)
    environment = mp.matrix(2)
    for j in range(4):
        for k in range(4):
            system[j, k] = sum(joint[2*j+e, 2*k+e] for e in range(2))
    for e in range(2):
        for f in range(2):
            environment[e, f] = sum(joint[2*j+e, 2*j+f] for j in range(4))
    return system, environment


def main(args):
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    study = Path(args.study)
    report_path = study / 'report.json'
    recorded = json.loads(report_path.read_text())
    assert recorded['all_passed'] and recorded['cycles'] == [0, 1, 1250, 2500, 4109, 5000]
    assert recorded['chi'] == '1/10000' and recorded['group_A'] == [-3, -1, 1, 3]
    assert digest(study / 'record.npz') == recorded['record_sha256']
    review = {
        'method': 'Independent 80-digit four-group by two-state operators; no project generator imports',
        'scope': 'Exactly the six declared integer cycles and three declared preparations',
        'study_report_sha256': digest(report_path),
        'review_source_sha256': digest(__file__),
        'mpmath_version': mp.__version__, 'decimal_digits': 80,
        'comparisons': [], 'all_passed': False,
    }
    start = time.monotonic()
    try:
        with mp.workdps(80):
            offsets = [0, mp.sqrt(2), mp.sqrt(3), mp.sqrt(5)]
            coupling = list(map(mp.mpf, [-3, -1, 1, 3]))
            plus = mp.matrix([1, 1]) / mp.sqrt(2)
            environment_initials = {'plus': outer(plus), 'mixed': mp.eye(2)/2,
                                    'eigenstate': mp.matrix([[1, 0], [0, 0]])}
            system_initial = mp.ones(4) / 4
            for cycle in recorded['cycles']:
                instant = 2 * mp.pi * cycle
                phi = instant / 10000
                isolated_vector = mp.matrix([mp.exp(-mp.j*instant*b)/2 for b in offsets])
                isolated = outer(isolated_vector)
                gamma = sum(mp.exp(-2*mp.j*phi*a) for a in coupling) / 4
                for preparation, environment_initial in environment_initials.items():
                    initial = mp.matrix(8)
                    evolved = mp.matrix(8)
                    for j in range(4):
                        for k in range(4):
                            for e, sign_e in enumerate((1, -1)):
                                for f, sign_f in enumerate((1, -1)):
                                    initial[2*j+e, 2*k+f] = environment_initial[e, f] / 4
                                    gap = offsets[j]-offsets[k] + (coupling[j]*sign_e-coupling[k]*sign_f)/10000
                                    evolved[2*j+e, 2*k+f] = initial[2*j+e, 2*k+f] * mp.exp(-mp.j*instant*gap)
                    system, environment = partial_traces(evolved)
                    transposed = mp.matrix(8)
                    for j in range(4):
                        for k in range(4):
                            for e in range(2):
                                for f in range(2):
                                    transposed[2*j+e, 2*k+f] = evolved[2*j+f, 2*k+e]
                    negative = -sum(value for value in mp.eighe(transposed, eigvals_only=True) if value < 0)
                    clock_eigenvalues = mp.eighe(system, eigvals_only=True)
                    entropy = -sum(value*mp.log(value, 2) for value in clock_eigenvalues if value > mp.mpf('1e-60'))
                    values = {
                        'S': distance(system_initial, system),
                        'E': distance(environment_initial, environment),
                        'SE': distance(initial, evolved),
                        'negativity': negative,
                        'clock_entropy_bits': entropy,
                        'same_time_clock_disturbance': distance(system, isolated),
                    }
                    expected = recorded['cases'][f'n{cycle}_{preparation}']
                    saved = {key: expected['return'][key]['distance'] for key in ('S', 'E', 'SE')}
                    saved.update(negativity=expected['negativity'],
                                 clock_entropy_bits=expected['density']['S']['entropy_bits'],
                                 same_time_clock_disturbance=expected['same_time_clock_disturbance'])
                    errors = {key: abs(float(value)-saved[key]) for key, value in values.items()}
                    row = {'cycle': cycle, 'preparation': preparation,
                           'values_80_digits': {key: mp.nstr(value, 80) for key, value in values.items()},
                           'maximum_record_error': max(errors.values()),
                           'record_tolerance': 2e-12,
                           'passed': max(errors.values()) <= 2e-12}
                    if preparation == 'plus':
                        lam = [(1+abs(gamma))/2, (1-abs(gamma))/2]
                        predicted_entropy = -sum(x*mp.log(x, 2) for x in lam if x > mp.mpf('1e-60'))
                        formula_error = max(abs(entropy-predicted_entropy),
                                            abs(negative-mp.sqrt(lam[0]*lam[1])))
                        row['formula_error_80_digits'] = mp.nstr(formula_error, 80)
                        row['passed'] &= formula_error < mp.mpf('1e-60')
                    review['comparisons'].append(row)
            review['all_passed'] = len(review['comparisons']) == 18 and all(row['passed'] for row in review['comparisons'])
    except Exception as error:
        review['exception'] = {'type': type(error).__name__, 'message': str(error)}
    review['wall_seconds'] = time.monotonic()-start
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(review, indent=2)+'\n')
    print(json.dumps({'output': str(output), 'all_passed': review['all_passed'],
                      'comparisons': len(review['comparisons']),
                      'wall_seconds': review['wall_seconds']}), flush=True)
    if not review['all_passed']:
        raise RuntimeError('Independent environment review failed; its evidence is retained')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', default='artifacts/studies/clock-environment-001/run-001')
    parser.add_argument('--output', required=True)
    main(parser.parse_args())
