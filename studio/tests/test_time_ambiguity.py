"""Operationally distinct local sensitivity and distant candidate ambiguity."""
import math

import numpy as np
import pytest

from studio.relational_clock import four_level_clock, fourier_basis, complete_observer
from studio.time_ambiguity import (
    DenseReference, ambiguity_labels, analytic_discrepancy, clock_cases,
    coefficients, local_resolution, readout_from_states,
)


def test_locally_sharper_observer_can_keep_a_distant_exact_alias():
    clock, observers = clock_cases()['four']
    matched = observers['matched']
    connected = observers['connected']
    assert coefficients(clock, matched)['C'] > coefficients(clock, connected)['C']
    assert analytic_discrepancy(clock, matched, [2 * np.pi])[0] < 1e-24
    assert analytic_discrepancy(clock, connected, [2 * np.pi])[0] > .2
    assert math.sqrt(analytic_discrepancy(clock, observers['disconnected'], [.2])[0]) > .02


def test_positive_qfi_does_not_preclude_an_exact_global_alias():
    clock = four_level_clock(True)
    observer = complete_observer(4)
    reference = DenseReference(clock, fourier_basis(4))
    np.testing.assert_allclose(reference.qfi, 5., atol=1e-13)
    assert reference.sld_residual < 1e-13
    assert analytic_discrepancy(clock, observer, [2 * np.pi])[0] < 1e-24


def test_midpoint_is_an_actual_nonzero_ambiguity_witness():
    clock, observers = clock_cases()['four']
    for name, cycle in [('connected', 29), ('complete', 70)]:
        readings = readout_from_states(observers[name], clock.states([0., 2 * np.pi * cycle]))
        midpoint = readings.mean(axis=0)
        errors = np.linalg.norm(readings - midpoint, axis=1)
        assert np.all(errors > .001)
        assert np.all(errors < .01)
        np.testing.assert_allclose(errors[0], errors[1], atol=1e-14)


def test_disjoint_balls_have_a_positive_triangle_gap():
    clock, observers = clock_cases()['four']
    distance = math.sqrt(analytic_discrepancy(clock, observers['connected'], [2 * np.pi])[0])
    margin, labels = ambiguity_labels([distance], .01)
    assert margin[0] > .4
    assert labels[0] == 1


def test_exact_threshold_is_retained_as_borderline_not_forced_into_a_class():
    margins, labels = ambiguity_labels([.02 - 1e-6, .02, .02 + 1e-6], .01)
    np.testing.assert_array_equal(labels, [-1, 0, 1])
    assert margins[1] == 0


def test_dense_starting_time_changes_observable_phase_but_not_separation():
    clock, observers = clock_cases()['four']
    observer = observers['connected']
    reference = DenseReference(clock, fourier_basis(4))
    differences = []
    for start in (0., .37, 9.1):
        differences.append(reference.selected(reference.at(start + .2) - reference.at(start), observer))
    assert np.max(abs(differences[0] - differences[1])) > .001
    norms = [np.linalg.norm(value) for value in differences]
    np.testing.assert_allclose(norms, norms[0], atol=1e-13)


def test_taylor_sandwich_uses_dense_readouts_instead_of_a_fitted_slope():
    clock, observers = clock_cases()['four']
    observer = observers['complete']
    constants = coefficients(clock, observer)
    reference = DenseReference(clock, fourier_basis(4))
    for delta in (.001, .1, .5):
        change = reference.selected(reference.at(.37 + delta) - reference.at(.37), observer)
        quotient = float(np.vdot(change, change).real) / delta ** 2
        assert quotient <= constants['C'] + 1e-11
        assert quotient >= constants['C'] - constants['K'] * delta ** 2 / 12 - 1e-11


def test_local_threshold_is_scoped_to_a_monotone_bracket_and_stationary_is_unresolved():
    clock, observers = clock_cases()['four']
    threshold = local_resolution(clock, observers['disconnected'], .01)
    assert threshold['resolved']
    expected = 2 * math.asin(2 * .01 * math.sqrt(2))
    np.testing.assert_allclose(threshold['separation'], expected, atol=1e-13)
    stationary, stationary_observers = clock_cases()['stationary']
    assert not local_resolution(stationary, stationary_observers['complete'], .01)['resolved']
    assert not local_resolution(clock, observers['disconnected'], 1.)['resolved']


@pytest.mark.parametrize('eta', [0., -.01, float('nan'), float('inf')])
def test_invalid_uncertainty_does_not_create_a_fake_local_resolution(eta):
    clock, observers = clock_cases()['four']
    with pytest.raises(ValueError):
        local_resolution(clock, observers['complete'], eta)
