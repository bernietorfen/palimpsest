"""Two known snapshot preparations: hidden relations and a certified near return.

Execute on the remote computation host. The restricted algebra represents
available measurements, not physical decoherence. Single-copy discrimination
is separate from the earlier ensemble expectation-value experiments.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import resource
import shutil
import signal
import sys
import time

import mpmath as mp
import numpy as np
from threadpoolctl import threadpool_limits

from studio.relational_clock import array_digest, fourier_basis, sha256_file


Q = 128
RADICANDS = (2, 3, 5)
SEARCH_SECONDS = 120.
TOTAL_SECONDS = 300.
MAX_MEMORY_BYTES = 256 * 1024 ** 2
MAX_RECORD_BYTES = 1024 ** 2
PRECISION = 80
TOLERANCE = 2e-12


class SearchLimit(RuntimeError):
    def __init__(self, candidate_count, elapsed):
        self.candidate_count = candidate_count
        self.elapsed = elapsed
        super().__init__(f'Search limit reached after {candidate_count} candidates')


def integer_box(k, q):
    """Exactly floor(q * frac(k sqrt(s))) for each declared radicand."""
    if type(k) is not int or k < 0 or type(q) is not int or q < 2:
        raise ValueError('Nonnegative integer index and integer q >= 2 required')
    return tuple(math.isqrt(s * (q * k) ** 2) - q * math.isqrt(s * k * k)
                 for s in RADICANDS)


def collision_certificate(k, l, q):
    roots = []
    for index in (k, l):
        for s in RADICANDS:
            roots.append({'index': index, 'radicand': s,
                          'f': math.isqrt(s * index * index),
                          'h': math.isqrt(s * (q * index) ** 2)})
    return {'q': q, 'k': k, 'l': l, 'n': k - l, 'roots': roots,
            'box_k': list(integer_box(k, q)), 'box_l': list(integer_box(l, q)),
            'm': [math.isqrt(s * k * k) - math.isqrt(s * l * l) for s in RADICANDS]}


def verify_certificate(witness):
    """Check only supplied integers and squared enclosures, without square roots."""
    try:
        q, k, l, n = (witness[key] for key in ('q', 'k', 'l', 'n'))
        if any(type(value) is not int for value in (q, k, l, n)):
            return False
        if not (q >= 2 and 0 <= l < k <= q ** 3 and n == k - l):
            return False
        supplied = witness['roots']
        if len(supplied) != 6:
            return False
        lookup = {}
        for row in supplied:
            index, s, f, h = (row[key] for key in ('index', 'radicand', 'f', 'h'))
            if any(type(value) is not int for value in (index, s, f, h)):
                return False
            if (index not in (k, l) or s not in RADICANDS or f < 0 or h < 0
                    or (index, s) in lookup):
                return False
            if not (f * f <= s * index * index < (f + 1) ** 2):
                return False
            if not (h * h <= s * (q * index) ** 2 < (h + 1) ** 2):
                return False
            lookup[index, s] = (f, h)
        boxes = {index: [lookup[index, s][1] - q * lookup[index, s][0]
                         for s in RADICANDS] for index in (k, l)}
        if any(not 0 <= coordinate < q for box in boxes.values() for coordinate in box):
            return False
        if not (boxes[k] == boxes[l] == witness['box_k'] == witness['box_l']):
            return False
        return witness['m'] == [lookup[k, s][0] - lookup[l, s][0] for s in RADICANDS]
    except (KeyError, TypeError, ValueError):
        return False


def first_collision(q=Q, seconds=SEARCH_SECONDS, clock=time.monotonic):
    """A fixed finite pigeonhole construction; no floating-point phases."""
    if type(q) is not int or not 2 <= q <= Q:
        raise ValueError('This scoped implementation permits integer 2 <= q <= 128')
    began = clock()
    seen = np.full(q ** 3, -1, dtype=np.int32)
    for k in range(q ** 3 + 1):
        if k % 1024 == 0 and clock() - began >= seconds:
            raise SearchLimit(k, clock() - began)
        a, b, c = integer_box(k, q)
        address = (a * q + b) * q + c
        l = int(seen[address])
        if l >= 0:
            witness = collision_certificate(k, l, q)
            witness['candidate_count'] = k + 1
            witness['search_wall_seconds'] = clock() - began
            witness['search_table_bytes'] = seen.nbytes
            return witness
        seen[address] = k
    raise AssertionError('No collision contradicts the finite pigeonhole count')


def high_precision_stroboscopic(n, integers=None):
    """Original 32-mode evolution checked against separately reduced group phases."""
    if integers is None:
        integers = [math.isqrt(s * n * n) for s in RADICANDS]
    with mp.workdps(PRECISION):
        offsets = [mp.mpf(0)] + [mp.sqrt(s) for s in RADICANDS]
        instant = 2 * mp.pi * n
        amplitude = 1 / mp.sqrt(32)
        # Original energies and large time: do not reduce these arguments.
        original = [amplitude * mp.exp(-mp.j * (r + offset) * instant)
                    for offset in offsets for r in range(8)]
        residuals = [n * mp.sqrt(s) - m for s, m in zip(RADICANDS, integers)]
        reduced_phases = [mp.mpc(1)] + [mp.exp(-2 * mp.pi * mp.j * x) for x in residuals]
        reduced = [amplitude * phase for phase in reduced_phases for _ in range(8)]
        state_error = max(abs(a - b) for a, b in zip(original, reduced))
        overlap = mp.fsum(amplitude * value for value in original)
        squared = 1 - abs(overlap) ** 2
        if squared < 0 and abs(squared) < mp.mpf('1e-70'):
            squared = mp.mpf(0)
        distance = mp.sqrt(squared)
        mean = mp.fsum(reduced_phases) / 4
        reduced_distance = mp.sqrt(mp.fsum(abs(z - mean) ** 2 for z in reduced_phases) / 4)
        text = lambda value: mp.nstr(value, PRECISION)
        record = {'n': n, 'time': text(instant), 'decimal_digits': PRECISION,
                  'state_agreement_error': text(state_error),
                  'distance': text(distance), 'reduced_distance': text(reduced_distance),
                  'distance_agreement_error': text(abs(distance - reduced_distance)),
                  'residuals': [text(x) for x in residuals],
                  'original_amplitudes': [[text(x.real), text(x.imag)] for x in original],
                  'reduced_group_phases': [[text(x.real), text(x.imag)] for x in reduced_phases],
                  'variance_bound': text(mp.pi * mp.sqrt(3) / Q),
                  'state_agreement_passed': bool(state_error <= mp.mpf('1e-60'))}
        state = np.array([complex(value) for value in original], dtype=np.complex128)
        state.setflags(write=False)
        return state, record


def group_projectors(groups=4, width=8):
    size = groups * width
    result = np.zeros((groups, size, size), dtype=np.complex128)
    for group in range(groups):
        indices = np.arange(group * width, (group + 1) * width)
        result[group, indices, indices] = 1
    result.setflags(write=False)
    return result


def restricted_representation(density, projectors):
    return sum((P @ density @ P for P in projectors), np.zeros_like(density))


def density_of(state):
    return np.outer(state, state.conj())


def helstrom(density0, density1):
    """Equal-prior binary discrimination, label 0 on the positive eigenspace."""
    difference = density0 - density1
    eigenvalues, eigenvectors = np.linalg.eigh((difference + difference.conj().T) / 2)
    # Numerical zero eigenvalues are assigned to label 1. Their sign is not data.
    positive = eigenvectors[:, eigenvalues > 1e-14]
    effect0 = positive @ positive.conj().T
    effect1 = np.eye(len(density0)) - effect0
    distance = float(np.sum(abs(eigenvalues)) / 2)
    success = float((np.trace(effect0 @ density0) + np.trace(effect1 @ density1)).real / 2)
    effect_eigenvalues = np.linalg.eigvalsh(effect0)
    quality = {
        'distance': distance, 'success': success, 'optimal_success': (1 + distance) / 2,
        'success_error': abs(success - (1 + distance) / 2),
        'positivity_violation': float(max(0., -effect_eigenvalues.min(), effect_eigenvalues.max() - 1)),
        'completeness_error': float(np.max(abs(effect0 + effect1 - np.eye(len(effect0))))),
        'idempotence_error': float(np.max(abs(effect0 @ effect0 - effect0))),
        'hermiticity_error': float(np.max(abs(effect0 - effect0.conj().T))),
    }
    return quality, effect0, eigenvalues


def peak_memory_bytes():
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == 'darwin' else value * 1024)


def run_protocol(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    inputs = ('studio/relational_clock.py', 'studio/operational_time.py',
              'studio/tests/test_operational_time.py', 'research/OPERATIONAL-TIME-PROPOSAL.md')
    captured = {}
    for name in inputs:
        target = output / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(name, target)
        captured[name] = sha256_file(target)
    began, cpu_began = time.monotonic(), time.process_time()
    checks, arrays = [], {}
    report = {'schema': 'operational-time-1', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'source_sha256': captured, 'q': Q, 'target_D': .05,
              'scope': 'known snapshot preparations; equal priors; one copy; no external cycle count',
              'versions': {'python': sys.version.split()[0], 'numpy': np.__version__, 'mpmath': mp.__version__},
              'checks': checks, 'cases': {}, 'calculation_completed': False}

    def truth(name, passed, **details):
        checks.append({'name': name, 'passed': bool(passed), **details})

    def upper(name, value, limit=TOLERANCE):
        value = float(value)
        truth(name, math.isfinite(value) and value <= limit, value=value, maximum=limit)

    def evaluate_pair(label, state0, state1, projectors, expected_D=None):
        arrays[label + '_states'] = np.asarray([state0, state1])
        before = array_digest(arrays[label + '_states'])
        base0, base1 = density_of(state0), density_of(state1)
        basis_cases = {}
        for basis_name, basis in [('energy', np.eye(len(state0))), ('fourier', fourier_basis(len(state0)))]:
            rho0, rho1 = basis @ base0 @ basis.conj().T, basis @ base1 @ basis.conj().T
            P = np.asarray([basis @ x @ basis.conj().T for x in projectors])
            visible0 = restricted_representation(rho0, P)
            visible1 = restricted_representation(rho1, P)
            prefix = label + '_' + basis_name
            full, effect, eigenvalues = helstrom(rho0, rho1)
            restricted, restricted_effect, restricted_eigenvalues = helstrom(visible0, visible1)
            arrays[prefix + '_density0'] = rho0
            arrays[prefix + '_density1'] = rho1
            arrays[prefix + '_effect0'] = effect
            arrays[prefix + '_restricted_effect0'] = restricted_effect
            arrays[prefix + '_difference_eigenvalues'] = eigenvalues
            arrays[prefix + '_restricted_eigenvalues'] = restricted_eigenvalues
            visible_error = float(np.max(abs(visible0 - visible1)))
            algebra_error = max(float(np.max(abs(restricted_effect @ x - x @ restricted_effect))) for x in P)
            upper(prefix + '_restricted_effect_in_algebra', algebra_error)
            for kind, measurement in [('full', full), ('restricted', restricted)]:
                for field in ('success_error', 'positivity_violation', 'completeness_error',
                              'idempotence_error', 'hermiticity_error'):
                    upper(prefix + '_' + kind + '_' + field, measurement[field])
            if expected_D is not None:
                upper(prefix + '_independent_pure_distance', abs(full['distance'] - expected_D))
            basis_cases[basis_name] = {'full': full, 'restricted': restricted,
                                       'visible_state_difference': visible_error,
                                       'restricted_algebra_error': algebra_error}
        for kind in ('full', 'restricted'):
            for field in ('distance', 'success'):
                upper(label + '_' + kind + '_basis_' + field,
                      abs(basis_cases['energy'][kind][field] - basis_cases['fourier'][kind][field]))
        truth(label + '_state_array_unchanged', before == array_digest(arrays[label + '_states']))
        report['cases'][label] = basis_cases
        return basis_cases

    def total_limit(_signum, _frame):
        raise TimeoutError('Declared five-minute calculation limit reached')

    old_handler = signal.signal(signal.SIGALRM, total_limit)
    signal.setitimer(signal.ITIMER_REAL, TOTAL_SECONDS)
    try:
        witness = first_collision()
        report['witness'] = witness
        truth('exact_integer_collision_certificate', verify_certificate(witness))
        truth('beyond_previous_grid_within_declared_endpoint', 4096 < witness['n'] <= Q ** 3,
              n=witness['n'], minimum_exclusive=4096, maximum=Q ** 3)
        upper('search_time', witness['search_wall_seconds'], SEARCH_SECONDS)
        # pi < 22/7: prove 3*(22/7)^2/Q^2 < (1/20)^2 by integers only.
        truth('exact_analytic_D_bound_below_one_twentieth', 3 * 22 ** 2 * 20 ** 2 < 7 ** 2 * Q ** 2,
              integer_left=3 * 22 ** 2 * 20 ** 2, integer_right=7 ** 2 * Q ** 2)
        initial = np.full(32, 1 / math.sqrt(32), dtype=np.complex128)
        initial.setflags(write=False)
        projectors = group_projectors()
        arrays['group_projectors'] = projectors
        for label, n, integers in [('first_return', 1, None), ('constructed_return', witness['n'], witness['m'])]:
            state, precision = high_precision_stroboscopic(n, integers)
            report.setdefault('high_precision', {})[label] = precision
            truth(label + '_80_digit_original_reduced_state_agreement', precision['state_agreement_passed'],
                  value=precision['state_agreement_error'], maximum='1e-60')
            upper(label + '_80_digit_distance_agreement', float(precision['distance_agreement_error']), 1e-60)
            distance = float(precision['distance'])
            result = evaluate_pair(label, initial, state, projectors, distance)
            for basis_name in ('energy', 'fourier'):
                upper(label + '_' + basis_name + '_restricted_state_identity',
                      result[basis_name]['visible_state_difference'])
                upper(label + '_' + basis_name + '_restricted_chance_success',
                      abs(result[basis_name]['restricted']['success'] - .5))
            if label == 'first_return':
                truth('first_return_globally_far', distance > .9, value=distance, minimum_exclusive=.9)
            else:
                truth('constructed_return_is_near_and_nonzero', 0 < distance <= .05,
                      value=distance, minimum_exclusive=0, maximum=.05)
                upper('constructed_return_optimal_success_at_most_52_5_percent',
                      result['energy']['full']['optimal_success'], .525)
                residuals = [abs(float(x)) for x in precision['residuals']]
                truth('independent_residual_values_obey_exact_certificate', max(residuals) < 1 / Q,
                      values=residuals, maximum_exclusive=1 / Q)
        identical = evaluate_pair('identical', initial, initial, projectors, 0.)
        upper('identical_control_success_half', abs(identical['energy']['full']['success'] - .5))
        with mp.workdps(PRECISION):
            commensurate = np.array([complex(mp.exp(-2 * mp.pi * mp.j * e) / 2) for e in range(4)])
        comm = evaluate_pair('commensurate', np.full(4, .5, dtype=np.complex128), commensurate,
                             group_projectors(2, 2), 0.)
        upper('commensurate_control_success_half', abs(comm['energy']['full']['success'] - .5))
        with mp.workdps(PRECISION):
            local = np.array([complex(mp.exp(-mp.j * (r + mp.sqrt(s)) * mp.mpf('0.2')) / mp.sqrt(32))
                              for s in (0, 2, 3, 5) for r in range(8)])
        nearby = evaluate_pair('local_change', initial, local, projectors)
        truth('restricted_algebra_sees_local_change', nearby['energy']['restricted']['success'] > .501,
              value=nearby['energy']['restricted']['success'], minimum_exclusive=.501)
        report['calculation_completed'] = True
    except Exception as error:
        report['exception'] = {'type': type(error).__name__, 'message': str(error)}
        if isinstance(error, SearchLimit):
            report['exception'].update(candidate_count=error.candidate_count, elapsed=error.elapsed)
        truth('calculation_completed_without_exception', False)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)

    report['calculation_wall_seconds'] = time.monotonic() - began
    report['calculation_cpu_seconds'] = time.process_time() - cpu_began
    report['peak_process_bytes'] = peak_memory_bytes()
    upper('total_calculation_time', report['calculation_wall_seconds'], TOTAL_SECONDS)
    upper('peak_process_memory', report['peak_process_bytes'], MAX_MEMORY_BYTES)
    np.savez_compressed(output / 'record.npz', **arrays)
    report['record_sha256'] = sha256_file(output / 'record.npz')
    storage_check = {'name': 'retained_record_size', 'value': 0, 'maximum': MAX_RECORD_BYTES, 'passed': True}
    checks.append(storage_check)

    # The metadata includes its own total byte count; settle its decimal width.
    for _ in range(5):
        report['all_passed'] = bool(report['calculation_completed'] and all(row['passed'] for row in checks))
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        members = {str(path.relative_to(output)): {'bytes': path.stat().st_size, 'sha256': sha256_file(path)}
                   for path in sorted(output.rglob('*')) if path.is_file() and path.name != 'manifest.json'}
        (output / 'manifest.json').write_text(json.dumps({'files': members}, indent=2) + '\n')
        size = sum(path.stat().st_size for path in output.rglob('*') if path.is_file())
        if size == storage_check['value']:
            break
        storage_check.update(value=size, passed=size <= MAX_RECORD_BYTES)
    else:
        raise RuntimeError('Record-size metadata did not settle; retained for inspection')
    print(json.dumps({'output': str(output), 'all_passed': report['all_passed'],
                      'check_count': len(checks), 'record_bytes': size,
                      'wall_seconds': report['calculation_wall_seconds'],
                      'cpu_seconds': report['calculation_cpu_seconds'],
                      'peak_process_bytes': report['peak_process_bytes'],
                      'n': report.get('witness', {}).get('n'),
                      'failures': [row for row in checks if not row['passed']]}), flush=True)
    if not report['all_passed']:
        raise RuntimeError('Operational-time admission failed; its complete record is retained')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='artifacts/studies/operational-time-001')
    with threadpool_limits(limits=2):
        run_protocol(parser.parse_args().output)
