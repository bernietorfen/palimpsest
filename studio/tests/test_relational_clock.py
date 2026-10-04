"""Independent physical and graph controls for the finite phase instrument."""
import math

import numpy as np
import pytest

from studio.relational_clock import (
    Observer, PhaseClock, bridge_gap, bridge_observer, complete_observer,
    four_level_clock, fourier_basis, operator_reference,
)


def test_local_return_can_hide_a_globally_distinguishable_state():
    clock = four_level_clock()
    state = clock.states([2 * np.pi])
    disconnected = bridge_observer(0.)
    assert disconnected.discrepancy(disconnected.changes(clock, state))[0] < 1e-24
    reference = operator_reference(clock, 2 * np.pi, complete_observer(4).edges)
    assert reference['distance'] > .9
    connected = bridge_observer(1.)
    assert connected.discrepancy(connected.changes(clock, state))[0] > .2


def test_commensurate_control_has_a_full_return_and_stationary_control_never_moves():
    clock = four_level_clock(commensurate=True)
    reference = operator_reference(clock, 2 * np.pi, complete_observer(4).edges)
    assert reference['distance'] < 1e-12
    stationary = PhaseClock(np.zeros(4), np.full(4, .25))
    states = stationary.states([0., 1., 100.])
    assert np.array_equal(states[0], states[2])


def test_dense_operator_reference_preserves_imaginary_coherence_sign():
    clock = PhaseClock(np.array([0., 1.]), np.array([.5, .5]))
    reference = operator_reference(clock, np.pi / 2, np.array([[0, 1]]))
    np.testing.assert_allclose(reference['coherences'], [0. + .5j], atol=1e-14)
    np.testing.assert_allclose(reference['distance'], math.sqrt(.5), atol=1e-14)


def test_basis_change_and_nonuniform_populations_preserve_trace_distance():
    clock = PhaseClock(np.array([0., .7, math.sqrt(2), 3.]), np.array([.1, .2, .3, .4]))
    observer = complete_observer(4)
    for instant in (0., .2, 2 * np.pi, 17.):
        ordinary = operator_reference(clock, instant, observer.edges)
        rotated = operator_reference(clock, instant, observer.edges, fourier_basis(4))
        np.testing.assert_allclose(rotated['distance'], ordinary['distance'], atol=2e-13)
        np.testing.assert_allclose(rotated['coherences'], ordinary['coherences'], atol=2e-13)
        state = clock.states([instant])
        np.testing.assert_allclose(observer.discrepancy(observer.changes(clock, state)), ordinary['distance'] ** 2, atol=2e-13)


def test_general_population_metric_has_a_valid_bound_and_disconnection_has_none():
    clock = PhaseClock(np.array([0., .9, math.sqrt(3), 2.4]), np.array([.05, .15, .3, .5]))
    states = clock.states(np.linspace(0, 30, 79))
    distance_squared = clock.return_distance_squared(states)
    observer = Observer(4, np.array([[0, 1], [1, 2], [2, 3]]), np.array([.2, 1.7, .4]))
    gap = observer.spectral_gap(clock.populations)
    assert gap > 0
    assert np.min(observer.discrepancy(observer.changes(clock, states)) / gap - distance_squared) > -1e-12
    disconnected = Observer(4, observer.edges, np.array([.2, 0., .4]))
    assert disconnected.spectral_gap(clock.populations) == 0
    assert disconnected.components() == ((0, 1), (2, 3))


def test_weak_bridge_formula_and_noise_bound_do_not_claim_a_false_precise_return():
    clock = four_level_clock()
    instant = 2 * np.pi
    state = clock.states([instant])
    actual = operator_reference(clock, instant, complete_observer(4).edges)['distance']
    for emphasis in (1e-6, 1e-4, .01, 1.):
        observer = bridge_observer(emphasis)
        gap = observer.spectral_gap(clock.populations)
        np.testing.assert_allclose(gap, bridge_gap(emphasis), atol=1e-14)
        changes = observer.changes(clock, state)[0]
        error = -changes
        measured = changes + error
        eta = math.sqrt(float(observer.discrepancy(error)))
        bound = (math.sqrt(float(observer.discrepancy(measured))) + eta) / math.sqrt(gap)
        assert observer.discrepancy(measured) == 0
        assert bound >= actual - 2e-11
        assert bound > .9


def test_relabeling_observation_edges_preserves_actual_readouts():
    clock = PhaseClock(np.array([0., .9, 1.7, 2.5]), np.array([.1, .2, .3, .4]))
    observer = Observer(4, np.array([[0, 1], [0, 3], [1, 2]]), np.array([.3, .7, 1.2]))
    times = np.array([0., .2, 1., 5.])
    original = observer.discrepancy(observer.changes(clock, clock.states(times)))
    permutation = np.array([2, 0, 3, 1])
    inverse = np.argsort(permutation)
    relabeled = PhaseClock(clock.energies[permutation], clock.populations[permutation])
    edges = np.sort(inverse[observer.edges], axis=1)
    transformed = Observer(4, edges, observer.emphasis)
    observed = transformed.discrepancy(transformed.changes(relabeled, relabeled.states(times)))
    np.testing.assert_allclose(observed, original, atol=2e-14)


def test_common_energy_shift_is_unobservable_to_density_readouts():
    clock = four_level_clock()
    shifted = PhaseClock(clock.energies + 3.75, clock.populations)
    observer = complete_observer(4)
    times = np.array([0., .2, 2 * np.pi, 19.])
    np.testing.assert_allclose(observer.coherences(clock.states(times)), observer.coherences(shifted.states(times)), atol=1e-13)


def test_observer_cannot_mutate_the_underlying_state():
    clock = four_level_clock()
    states = clock.states([0., 2 * np.pi])
    before = states.tobytes()
    noisy = bridge_observer(1.).changes(clock, states)
    noisy[:] = 0
    assert states.tobytes() == before
    with pytest.raises(ValueError):
        states[0, 0] = 3


@pytest.mark.parametrize('populations', [[0., .5, .25, .25], [.1, .2, .3, .3]])
def test_zero_support_and_unnormalized_populations_are_not_silently_admitted(populations):
    with pytest.raises(ValueError):
        PhaseClock(np.arange(4), np.array(populations))


@pytest.mark.parametrize('edges,emphasis', [
    ([[0, 1], [0, 1]], [1., 1.]), ([[0, 4]], [1.]),
    ([[1, 1]], [1.]), ([[0, 1]], [-1.]), ([[0., 1.]], [1.]),
])
def test_malformed_observation_graphs_are_rejected(edges, emphasis):
    with pytest.raises(ValueError):
        Observer(4, np.array(edges), np.array(emphasis))
