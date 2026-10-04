"""A fixed finite isolation test for the recorded clock return.

Six times, three preparations, two CPU threads and no GPU. The clock and
one-qubit environment evolve jointly and unitarily. Reduced entropy is called
entanglement entropy only when the joint preparation is pure. The old film
and expectation-value observer model are not reinterpreted by this study.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import signal
import sys
import time

import mpmath as mp
import numpy as np
import scipy
from scipy.linalg import expm
from threadpoolctl import threadpool_info, threadpool_limits

from studio.operational_time import density_of, helstrom, peak_memory_bytes
from studio.relational_clock import array_digest, fourier_basis, sha256_file


CYCLES = (0, 1, 1250, 2500, 4109, 5000)
GROUP_A = (-3, -1, 1, 3)
PRECISION = 80
CHI_DENOMINATOR = 10000
TOLERANCE = 2e-12
DENSE_TOLERANCE = 2e-9
ENTROPY_TOLERANCE = 2e-10
TOTAL_SECONDS = 120.
MAX_MEMORY_BYTES = 256 * 1024 ** 2
MAX_RECORD_BYTES = 2 * 1024 ** 2
PREVIOUS_STUDIES = ('relational-clock-001', 'time-ambiguity-001', 'operational-time-001')


def trace_distance(first, second):
    """Density-matrix trace distance, also valid for mixed preparations."""
    difference = np.asarray(first) - np.asarray(second)
    return float(np.abs(np.linalg.eigvalsh((difference + difference.conj().T) / 2)).sum() / 2)


def marginals(density, dimensions=(32, 2)):
    """S-major, E-minor ordering: matrix indices (s,e;s',e')."""
    system, environment = dimensions
    if density.shape != (system * environment, system * environment):
        raise ValueError('Density shape must match the declared tensor factors')
    tensor = density.reshape(system, environment, system, environment)
    return (np.trace(tensor, axis1=1, axis2=3),
            np.trace(tensor, axis1=0, axis2=2))


def operator_marginals(density, dimensions=(32, 2)):
    """Independent sums of subsystem Kraus operators; no tensor reshape."""
    system, environment = dimensions
    system_density = np.zeros((system, system), dtype=np.complex128)
    environment_density = np.zeros((environment, environment), dtype=np.complex128)
    for bra in np.eye(environment):
        operator = np.kron(np.eye(system), bra[None, :])
        system_density += operator @ density @ operator.conj().T
    for bra in np.eye(system):
        operator = np.kron(bra[None, :], np.eye(environment))
        environment_density += operator @ density @ operator.conj().T
    return system_density, environment_density


def partial_transpose(density, dimensions=(32, 2)):
    system, environment = dimensions
    return density.reshape(system, environment, system, environment).transpose(0, 3, 2, 1).reshape(density.shape)


def density_metrics(density):
    eigenvalues = np.linalg.eigvalsh((density + density.conj().T) / 2)
    positive = eigenvalues[eigenvalues > 0]
    return {
        'trace_error': float(abs(np.trace(density) - 1)),
        'hermiticity_error': float(np.max(abs(density - density.conj().T))),
        'positivity_violation': float(max(0., -eigenvalues.min())),
        'purity': float(np.trace(density @ density).real),
        'entropy_bits': float(-np.sum(positive * np.log2(positive))),
    }, eigenvalues


def negativity(density, dimensions=(32, 2)):
    transposed = partial_transpose(density, dimensions)
    values = np.linalg.eigvalsh((transposed + transposed.conj().T) / 2)
    # Equivalent to (trace norm - 1)/2 for a normalized density, avoiding
    # cancellation at separable controls. Normalization is checked separately.
    return float(-values[values < 0].sum()), values


def initial_preparations():
    plus = density_of(np.array([1., 1.]) / math.sqrt(2))
    return {'plus': plus, 'mixed': np.eye(2) / 2,
            'eigenstate': np.diag([1., 0.])}


def group_isometry():
    """Uniform eight-mode vector in each of four orthogonal groups."""
    result = np.zeros((32, 4), dtype=np.complex128)
    for group in range(4):
        result[8 * group:8 * (group + 1), group] = 1 / math.sqrt(8)
    return result


def hamiltonian():
    energies = np.array([r + offset for offset in (0., math.sqrt(2), math.sqrt(3), math.sqrt(5))
                         for r in range(8)])
    interaction = np.repeat(GROUP_A, 8) / CHI_DENOMINATOR
    return np.kron(np.diag(energies), np.eye(2)) + np.kron(np.diag(interaction), np.diag([1., -1.]))


def high_precision_evolution(cycle):
    """Original large-argument phases and independently factored/compressed ones."""
    if type(cycle) is not int or cycle not in CYCLES:
        raise ValueError('Only the six preregistered integer cycles are admitted')
    with mp.workdps(PRECISION):
        offsets = [mp.mpf(0), mp.sqrt(2), mp.sqrt(3), mp.sqrt(5)]
        instant = 2 * mp.pi * cycle
        phi = instant / CHI_DENOMINATOR
        original, isolated, interaction, compressed = [], [], [], []
        for offset, a in zip(offsets, GROUP_A):
            for r in range(8):
                isolated.append(mp.exp(-mp.j * instant * (offset + r)))
                for z in (1, -1):
                    original.append(mp.exp(-mp.j * instant * (offset + r + mp.mpf(a * z) / CHI_DENOMINATOR)))
                    interaction.append(mp.exp(-mp.j * phi * a * z))
            for z in (1, -1):
                compressed.append(mp.exp(-mp.j * (instant * offset + phi * a * z)))
        factored = [isolated[j // 2] * interaction[j] for j in range(64)]
        expanded = [compressed[2 * (j // 16) + j % 2] for j in range(64)]
        gamma_sum = mp.fsum(mp.exp(-2 * mp.j * phi * a) for a in GROUP_A) / 4
        gamma = mp.cos(4 * phi) * mp.cos(2 * phi)
        lam_plus = (1 + abs(gamma)) / 2
        lam_minus = (1 - abs(gamma)) / 2
        entropy = -mp.fsum(x * mp.log(x, 2) for x in (lam_plus, lam_minus) if x > 0)
        iso_group = [mp.exp(-mp.j * instant * offset) for offset in offsets]
        mean = mp.fsum(iso_group) / 4
        iso_distance = mp.sqrt(mp.fsum(abs(value - mean) ** 2 for value in iso_group) / 4)
        text = lambda value: mp.nstr(value, PRECISION)
        reference = {
            'cycle': cycle, 'time': text(instant), 'interaction_phase': text(phi),
            'decimal_digits': PRECISION, 'gamma': text(gamma),
            'gamma_formula_error': text(abs(gamma - gamma_sum)),
            'lambda_plus': text(lam_plus), 'lambda_minus': text(lam_minus),
            'entropy_bits': text(entropy), 'purity': text((1 + abs(gamma) ** 2) / 2),
            'negativity': text(mp.sqrt(lam_plus * lam_minus)),
            'isolated_distance': text(iso_distance),
            'factorization_error': text(max(abs(a - b) for a, b in zip(original, factored))),
            'compression_error': text(max(abs(a - b) for a, b in zip(original, expanded))),
        }
        converted = [np.array([complex(x) for x in values], dtype=np.complex128)
                     for values in (original, isolated, interaction, compressed)]
        for values in converted:
            values.setflags(write=False)
        return (*converted, reference)


def diagonal_evolution(density, phases):
    return phases[:, None] * density * phases.conj()[None, :]


def previous_hashes():
    result = {}
    for name in PREVIOUS_STUDIES:
        folder = Path('artifacts/studies') / name
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                result[str(path)] = sha256_file(path)
    return result


def calculate(report, arrays, truth, upper):
    initial_system = density_of(np.full(32, 1 / math.sqrt(32), dtype=np.complex128))
    initial_group = np.full((4, 4), .25, dtype=np.complex128)
    preparations = initial_preparations()
    W_S = fourier_basis(32)
    W_E = np.array([[1., 1.], [1., -1.]]) / math.sqrt(2)
    W_SE = np.kron(W_S, W_E)
    H = hamiltonian()
    local_H = W_SE @ H @ W_SE.conj().T
    J_S = group_isometry()
    J_SE = np.kron(J_S, np.eye(2))
    arrays.update(initial_system=initial_system, H=H, local_W_S=W_S, local_W_E=W_E,
                  group_isometry=J_S, cycles=np.array(CYCLES))
    report['previous_sha256'] = previous_hashes()
    truth('three_prior_studies_present', all(any(f'artifacts/studies/{name}/' in key
          for key in report['previous_sha256']) for name in PREVIOUS_STUDIES))
    truth('cpu_thread_limit', all(item.get('num_threads', 0) <= 2 for item in threadpool_info()),
          threadpools=threadpool_info())
    upper('local_basis_unitarity', np.max(abs(W_SE.conj().T @ W_SE - np.eye(64))))
    upper('compression_isometry', np.max(abs(J_S.conj().T @ J_S - np.eye(4))))

    for cycle in CYCLES:
        phases, isolated_phases, interaction, group_phases, reference = high_precision_evolution(cycle)
        immutable_before = [array_digest(x) for x in (phases, isolated_phases, interaction, group_phases)]
        label = f'n{cycle}'
        instant = float(reference['time'])
        isolated = diagonal_evolution(initial_system, isolated_phases)
        iso_distance = trace_distance(initial_system, isolated)
        arrays[label + '_isolated_density'] = isolated
        arrays[label + '_original_phases'] = phases
        arrays[label + '_interaction_phases'] = interaction
        arrays[label + '_compressed_phases'] = group_phases
        report['high_precision'][str(cycle)] = reference
        report['isolated'][str(cycle)] = {'distance': iso_distance,
                                         'optimal_success': (1 + iso_distance) / 2}
        for field in ('factorization_error', 'compression_error', 'gamma_formula_error'):
            upper(label + '_80_digit_' + field, float(reference[field]), 1e-60)
        upper(label + '_isolated_independent_distance', abs(iso_distance - float(reference['isolated_distance'])))
        if cycle == 4109:
            upper('previous_near_return_reproduced', abs(iso_distance - .017388884873856538))
        dense_U = expm(-1j * instant * H)
        local_dense_U = expm(-1j * instant * local_H)
        clock_cases = {}

        for preparation, environment0 in preparations.items():
            prefix = label + '_' + preparation
            joint0 = np.kron(initial_system, environment0)
            joint = diagonal_evolution(joint0, phases)
            system, environment = marginals(joint)
            block_system, block_environment = operator_marginals(joint)
            reduced_group = diagonal_evolution(np.kron(initial_group, environment0), group_phases)
            matrices = {'S': system, 'E': environment, 'SE': joint}
            initials = {'S': initial_system, 'E': environment0, 'SE': joint0}
            local_bases = {'S': W_S, 'E': W_E, 'SE': W_SE}
            compressions = {'S': J_S, 'E': np.eye(2), 'SE': J_SE}
            result = {'return': {}, 'density': {}}
            report['cases'][prefix] = result
            clock_cases[preparation] = system
            upper(prefix + '_operator_partial_trace_S', np.max(abs(system - block_system)))
            upper(prefix + '_operator_partial_trace_E', np.max(abs(environment - block_environment)))
            upper(prefix + '_compressed_full_agreement', np.max(abs(joint - J_SE @ reduced_group @ J_SE.conj().T)))
            upper(prefix + '_dense_exponential', trace_distance(joint, dense_U @ joint0 @ dense_U.conj().T), DENSE_TOLERANCE)
            local0 = W_SE @ joint0 @ W_SE.conj().T
            local_joint = W_SE @ joint @ W_SE.conj().T
            upper(prefix + '_local_dense_exponential', trace_distance(local_joint, local_dense_U @ local0 @ local_dense_U.conj().T), DENSE_TOLERANCE)
            local_system, local_environment = marginals(local_joint)
            upper(prefix + '_local_partial_trace_S', np.max(abs(local_system - W_S @ system @ W_S.conj().T)))
            upper(prefix + '_local_partial_trace_E', np.max(abs(local_environment - W_E @ environment @ W_E.conj().T)))
            for register, density in matrices.items():
                metrics, eigenvalues = density_metrics(density)
                quality, effect, difference_eigenvalues = helstrom(initials[register], density)
                result['density'][register] = metrics
                result['return'][register] = quality
                arrays[prefix + '_' + register + '_density'] = density
                arrays[prefix + '_' + register + '_eigenvalues'] = eigenvalues
                arrays[prefix + '_' + register + '_difference_eigenvalues'] = difference_eigenvalues
                isometry = compressions[register]
                compressed_effect = isometry.conj().T @ effect @ isometry
                arrays[prefix + '_' + register + '_effect0_compressed'] = compressed_effect
                upper(prefix + '_' + register + '_effect_support', np.max(abs(effect - isometry @ compressed_effect @ isometry.conj().T)))
                for field in ('trace_error', 'hermiticity_error', 'positivity_violation'):
                    upper(prefix + '_' + register + '_' + field, metrics[field])
                for field in ('success_error', 'positivity_violation', 'completeness_error',
                              'idempotence_error', 'hermiticity_error'):
                    upper(prefix + '_' + register + '_helstrom_' + field, quality[field])
                W = local_bases[register]
                rotated0 = W @ initials[register] @ W.conj().T
                rotated1 = W @ density @ W.conj().T
                rotated_quality, _, _ = helstrom(rotated0, rotated1)
                rotated_metrics, _ = density_metrics(rotated1)
                rotated_effect = W @ effect @ W.conj().T
                measured = float((np.trace(rotated_effect @ rotated0) +
                                  np.trace((np.eye(len(W)) - rotated_effect) @ rotated1)).real / 2)
                for field in ('distance', 'success', 'optimal_success'):
                    upper(prefix + '_' + register + '_local_covariance_' + field,
                          abs(rotated_quality[field] - quality[field]), DENSE_TOLERANCE)
                upper(prefix + '_' + register + '_transformed_measurement',
                      abs(measured - quality['optimal_success']), DENSE_TOLERANCE)
                for field in ('purity', 'entropy_bits'):
                    upper(prefix + '_' + register + '_local_covariance_' + field,
                          abs(rotated_metrics[field] - metrics[field]), DENSE_TOLERANCE)
            value, pt_values = negativity(joint)
            local_value, _ = negativity(local_joint)
            arrays[prefix + '_partial_transpose_eigenvalues'] = pt_values
            result['negativity'] = value
            result['same_time_clock_disturbance'] = trace_distance(system, isolated)
            upper(prefix + '_local_covariance_negativity', abs(value - local_value), DENSE_TOLERANCE)
            for register in ('S', 'E'):
                slack = result['return']['SE']['distance'] - result['return'][register]['distance']
                truth(prefix + '_' + register + '_partial_trace_contraction', slack >= -TOLERANCE,
                      slack=slack, minimum=-TOLERANCE)
            block_error = max(np.max(abs(system[8 * g:8 * (g + 1), 8 * g:8 * (g + 1)] -
                                        isolated[8 * g:8 * (g + 1), 8 * g:8 * (g + 1)]))
                              for g in range(4))
            upper(prefix + '_every_within_group_block_unchanged', block_error)
            if preparation in ('plus', 'mixed'):
                phase_a = np.repeat(GROUP_A, 8)
                analytic_system = isolated * np.cos(float(reference['interaction_phase']) *
                                                     (phase_a[:, None] - phase_a[None, :]))
                upper(prefix + '_analytic_clock_marginal', np.max(abs(system - analytic_system)))
            if preparation == 'plus':
                gamma = float(reference['gamma'])
                analytic_environment = np.array([[1., gamma], [gamma, 1.]]) / 2
                upper(prefix + '_analytic_environment_marginal', np.max(abs(environment - analytic_environment)))
                predicted_eigenvalues = np.array([float(reference['lambda_minus']), float(reference['lambda_plus'])])
                for register in ('S', 'E'):
                    eigenvalues = np.linalg.eigvalsh(matrices[register])
                    expected = np.r_[np.zeros(len(eigenvalues) - 2), predicted_eigenvalues]
                    upper(prefix + '_' + register + '_Schmidt_eigenvalues', np.max(abs(eigenvalues - expected)))
                    upper(prefix + '_' + register + '_analytic_purity', abs(result['density'][register]['purity'] - float(reference['purity'])))
                    upper(prefix + '_' + register + '_analytic_entropy', abs(result['density'][register]['entropy_bits'] - float(reference['entropy_bits'])), ENTROPY_TOLERANCE)
                upper(prefix + '_analytic_negativity', abs(value - float(reference['negativity'])))
                result['entanglement_entropy_bits'] = result['density']['S']['entropy_bits']
                if cycle == 1:
                    disturbance = trace_distance(joint, np.kron(isolated, environment0))
                    result['same_time_joint_disturbance'] = disturbance
                    truth('early_joint_perturbation_below_0_002', disturbance < .002,
                          value=disturbance, maximum_exclusive=.002)
                if cycle == 4109:
                    truth('near_return_isolation_failure_distance_gate', result['return']['S']['distance'] > .5,
                          value=result['return']['S']['distance'], minimum_exclusive=.5)
                    truth('near_return_isolation_failure_entropy_gate', result['entanglement_entropy_bits'] > .5,
                          value=result['entanglement_entropy_bits'], minimum_exclusive=.5)
            elif preparation == 'mixed':
                plus_system = diagonal_evolution(initial_system, phases[0::2])
                minus_system = diagonal_evolution(initial_system, phases[1::2])
                separable = (np.kron(plus_system, np.diag([1., 0.])) +
                             np.kron(minus_system, np.diag([0., 1.]))) / 2
                upper(prefix + '_explicit_separable_decomposition', np.max(abs(joint - separable)))
                upper(prefix + '_separable_negativity', value)
                upper(prefix + '_environment_unchanged', trace_distance(environment, environment0))
                result['entanglement_status'] = 'separable by explicit two-term product-state decomposition'
            else:
                upper(prefix + '_product_state', np.max(abs(joint - np.kron(system, environment))))
                upper(prefix + '_product_negativity', value)
                upper(prefix + '_environment_unchanged', trace_distance(environment, environment0))
                upper(prefix + '_clock_purity_one', abs(result['density']['S']['purity'] - 1))
                result['entanglement_status'] = 'product throughout; coherent clock detuning only'
        upper(label + '_plus_and_mixed_clock_marginals_identical',
              np.max(abs(clock_cases['plus'] - clock_cases['mixed'])))
        truth(label + '_phase_inputs_immutable', immutable_before ==
              [array_digest(x) for x in (phases, isolated_phases, interaction, group_phases)])
        primary = report['cases'][label + '_plus']
        if cycle == 1250:
            upper('n1250_exact_one_bit', abs(primary['entanglement_entropy_bits'] - 1), ENTROPY_TOLERANCE)
            upper('n1250_exact_half_purity', abs(primary['density']['S']['purity'] - .5))
            upper('n1250_exact_half_negativity', abs(primary['negativity'] - .5))
        elif cycle == 2500:
            # sin(pi*a/2) is exactly (1,-1,1,-1) for the four odd integers.
            interaction_control = -1j * np.kron(np.repeat([1., -1., 1., -1.], 8), [1., -1.])
            upper('n2500_exact_interaction_factorization', np.max(abs(interaction - interaction_control)))
            upper('n2500_disentangled', primary['negativity'])
            upper('n2500_environment_orthogonal', abs(primary['return']['E']['distance'] - 1))
            upper('n2500_joint_orthogonal', abs(primary['return']['SE']['distance'] - 1))
            minus = density_of(np.array([1., -1.]) / math.sqrt(2))
            upper('n2500_environment_is_minus', np.max(abs(arrays[label + '_plus_E_density'] - minus)))
        elif cycle == 5000:
            upper('n5000_exact_interaction_minus_identity', np.max(abs(interaction + 1)))
            for preparation, environment0 in preparations.items():
                prefix = label + '_' + preparation
                upper(prefix + '_isolated_product_restored_at_same_time',
                      trace_distance(arrays[prefix + '_SE_density'], np.kron(isolated, environment0)))
            upper('n5000_environment_restored', primary['return']['E']['distance'])
            upper('n5000_disentangled', primary['negativity'])
    truth('previous_study_files_unchanged', report['previous_sha256'] == previous_hashes())
    report['calculation_completed'] = True


def run_protocol(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    sources = ('studio/relational_clock.py', 'studio/operational_time.py',
               'studio/clock_environment.py', 'studio/tests/test_clock_environment.py',
               'research/CLOCK-ENVIRONMENT-PROPOSAL.md')
    captured = {}
    for name in sources:
        target = output / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(name, target)
        captured[name] = sha256_file(target)
    began, cpu_began = time.monotonic(), time.process_time()
    arrays, checks = {}, []
    report = {
        'schema': 'clock-environment-1', 'started_utc': datetime.now(timezone.utc).isoformat(),
        'source_sha256': captured, 'cycles': list(CYCLES), 'chi': '1/10000',
        'group_A': list(GROUP_A), 'dimensions': [32, 2], 'hbar': 1,
        'tensor_order': 'system-major, environment-minor',
        'scope': 'two known snapshots; equal priors; one copy; no external cycle count or correlated record; no external purification',
        'versions': {'python': sys.version.split()[0], 'numpy': np.__version__,
                     'scipy': scipy.__version__, 'mpmath': mp.__version__},
        'checks': checks, 'cases': {}, 'isolated': {}, 'high_precision': {},
        'calculation_completed': False,
    }

    def truth(name, passed, **details):
        checks.append({'name': name, 'passed': bool(passed), **details})

    def upper(name, value, limit=TOLERANCE):
        value = float(value)
        truth(name, math.isfinite(value) and value <= limit, value=value, maximum=limit)

    def deadline(_signal, _frame):
        raise TimeoutError('The fixed 120-second calculation budget expired')

    old_handler = signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, TOTAL_SECONDS)
    try:
        with threadpool_limits(limits=2):
            calculate(report, arrays, truth, upper)
    except Exception as error:
        report['exception'] = {'type': type(error).__name__, 'message': str(error)}
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
    storage_check = {'name': 'retained_record_size', 'value': 0,
                     'maximum': MAX_RECORD_BYTES, 'passed': True}
    checks.append(storage_check)
    manifest_path = output / 'manifest.json'
    for _ in range(5):
        report['all_passed'] = bool(report['calculation_completed'] and all(row['passed'] for row in checks))
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        members = {str(path.relative_to(output)): {'bytes': path.stat().st_size, 'sha256': sha256_file(path)}
                   for path in sorted(output.rglob('*')) if path.is_file() and path != manifest_path}
        manifest_path.write_text(json.dumps({'files': members}, indent=2) + '\n')
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
                      'failures': [row for row in checks if not row['passed']]}), flush=True)
    if not report['all_passed']:
        raise RuntimeError('Clock-environment admission failed; its complete record is retained')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='artifacts/studies/clock-environment-001')
    run_protocol(parser.parse_args().output)
