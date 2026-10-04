"""Tensor ordering, separable controls and retained failure evidence."""
import json
import math

import numpy as np
import pytest

import studio.clock_environment as study
from studio.operational_time import density_of


def test_partial_traces_have_the_declared_unequal_tensor_dimensions():
    system = density_of(np.array([1., 2j, -3.]) / math.sqrt(14))
    environment = np.array([[.7, .1j], [-.1j, .3]])
    product = np.kron(system, environment)
    for route in (study.marginals, study.operator_marginals):
        first, second = route(product, (3, 2))
        np.testing.assert_allclose(first, system, atol=1e-14)
        np.testing.assert_allclose(second, environment, atol=1e-14)
    with pytest.raises(ValueError, match='tensor factors'):
        study.marginals(product, (2, 2))


def test_identical_marginals_do_not_distinguish_bell_entanglement_from_classical_mixture():
    bell = density_of(np.array([1., 0., 0., 1.]) / math.sqrt(2))
    classical = np.diag([.5, 0., 0., .5])
    for route in (study.marginals, study.operator_marginals):
        for first, second in zip(route(bell, (2, 2)), route(classical, (2, 2))):
            np.testing.assert_allclose(first, second, atol=1e-14)
    assert study.negativity(bell, (2, 2))[0] == pytest.approx(.5)
    assert study.negativity(classical, (2, 2))[0] == pytest.approx(0.)
    np.testing.assert_allclose(study.partial_transpose(study.partial_transpose(bell, (2, 2)), (2, 2)), bell)


def test_mixed_state_trace_distance_cannot_use_pure_overlap_shortcut():
    pure = np.diag([1., 0.])
    mixed = np.eye(2) / 2
    assert study.trace_distance(pure, mixed) == pytest.approx(.5)
    assert abs(study.trace_distance(pure, mixed) - math.sqrt(1 - np.trace(pure @ mixed))) > .2


def test_maximally_mixed_and_coherent_environments_have_the_same_clock_but_different_entanglement():
    phases, *_ = study.high_precision_evolution(1250)
    initial = np.full((32, 32), 1 / 32, dtype=np.complex128)
    preparations = study.initial_preparations()
    primary = study.diagonal_evolution(np.kron(initial, preparations['plus']), phases)
    separable = study.diagonal_evolution(np.kron(initial, preparations['mixed']), phases)
    primary_system, _ = study.marginals(primary)
    separable_system, _ = study.marginals(separable)
    np.testing.assert_allclose(primary_system, separable_system, atol=1e-14)
    assert study.negativity(primary)[0] == pytest.approx(.5)
    assert study.negativity(separable)[0] < 1e-14


def test_disentanglement_does_not_restore_the_environment_preparation():
    phases, *_ = study.high_precision_evolution(2500)
    initial = np.full((32, 32), 1 / 32, dtype=np.complex128)
    plus = study.initial_preparations()['plus']
    later = study.diagonal_evolution(np.kron(initial, plus), phases)
    system, environment = study.marginals(later)
    np.testing.assert_allclose(later, np.kron(system, environment), atol=1e-14)
    assert study.negativity(later)[0] < 1e-14
    assert study.trace_distance(environment, plus) == pytest.approx(1.)


def test_interaction_return_is_not_an_assertion_of_full_clock_return():
    phases, isolated_phases, interaction, _, _ = study.high_precision_evolution(5000)
    np.testing.assert_allclose(interaction, -np.ones(64), atol=1e-14)
    initial = np.full((32, 32), 1 / 32, dtype=np.complex128)
    plus = study.initial_preparations()['plus']
    later = study.diagonal_evolution(np.kron(initial, plus), phases)
    isolated = study.diagonal_evolution(initial, isolated_phases)
    np.testing.assert_allclose(later, np.kron(isolated, plus), atol=1e-14)
    assert study.trace_distance(isolated, initial) > .05


def test_eigenstate_environment_is_product_even_when_the_clock_changes():
    phases, isolated_phases, *_ = study.high_precision_evolution(4109)
    initial = np.full((32, 32), 1 / 32, dtype=np.complex128)
    eigenstate = study.initial_preparations()['eigenstate']
    joint = study.diagonal_evolution(np.kron(initial, eigenstate), phases)
    system, environment = study.marginals(joint)
    np.testing.assert_allclose(joint, np.kron(system, environment), atol=1e-14)
    assert study.negativity(joint)[0] < 1e-14
    isolated = study.diagonal_evolution(initial, isolated_phases)
    assert study.trace_distance(system, isolated) > .1


def test_dense_local_basis_propagation_preserves_the_physical_tensor_split():
    phases, _, _, _, reference = study.high_precision_evolution(1)
    H = study.hamiltonian()
    W_S = study.fourier_basis(32)
    W_E = np.array([[1., 1.], [1., -1.]]) / math.sqrt(2)
    W = np.kron(W_S, W_E)
    initial = np.kron(np.full((32, 32), 1 / 32), study.initial_preparations()['plus'])
    direct = study.diagonal_evolution(initial, phases)
    U = study.expm(-1j * float(reference['time']) * (W @ H @ W.conj().T))
    propagated = U @ W @ initial @ W.conj().T @ U.conj().T
    expected = W @ direct @ W.conj().T
    assert study.trace_distance(propagated, expected) < 1e-12
    system, environment = study.marginals(direct)
    rotated_system, rotated_environment = study.marginals(propagated)
    np.testing.assert_allclose(rotated_system, W_S @ system @ W_S.conj().T, atol=1e-12)
    np.testing.assert_allclose(rotated_environment, W_E @ environment @ W_E.conj().T, atol=1e-12)


def test_scope_rejects_extra_cycles_and_preserves_phase_arrays():
    with pytest.raises(ValueError, match='six preregistered'):
        study.high_precision_evolution(2)
    phases, isolated, interaction, groups, _ = study.high_precision_evolution(0)
    for array in (phases, isolated, interaction, groups):
        assert not array.flags.writeable


def test_failed_calculation_keeps_exception_sources_and_manifest(tmp_path, monkeypatch):
    def fail(_cycle):
        raise ArithmeticError('deliberate reference failure')

    monkeypatch.setattr(study, 'high_precision_evolution', fail)
    output = tmp_path / 'failure'
    with pytest.raises(RuntimeError, match='complete record is retained'):
        study.run_protocol(output)
    report = json.loads((output / 'report.json').read_text())
    assert not report['all_passed']
    assert not report['calculation_completed']
    assert report['exception']['type'] == 'ArithmeticError'
    assert any(not check['passed'] for check in report['checks'])
    assert (output / 'source/studio/clock_environment.py').is_file()
    assert 'report.json' in json.loads((output / 'manifest.json').read_text())['files']
