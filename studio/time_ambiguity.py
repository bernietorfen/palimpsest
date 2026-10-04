"""Local readout speed and distant aliases of the admitted relational clocks.

Execute on the remote computation host. Error radii describe deterministic
weighted expectation-value uncertainty, not measurement shots or backaction.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import time

import numpy as np
from scipy.linalg import expm
from scipy.optimize import brentq
from threadpoolctl import threadpool_limits

from studio.relational_clock import (
    Observer, PhaseClock, array_digest, bridge_observer, complete_observer,
    four_level_clock, fourier_basis, group_observer, sha256_file,
    thirty_two_level_clock,
)


ERROR_RADII = (0.001, 0.01, 0.05)
LOCAL_DELTAS = (1e-4, 1e-3, 1e-2, .1, .2, .5)
START_TIMES = (0., .37, 9.1)
WITNESS_CYCLES = (1, 2, 5, 12, 29, 70, 169, 985, 2378, 4096)
BORDERLINE_DISTANCE = 1e-10


def clock_cases():
    ordinary = four_level_clock()
    four_observers = {'disconnected': bridge_observer(0.),
                      'matched': Observer(4, np.array([[0, 1], [2, 3]]), np.full(2, 1.5)),
                      'weak': bridge_observer(1e-6), 'connected': bridge_observer(1.),
                      'complete': complete_observer(4)}
    controls = {key: four_observers[key] for key in ('disconnected', 'connected', 'complete')}
    return {
        'four': (ordinary, four_observers),
        'thirty_two': (thirty_two_level_clock(), {'disconnected': group_observer(),
                                                'connected': group_observer(True),
                                                'complete': complete_observer(32)}),
        'commensurate': (four_level_clock(True), controls),
        'stationary': (PhaseClock(np.zeros(4), np.full(4, .25)), controls),
    }


def coefficients(clock, observer):
    first, second = observer.edges.T
    gaps = clock.energies[first] - clock.energies[second]
    weights = observer.emphasis * clock.populations[first] * clock.populations[second]
    C = float(np.sum(weights * gaps ** 2))
    K = float(np.sum(weights * gaps ** 4))
    active = np.abs(gaps[weights > 0])
    maximum_gap = float(active.max()) if len(active) else 0.
    return {'C': C, 'K': K, 'maximum_gap': maximum_gap,
            'monotone_interval_end': math.pi / maximum_gap if maximum_gap else None}


def analytic_discrepancy(clock, observer, deltas):
    deltas = np.atleast_1d(np.asarray(deltas, dtype=np.float64))
    first, second = observer.edges.T
    gaps = clock.energies[first] - clock.energies[second]
    weights = observer.emphasis * clock.populations[first] * clock.populations[second]
    result = np.empty(len(deltas), dtype=np.float64)
    for start in range(0, len(deltas), 512):
        block = deltas[start:start + 512]
        result[start:start + len(block)] = 4 * np.sum(weights * np.sin(block[:, None] * gaps / 2) ** 2, axis=1)
    return result


def readout_from_states(observer, states):
    return np.sqrt(observer.emphasis)[None] * observer.coherences(states)


def ambiguity_labels(distances, eta, tolerance=BORDERLINE_DISTANCE):
    """-1: overlapping error balls; 0: numerical borderline; +1: disjoint."""
    margins = np.asarray(distances) - 2 * eta
    labels = np.zeros(margins.shape, dtype=np.int8)
    labels[margins < -tolerance] = -1
    labels[margins > tolerance] = 1
    return margins, labels


def local_resolution(clock, observer, eta):
    if not math.isfinite(eta) or eta <= 0:
        raise ValueError('A local resolution threshold needs a positive finite error radius')
    constants = coefficients(clock, observer)
    endpoint = constants['monotone_interval_end']
    if endpoint is None:
        return {'resolved': False, 'reason': 'stationary readout', 'eta': eta}
    distance = lambda delta: math.sqrt(float(analytic_discrepancy(clock, observer, [delta])[0]))
    if distance(endpoint) <= 2 * eta:
        return {'resolved': False, 'reason': 'threshold not reached in the proved monotone interval',
                'eta': eta, 'bracket': [0., endpoint]}
    root = brentq(lambda delta: distance(delta) - 2 * eta, 0., endpoint, xtol=5e-15, rtol=1e-14)
    return {'resolved': True, 'eta': eta, 'separation': root,
            'residual': distance(root) - 2 * eta, 'bracket': [0., endpoint],
            'quadratic_prediction': 2 * eta / math.sqrt(constants['C'])}


class DenseReference:
    """Explicit Hermitian operators and dense propagation, independent of gap sums."""
    def __init__(self, clock, basis):
        self.clock = clock
        self.basis = np.asarray(basis, dtype=np.complex128)
        self.H = self.basis @ np.diag(clock.energies) @ self.basis.conj().T
        self.initial = self.basis @ np.sqrt(clock.populations)
        self.edges = complete_observer(clock.size).edges
        self.indices = {tuple(edge): index for index, edge in enumerate(self.edges)}
        x_operators, y_operators = [], []
        for first, second in self.edges:
            elementary = np.outer(self.basis[:, first], self.basis[:, second].conj())
            x_operators.append(elementary + elementary.conj().T)
            y_operators.append(-1j * elementary + 1j * elementary.conj().T)
        self.X = np.asarray(x_operators)
        self.Y = np.asarray(y_operators)
        rho = np.outer(self.initial, self.initial.conj())
        self.rho_dot = -1j * (self.H @ rho - rho @ self.H)
        L = 2 * self.rho_dot
        self.sld_residual = float(np.max(abs((L @ rho + rho @ L) / 2 - self.rho_dot)))
        self.qfi = float(np.trace(rho @ L @ L).real)
        self.derivative = self.expectations(self.rho_dot)
        self.cache = {}

    def expectations(self, density):
        x = np.einsum('ij,eji->e', density, self.X).real
        y = np.einsum('ij,eji->e', density, self.Y).real
        return (x - 1j * y) / 2

    def at(self, instant):
        instant = float(instant)
        if instant not in self.cache:
            state = expm(-1j * instant * self.H) @ self.initial
            self.cache[instant] = self.expectations(np.outer(state, state.conj()))
        return self.cache[instant]

    def selected(self, vector, observer):
        indices = [self.indices[tuple(edge)] for edge in observer.edges]
        return np.sqrt(observer.emphasis) * vector[indices]


def exact_coefficient(clock_id, observer_id):
    if clock_id == 'stationary':
        return '0', 0.
    if clock_id == 'commensurate':
        formulas = {'disconnected': ('1/8', 1/8), 'connected': ('3/16', 3/16), 'complete': ('5/4', 5/4)}
        return formulas[observer_id]
    if clock_id == 'four':
        formulas = {'disconnected': ('1/8', 1/8), 'matched': ('3/16', 3/16),
                    'weak': ('1/8+10^-6*(3-2*sqrt(2))/16', 1/8 + 1e-6 * (3 - 2 * math.sqrt(2)) / 16),
                    'connected': ('(5-2*sqrt(2))/16', (5 - 2 * math.sqrt(2)) / 16),
                    'complete': ('3/4', 3/4)}
        return formulas[observer_id]
    offsets = np.sqrt([0., 2., 3., 5.])
    if observer_id == 'disconnected':
        return '7/256', 7/256
    if observer_id == 'connected':
        return '[28+sum_g(7+b_g-b_(g+1))^2]/1024', float((28 + np.sum((7 + offsets[:-1] - offsets[1:]) ** 2)) / 1024)
    return '31/4-(sqrt(2)+sqrt(3)+sqrt(5))^2/16', 31/4 - (math.sqrt(2) + math.sqrt(3) + math.sqrt(5)) ** 2 / 16


def run_protocol(output):
    import scipy

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    inputs = ('studio/relational_clock.py', 'studio/time_ambiguity.py',
              'studio/tests/test_time_ambiguity.py', 'research/TIME-AMBIGUITY-PROPOSAL.md')
    captured = {}
    for name in inputs:
        target = output / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(name, target)
        captured[name] = sha256_file(target)
    began = time.monotonic()
    checks = []

    def upper(name, value, limit):
        value = float(value)
        checks.append({'name': name, 'value': value, 'maximum': limit,
                       'passed': math.isfinite(value) and value <= limit})

    def lower(name, value, limit):
        value = float(value)
        checks.append({'name': name, 'value': value, 'minimum': limit,
                       'passed': math.isfinite(value) and value >= limit})

    def truth(name, value):
        checks.append({'name': name, 'passed': bool(value)})

    cycles = np.arange(1, 4097, dtype=np.int64)
    grid = 2 * np.pi * cycles
    arrays = {'stroboscopic_cycles': cycles, 'stroboscopic_separations': grid,
              'local_deltas': np.asarray(LOCAL_DELTAS), 'start_times': np.asarray(START_TIMES),
              'error_radii': np.asarray(ERROR_RADII)}
    models = {}
    matrix_cases = []
    midpoint_cases = []
    for clock_id, (clock, observers) in clock_cases().items():
        states = clock.states(np.concatenate(([0.], grid)))
        states_digest = array_digest(states)
        parameters_digest = array_digest(np.concatenate((clock.energies, clock.populations)))
        arrays[clock_id + '_states'] = states
        mean = float(clock.populations @ clock.energies)
        variance = float(clock.populations @ (clock.energies - mean) ** 2)
        model = {'energies': clock.energies.tolist(), 'populations': clock.populations.tolist(),
                 'energy_variance': variance, 'state_sha256': states_digest, 'observers': {}}
        bases = [('energy', np.eye(clock.size))]
        if clock.size == 4:
            bases.append(('fourier', fourier_basis(4)))
        references = [(name, DenseReference(clock, basis)) for name, basis in bases]
        for name, reference in references:
            upper(f'{clock_id}_{name}_SLD_equation_residual', reference.sld_residual, 2e-12)
            upper(f'{clock_id}_{name}_QFI_variance_identity', abs(reference.qfi - 4 * variance), 2e-12)
        model['qfi'] = references[0][1].qfi

        for observer_id, observer in observers.items():
            key = f'{clock_id}_{observer_id}'
            constants = coefficients(clock, observer)
            symbolic_C, expected_C = exact_coefficient(clock_id, observer_id)
            upper(key + '_exact_C', abs(constants['C'] - expected_C), 2e-12)
            if observer_id == 'complete':
                upper(key + '_C_variance_identity', abs(constants['C'] - variance), 2e-12)
            matrix_error = starting_time_error = max_taylor_excess = 0.
            for basis_name, reference in references:
                derivative = reference.selected(reference.derivative, observer)
                derivative_C = float(np.vdot(derivative, derivative).real)
                upper(key + '_' + basis_name + '_dense_derivative_C', abs(derivative_C - constants['C']), 2e-12)
                for delta in LOCAL_DELTAS:
                    analytic_R = float(analytic_discrepancy(clock, observer, [delta])[0])
                    for start in START_TIMES:
                        first = reference.selected(reference.at(start), observer)
                        second = reference.selected(reference.at(start + delta), observer)
                        change = second - first
                        R = float(np.vdot(change, change).real)
                        quotient = R / delta ** 2
                        lower_bound = constants['C'] - constants['K'] * delta ** 2 / 12
                        excess = max(0., quotient - constants['C'], lower_bound - quotient)
                        error = abs(math.sqrt(R) - math.sqrt(analytic_R))
                        max_taylor_excess = max(max_taylor_excess, excess)
                        starting_time_error = max(starting_time_error, error)
                        matrix_error = max(matrix_error, abs(R - analytic_R))
                        matrix_cases.append({'clock': clock_id, 'observer': observer_id, 'basis': basis_name,
                                             'start': start, 'delta': delta, 'R_dense': R,
                                             'R_analytic': analytic_R, 'quadratic_quotient': quotient,
                                             'taylor_lower_coefficient': lower_bound, 'C': constants['C'],
                                             'taylor_excess': excess, 'passed': excess <= 2e-10 and error <= 2e-12})
                        midpoint = (first + second) / 2
                        distances = [float(np.linalg.norm(midpoint - first)), float(np.linalg.norm(midpoint - second))]
                        upper(key + f'_{basis_name}_{start}_{delta}_midpoint_identity', max(abs(d - math.sqrt(R) / 2) for d in distances), 2e-12)
            upper(key + '_Taylor_sandwich_excess', max_taylor_excess, 2e-10)
            upper(key + '_starting_time_distance_error', starting_time_error, 2e-12)

            R_grid = analytic_discrepancy(clock, observer, grid)
            distances = np.sqrt(R_grid)
            arrays[key + '_R'] = R_grid
            arrays[key + '_distance'] = distances
            grid_summary = []
            local_thresholds = []
            for eta in ERROR_RADII:
                margin, labels = ambiguity_labels(distances, eta)
                arrays[key + f'_margin_eta_{eta:g}'] = margin
                arrays[key + f'_class_eta_{eta:g}'] = labels
                overlapping = cycles[labels == -1]
                borderline = cycles[labels == 0]
                grid_summary.append({'eta': eta, 'overlap_count': int(len(overlapping)),
                                     'disjoint_count': int(np.sum(labels == 1)),
                                     'borderline_cycles': borderline.tolist(),
                                     'first_overlapping_candidate': int(overlapping[0]) if len(overlapping) else None,
                                     'minimum_signed_margin': float(margin.min()),
                                     'maximum_signed_margin': float(margin.max())})
                threshold = local_resolution(clock, observer, eta)
                if threshold['resolved']:
                    upper(key + f'_local_threshold_residual_{eta:g}', abs(threshold['residual']), 2e-12)
                    lower(key + f'_local_threshold_quadratic_lower_{eta:g}', threshold['separation'] - threshold['quadratic_prediction'], -2e-12)
                local_thresholds.append(threshold)
            if clock_id == 'commensurate':
                upper(key + '_all_stroboscopic_returns', distances.max(), 2e-11)
            if clock_id == 'stationary':
                upper(key + '_all_times_stationary', max(distances.max(), constants['C']), 0.)

            witness_times = 2 * np.pi * np.array(WITNESS_CYCLES)
            witness_states = clock.states(np.concatenate(([0.], witness_times)))
            readings = readout_from_states(observer, witness_states)
            first = readings[0]
            second = readings[1:]
            midpoints = (first[None] + second) / 2
            endpoint_errors = np.stack([np.linalg.norm(midpoints - first, axis=1),
                                       np.linalg.norm(midpoints - second, axis=1)], axis=1)
            separation = np.linalg.norm(second - first, axis=1)
            upper(key + '_witness_midpoint_identity', np.max(abs(endpoint_errors - separation[:, None] / 2)), 2e-12)
            upper(key + '_witness_analytic_distance_error', np.max(abs(separation - np.sqrt(analytic_discrepancy(clock, observer, witness_times)))), 2e-11)
            arrays[key + '_witness_times'] = witness_times
            arrays[key + '_witness_initial'] = first
            arrays[key + '_witness_readouts'] = second
            arrays[key + '_witness_midpoints'] = midpoints
            arrays[key + '_witness_endpoint_errors'] = endpoint_errors
            for index, cycle in enumerate(WITNESS_CYCLES):
                for eta in ERROR_RADII:
                    margin = float(separation[index] - 2 * eta)
                    midpoint_cases.append({'clock': clock_id, 'observer': observer_id,
                                           'cycle': cycle, 'eta': eta, 'separation': float(separation[index]),
                                           'endpoint_errors': endpoint_errors[index].tolist(),
                                           'triangle_gap': margin,
                                           'classification': 'overlap' if margin < -BORDERLINE_DISTANCE else
                                                             'disjoint' if margin > BORDERLINE_DISTANCE else 'borderline'})
            model['observers'][observer_id] = {
                **constants, 'C_expression': symbolic_C, 'sum_emphases': float(observer.emphasis.sum()),
                'matrix_R_max_error': matrix_error, 'starting_time_distance_max_error': starting_time_error,
                'taylor_max_excess': max_taylor_excess, 'grid_summary': grid_summary,
                'local_thresholds': local_thresholds,
                'distance_at_point_two': float(math.sqrt(analytic_discrepancy(clock, observer, [.2])[0])),
                'distance_at_two_pi': float(distances[0]),
            }
        truth(clock_id + '_state_bytes_unchanged', array_digest(states) == states_digest)
        truth(clock_id + '_configuration_unchanged', array_digest(np.concatenate((clock.energies, clock.populations))) == parameters_digest)
        models[clock_id] = model

    for clock_id in ('four', 'thirty_two'):
        rows = models[clock_id]['observers']
        lower(clock_id + '_local_disconnected_resolves_point_two', rows['disconnected']['distance_at_point_two'], .02 + BORDERLINE_DISTANCE)
        upper(clock_id + '_disconnected_alias_two_pi', rows['disconnected']['distance_at_two_pi'], 1e-12)
        for observer_id in ('connected', 'complete'):
            lower(clock_id + '_' + observer_id + '_rejects_first_alias', rows[observer_id]['distance_at_two_pi'], .02 + BORDERLINE_DISTANCE)
    lower('matched_weight_local_sharpness_exceeds_connected',
          models['four']['observers']['matched']['C'] - models['four']['observers']['connected']['C'], 0.)
    upper('matched_weight_alias_remains', models['four']['observers']['matched']['distance_at_two_pi'], 1e-12)
    for observer_id, cycle in [('connected', 29), ('complete', 70)]:
        row = next(item for item in midpoint_cases if item['clock'] == 'four' and item['observer'] == observer_id
                   and item['cycle'] == cycle and item['eta'] == .01)
        upper(f'{observer_id}_declared_nonzero_midpoint_overlap', max(row['endpoint_errors']), .01)
        lower(f'{observer_id}_declared_midpoint_has_nonzero_separation', row['separation'], 1e-4)
    truth('every_dense_matrix_case_passed', all(row['passed'] for row in matrix_cases))

    np.savez_compressed(output / 'record.npz', **arrays)
    report = {'format': 'palimpsest-time-ambiguity', 'version': 1,
              'verified_utc': datetime.now(timezone.utc).isoformat(), 'input_sha256': captured,
              'numpy_version': np.__version__, 'scipy_version': scipy.__version__,
              'grid': {'name': 'stroboscopic candidate grid', 'cycle_minimum': 1, 'cycle_maximum': 4096,
                       'lag_formula': '2*pi*n', 'horizon': float(grid[-1]), 'continuous_first_hit_claim': False},
              'error_radii': ERROR_RADII, 'borderline_distance': BORDERLINE_DISTANCE,
              'local_deltas': LOCAL_DELTAS, 'starting_times': START_TIMES,
              'models': models, 'dense_matrix_cases': matrix_cases, 'midpoint_cases': midpoint_cases,
              'checks': checks, 'all_passed': all(check['passed'] for check in checks),
              'elapsed_seconds': time.monotonic() - began,
              'scope': 'Finite candidate-time ambiguity under a chosen deterministic weighted expectation-value error norm. Pure fixed-population states, known parameters, no equal shot/resource noise comparison, no measurement-backaction model, no irreversible loss. QFI is the established optimized local sensitivity, not this graph norm or a global clock guarantee.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    manifest = {'format': 'palimpsest-time-ambiguity-files', 'version': 1,
                'files': [{'path': str(path.relative_to(output)), 'bytes': path.stat().st_size, 'sha256': sha256_file(path)}
                          for path in sorted(output.rglob('*')) if path.is_file()]}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'all_passed': report['all_passed'], 'checks': len(checks),
                      'dense_matrix_cases': len(matrix_cases), 'midpoint_cases': len(midpoint_cases),
                      'elapsed_seconds': report['elapsed_seconds'],
                      'record_bytes': sum(path.stat().st_size for path in output.rglob('*') if path.is_file()),
                      'failures': [check for check in checks if not check['passed']]}), flush=True)
    if not report['all_passed']:
        raise RuntimeError('Time-ambiguity admission failed; the complete record has been retained')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='artifacts/studies/time-ambiguity-001')
    with threadpool_limits(limits=2):
        run_protocol(parser.parse_args().output)
