"""Finite unitary phases and the relationships through which a return is seen.

Run scientific calculations on the remote computation host. Pair readouts are
calculated ensemble expectations, not simultaneous measurements of an unknown
single quantum system. No GPU, external assets or trained models are required.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import time

import numpy as np


@dataclass(frozen=True)
class PhaseClock:
    energies: np.ndarray
    populations: np.ndarray

    def __post_init__(self):
        energies = np.asarray(self.energies, dtype=np.float64).copy()
        populations = np.asarray(self.populations, dtype=np.float64).copy()
        if energies.ndim != 1 or len(energies) < 2 or populations.shape != energies.shape:
            raise ValueError('Energies and populations must be matching vectors with at least two levels')
        if not np.isfinite(energies).all() or not np.isfinite(populations).all():
            raise ValueError('Clock parameters must be finite')
        if np.any(populations <= 0) or abs(populations.sum() - 1.) > 1e-14:
            raise ValueError('Populations must be strictly positive and sum to one')
        energies.setflags(write=False)
        populations.setflags(write=False)
        object.__setattr__(self, 'energies', energies)
        object.__setattr__(self, 'populations', populations)

    @property
    def size(self):
        return len(self.energies)

    def states(self, times):
        times = np.atleast_1d(np.asarray(times, dtype=np.float64))
        if times.ndim != 1 or not np.isfinite(times).all():
            raise ValueError('Times must be a finite one-dimensional vector')
        states = np.sqrt(self.populations)[None] * np.exp(-1j * times[:, None] * self.energies)
        states.setflags(write=False)
        return states

    def return_distance_squared(self, states):
        """Pure-state trace distance squared, by a stable phase-variance identity."""
        states = np.asarray(states, dtype=np.complex128)
        if states.ndim != 2 or states.shape[1] != self.size:
            raise ValueError('States must contain one amplitude per clock level')
        phases = states / np.sqrt(self.populations)[None]
        mean = phases @ self.populations
        return np.sum(self.populations * np.abs(phases - mean[:, None]) ** 2, axis=1)


@dataclass(frozen=True)
class Observer:
    size: int
    edges: np.ndarray
    emphasis: np.ndarray

    def __post_init__(self):
        raw_edges = np.asarray(self.edges)
        if raw_edges.ndim != 2 or raw_edges.shape[1] != 2:
            raise ValueError('An observation edge needs two integer level indices')
        if not np.issubdtype(raw_edges.dtype, np.integer):
            raise ValueError('Observation indices must be integers')
        edges = raw_edges.astype(np.int64, copy=True)
        emphasis = np.asarray(self.emphasis, dtype=np.float64).copy()
        if not isinstance(self.size, int) or self.size < 2:
            raise ValueError('An observer needs at least two levels')
        if emphasis.shape != (len(edges),) or not np.isfinite(emphasis).all() or np.any(emphasis < 0):
            raise ValueError('Each observation needs a finite nonnegative emphasis')
        if np.any(edges < 0) or np.any(edges >= self.size) or np.any(edges[:, 0] >= edges[:, 1]):
            raise ValueError('Observation edges must be ordered distinct valid level indices')
        if len({tuple(edge) for edge in edges}) != len(edges):
            raise ValueError('Repeated observation edges are not admitted')
        edges.setflags(write=False)
        emphasis.setflags(write=False)
        object.__setattr__(self, 'edges', edges)
        object.__setattr__(self, 'emphasis', emphasis)

    def coherences(self, states):
        return states[:, self.edges[:, 0]] * states[:, self.edges[:, 1]].conj()

    def changes(self, clock, states):
        if clock.size != self.size:
            raise ValueError('The observer and clock dimensions differ')
        initial = np.sqrt(clock.populations[self.edges[:, 0]] * clock.populations[self.edges[:, 1]])
        return self.coherences(states) - initial[None]

    def discrepancy(self, changes):
        return np.sum(self.emphasis * np.abs(changes) ** 2, axis=-1)

    def components(self):
        adjacent = [[] for _ in range(self.size)]
        for (first, second), emphasis in zip(self.edges, self.emphasis):
            if emphasis > 0:
                adjacent[first].append(second)
                adjacent[second].append(first)
        remaining = set(range(self.size))
        components = []
        while remaining:
            pending = [min(remaining)]
            found = set()
            while pending:
                node = pending.pop()
                if node in found:
                    continue
                found.add(node)
                pending.extend(adjacent[node])
            remaining.difference_update(found)
            components.append(tuple(sorted(found)))
        return tuple(components)

    def spectral_gap(self, populations):
        """Zero means disconnected: no certificate controls every relative phase."""
        if len(self.components()) != 1:
            return 0.
        populations = np.asarray(populations, dtype=np.float64)
        if populations.shape != (self.size,) or np.any(populations <= 0):
            raise ValueError('The graph metric needs one positive population per level')
        laplacian = np.zeros((self.size, self.size), dtype=np.float64)
        for (first, second), emphasis in zip(self.edges, self.emphasis):
            weight = emphasis * populations[first] * populations[second]
            laplacian[first, first] += weight
            laplacian[second, second] += weight
            laplacian[first, second] -= weight
            laplacian[second, first] -= weight
        metric = laplacian / np.sqrt(populations[:, None] * populations[None, :])
        gap = float(np.linalg.eigvalsh(metric)[1])
        if gap <= 0:
            raise ArithmeticError('The connected graph gap is not numerically resolved')
        return gap


def complete_observer(size):
    edges = np.array([(i, j) for i in range(size) for j in range(i + 1, size)], dtype=np.int64)
    return Observer(size, edges, np.ones(len(edges)))


def four_level_clock(commensurate=False):
    offset = 2. if commensurate else math.sqrt(2.)
    return PhaseClock(np.array([0., 1., offset, 1. + offset]), np.full(4, .25))


def bridge_observer(emphasis):
    return Observer(4, np.array([[0, 1], [1, 2], [2, 3]]), np.array([1., emphasis, 1.]))


def bridge_gap(emphasis):
    """Analytical four-level gap, rationalized near disconnection."""
    if not math.isfinite(emphasis) or emphasis < 0:
        raise ValueError('Bridge emphasis must be finite and nonnegative')
    return emphasis / (2. * (1. + emphasis + math.sqrt(1. + emphasis ** 2)))


def thirty_two_level_clock():
    offsets = np.sqrt([0., 2., 3., 5.])
    return PhaseClock((offsets[:, None] + np.arange(8)[None]).reshape(-1), np.full(32, 1. / 32.))


def group_observer(connected=False):
    edges = [(g * 8 + r, g * 8 + r + 1) for g in range(4) for r in range(7)]
    if connected:
        edges.extend([(7, 8), (15, 16), (23, 24)])
    return Observer(32, np.array(edges, dtype=np.int64), np.ones(len(edges)))


def fourier_basis(size):
    indices = np.arange(size)
    return np.exp(2j * np.pi * indices[:, None] * indices[None, :] / size) / math.sqrt(size)


def operator_reference(clock, instant, edges, basis=None):
    """Independent dense exponential, density operator and measurement matrices.

    The standard Y operator has expectation -2 Im(rho_jk), hence the minus
    sign when reconstructing the complex coherence from the two expectations.
    """
    from scipy.linalg import expm

    basis = np.eye(clock.size, dtype=np.complex128) if basis is None else np.asarray(basis)
    hamiltonian = basis @ np.diag(clock.energies) @ basis.conj().T
    initial = basis @ np.sqrt(clock.populations).astype(np.complex128)
    state = expm(-1j * instant * hamiltonian) @ initial
    density = np.outer(state, state.conj())
    initial_density = np.outer(initial, initial.conj())
    trace_distance = .5 * np.abs(np.linalg.eigvalsh(density - initial_density)).sum()
    coherences = []
    for first, second in edges:
        elementary = np.outer(basis[:, first], basis[:, second].conj())
        x_observable = elementary + elementary.conj().T
        y_observable = -1j * elementary + 1j * elementary.conj().T
        x_value = np.trace(density @ x_observable).real
        y_value = np.trace(density @ y_observable).real
        coherences.append((x_value - 1j * y_value) / 2.)
    return {'state': state, 'density': density, 'distance': float(trace_distance),
            'coherences': np.asarray(coherences, dtype=np.complex128)}


def density_distance_squared(states, initial, block_size=64):
    """Independent trace-norm calculation in small batches, without overlap formulas."""
    initial_density = np.outer(initial, initial.conj())
    result = np.empty(len(states), dtype=np.float64)
    for start in range(0, len(states), block_size):
        block = states[start:start + block_size]
        differences = block[:, :, None] * block[:, None, :].conj() - initial_density[None]
        distance = .5 * np.abs(np.linalg.eigvalsh(differences)).sum(axis=1)
        result[start:start + len(block)] = distance ** 2
    return result


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def array_digest(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def run_protocol(output):
    """Execute the declared small study, retaining failed admissions as evidence."""
    import scipy
    from threadpoolctl import threadpool_limits

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    inputs = ('studio/relational_clock.py', 'studio/tests/test_relational_clock.py',
              'research/RELATIONAL-CLOCK-PROTOCOL.md')
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

    clock = four_level_clock()
    special = np.array([0., 2 * np.pi, 4 * np.pi, *[2 * np.pi * n for n in (5, 12, 29, 70, 169)]])
    times = np.unique(np.concatenate([np.linspace(0, 20 * np.pi, 4097), special]))
    states = clock.states(times)
    digest_before = array_digest(states)
    distances_squared = clock.return_distance_squared(states)
    first_return_index = int(np.searchsorted(times, 2 * np.pi))
    full = complete_observer(4)
    full_discrepancy = full.discrepancy(full.changes(clock, states))
    upper('four_level_norm_error', np.max(abs(np.sum(abs(states) ** 2, axis=1) - 1)), 1e-12)
    upper('four_level_complete_identity', np.max(abs(full_discrepancy - distances_squared)), 1e-12)
    with threadpool_limits(limits=2):
        matrix_distance_squared = density_distance_squared(states, np.sqrt(clock.populations))
    upper('four_level_all_times_density_distance_error', np.max(abs(full_discrepancy - matrix_distance_squared)), 1e-12)
    dense_cases = []
    reference_state_error = reference_readout_error = reference_distance_error = 0.
    with threadpool_limits(limits=2):
        for instant in special:
            expected = clock.states([instant])[0]
            index = int(np.searchsorted(times, instant))
            for label, basis in [('energy', np.eye(4)), ('fourier', fourier_basis(4))]:
                reference = operator_reference(clock, float(instant), full.edges, basis)
                reference_state_error = max(reference_state_error, float(np.max(abs(reference['state'] - basis @ expected))))
                reference_readout_error = max(reference_readout_error, float(np.max(abs(reference['coherences'] - full.coherences(states[index:index + 1])[0]))))
                reference_distance_error = max(reference_distance_error, abs(reference['distance'] ** 2 - full_discrepancy[index]))
                dense_cases.append({'time': float(instant), 'basis': label, 'trace_distance': reference['distance']})
    upper('dense_exponential_state_error', reference_state_error, 1e-12)
    upper('dense_operator_coherence_error', reference_readout_error, 2e-12)
    upper('dense_operator_distance_squared_error', reference_distance_error, 1e-12)
    false_return = operator_reference(clock, 2 * np.pi, full.edges)
    lower('disconnected_return_full_trace_distance', false_return['distance'], .9)
    upper('analytical_false_return_distance_error', abs(false_return['distance'] - abs(math.sin(np.pi * math.sqrt(2)))), 1e-12)
    matched_weight = Observer(4, np.array([[0, 1], [2, 3]]), np.full(2, 1.5))
    matched_R = float(matched_weight.discrepancy(matched_weight.changes(clock, states[first_return_index:first_return_index + 1]))[0])
    upper('matched_weight_disconnected_return', matched_R, 1e-24)
    truth('matched_weight_sum_equals_connected', matched_weight.emphasis.sum() == bridge_observer(1.).emphasis.sum())
    positive = operator_reference(four_level_clock(commensurate=True), 2 * np.pi, full.edges)
    upper('commensurate_positive_global_return_distance', positive['distance'], 1e-12)
    near_return = operator_reference(clock, 2 * np.pi * 169, full.edges)
    upper('declared_irrational_near_return_distance', near_return['distance'], .01)

    graphs = []
    noise_cases = []
    observer_arrays = {}
    for emphasis in (0., 1e-6, 1e-4, 1e-2, 1.):
        observer = bridge_observer(emphasis)
        changes = observer.changes(clock, states)
        discrepancy = observer.discrepancy(changes)
        gap = observer.spectral_gap(clock.populations)
        analytical_gap = bridge_gap(emphasis)
        upper(f'gap_formula_{emphasis:g}', abs(gap - analytical_gap), 1e-12)
        upper(f'bridge_return_formula_{emphasis:g}', abs(discrepancy[first_return_index] - emphasis * false_return['distance'] ** 2 / 4), 1e-12)
        detail = {'emphasis': emphasis, 'components': len(observer.components()),
                  'spectral_gap': gap, 'analytical_gap': analytical_gap,
                  'observation_discrepancy_at_2pi': float(discrepancy[first_return_index]),
                  'passes_observation_threshold_1e_minus_6': bool(discrepancy[first_return_index] <= 1e-6)}
        observer_arrays[f'four_R_bridge_{emphasis:g}'] = discrepancy
        if gap == 0:
            upper('disconnected_observation_return', discrepancy[first_return_index], 1e-24)
        else:
            slack = discrepancy / gap - distances_squared
            lower(f'connected_bound_slack_{emphasis:g}', np.min(slack), -2e-11)
            detail['minimum_bound_slack'] = float(np.min(slack))
            raw = changes[first_return_index].copy()
            direction = np.array([1. + 2j, -2. + .5j, .75 - 1j])
            direction /= math.sqrt(float(observer.discrepancy(direction)))
            errors = [(f'bounded_{eta:g}', eta * direction) for eta in (0., 1e-6, 1e-3, .1)]
            errors.append(('cancellation', -raw))
            for name, error in errors:
                eta = math.sqrt(float(observer.discrepancy(error)))
                measured = raw + error
                measured_R = float(observer.discrepancy(measured))
                bound = min(1., (math.sqrt(measured_R) + eta) / math.sqrt(gap))
                slack = bound - false_return['distance']
                lower(f'noise_bound_slack_{emphasis:g}_{name}', slack, -2e-11)
                noise_cases.append({'emphasis': emphasis, 'kind': name, 'error_norm': eta,
                                    'measured_discrepancy': measured_R, 'distance_bound': bound,
                                    'actual_distance': false_return['distance'], 'slack': slack})
        graphs.append(detail)

    shifted = PhaseClock(clock.energies + 3.75, clock.populations)
    shifted_states = shifted.states(times)
    upper('common_energy_shift_distance_error', np.max(abs(shifted.return_distance_squared(shifted_states) - distances_squared)), 2e-12)
    upper('common_energy_shift_observation_error', np.max(abs(full.coherences(shifted_states) - full.coherences(states))), 2e-12)
    stationary = PhaseClock(np.zeros(4), clock.populations)
    upper('stationary_state_distance_squared', stationary.return_distance_squared(stationary.states(times)).max(), 2e-12)
    permutation = np.array([2, 0, 3, 1])
    relabeled = PhaseClock(clock.energies[permutation], clock.populations[permutation])
    relabeled_states = relabeled.states(times)
    inverse = np.argsort(permutation)
    upper('relabeling_state_error', np.max(abs(relabeled_states[:, inverse] - states)), 2e-12)
    upper('relabeling_distance_error', np.max(abs(relabeled.return_distance_squared(relabeled_states) - distances_squared)), 2e-12)
    truth('four_level_state_bytes_unchanged', array_digest(states) == digest_before)

    large_clock = thirty_two_level_clock()
    large_states = large_clock.states(times)
    large_digest_before = array_digest(large_states)
    large_distance_squared = large_clock.return_distance_squared(large_states)
    with threadpool_limits(limits=2):
        large_matrix_distance_squared = density_distance_squared(large_states, np.sqrt(large_clock.populations))
    upper('thirty_two_all_times_density_distance_error', np.max(abs(large_distance_squared - large_matrix_distance_squared)), 2e-12)
    large_graphs = []
    selected_coherences = None
    with threadpool_limits(limits=2):
        for name, observer in [('disconnected', group_observer()), ('connected', group_observer(True)),
                               ('complete', complete_observer(32))]:
            discrepancy = observer.discrepancy(observer.changes(large_clock, large_states))
            gap = observer.spectral_gap(large_clock.populations)
            detail = {'name': name, 'components': len(observer.components()), 'edges': len(observer.edges),
                      'spectral_gap': gap, 'observation_discrepancy_at_2pi': float(discrepancy[first_return_index])}
            if gap:
                slack = discrepancy / gap - large_distance_squared
                lower(f'thirty_two_{name}_bound_slack', np.min(slack), -2e-11)
                detail['minimum_bound_slack'] = float(np.min(slack))
            else:
                upper('thirty_two_disconnected_return', discrepancy[first_return_index], 1e-24)
            if name == 'complete':
                upper('thirty_two_complete_identity', np.max(abs(discrepancy - large_distance_squared)), 2e-12)
                dense_error = 0.
                for instant in special:
                    index = int(np.searchsorted(times, instant))
                    reference = operator_reference(large_clock, float(instant), np.empty((0, 2), dtype=int))
                    dense_error = max(dense_error, abs(reference['distance'] ** 2 - discrepancy[index]))
                upper('thirty_two_dense_density_distance_error', dense_error, 2e-12)
            if name == 'connected':
                selected_coherences = observer.coherences(large_states)
            observer_arrays[f'thirty_two_R_{name}'] = discrepancy
            large_graphs.append(detail)
    upper('thirty_two_norm_error', np.max(abs(np.sum(abs(large_states) ** 2, axis=1) - 1)), 1e-12)
    truth('thirty_two_state_bytes_unchanged', array_digest(large_states) == large_digest_before)

    arrays = {'time': times, 'special_times': special, 'four_states': states,
              'four_distance_squared': distances_squared, 'four_density_distance_squared': matrix_distance_squared,
              'four_R_complete': full_discrepancy,
              'thirty_two_states': large_states, 'thirty_two_distance_squared': large_distance_squared,
              'thirty_two_density_distance_squared': large_matrix_distance_squared,
              'thirty_two_connected_coherences': selected_coherences, **observer_arrays}
    np.savez_compressed(output / 'record.npz', **arrays)
    report = {'format': 'palimpsest-relational-clock', 'version': 1,
              'verified_utc': datetime.now(timezone.utc).isoformat(),
              'input_sha256': captured, 'numpy_version': np.__version__, 'scipy_version': scipy.__version__,
              'units': 'hbar=1; E is angular frequency per abstract time unit; states have unit norm; populations sum to one; D is half the trace norm; R is weighted squared coherence change',
              'four_level': {'energies': clock.energies.tolist(), 'populations': clock.populations.tolist(),
                             'false_return_distance': false_return['distance'],
                             'positive_control_return_distance': positive['distance'],
                             'near_return_n': 169, 'near_return_distance': near_return['distance'],
                             'matched_weight_disconnected_R_at_2pi': matched_R,
                             'state_sha256': digest_before, 'graphs': graphs},
              'thirty_two_level': {'energies': large_clock.energies.tolist(), 'populations': large_clock.populations.tolist(),
                                   'full_distance_at_2pi': float(math.sqrt(large_distance_squared[first_return_index])),
                                   'state_sha256': large_digest_before, 'graphs': large_graphs},
              'dense_reference_cases': dense_cases, 'bounded_noise_cases': noise_cases,
              'time_samples': len(times), 'checks': checks, 'all_passed': all(c['passed'] for c in checks),
              'elapsed_seconds': time.monotonic() - began,
              'scope': 'Exact finite unitary model, with numerical cross-checks of a proved graph observation bound. Readouts are calculated ensemble expectations. The artwork is an authored interpretation. No physical quantum realization, backaction-free single-system monitoring, entropy production, human perception result or universal novelty claim.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    manifest = {'format': 'palimpsest-relational-clock-files', 'version': 1,
                'files': [{'path': str(path.relative_to(output)), 'bytes': path.stat().st_size, 'sha256': sha256_file(path)}
                          for path in sorted(output.rglob('*')) if path.is_file()]}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'all_passed': report['all_passed'], 'checks': len(checks),
                      'false_return_distance': false_return['distance'], 'near_return_distance': near_return['distance'],
                      'elapsed_seconds': report['elapsed_seconds'],
                      'record_bytes': sum(p.stat().st_size for p in output.rglob('*') if p.is_file())}), flush=True)
    if not report['all_passed']:
        raise RuntimeError('Relational-clock admission failed; the complete report has been retained')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='artifacts/studies/relational-clock-001')
    run_protocol(parser.parse_args().output)
