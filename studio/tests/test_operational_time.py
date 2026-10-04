"""Exact arithmetic, observable restrictions and achieved discrimination."""
from copy import deepcopy
import json
import math

import mpmath as mp
import numpy as np
import pytest

import studio.operational_time as operational_time
from studio.operational_time import (
    SearchLimit, collision_certificate, density_of, first_collision, group_projectors,
    helstrom, integer_box, restricted_representation, verify_certificate,
)
from studio.relational_clock import fourier_basis


def test_integer_bins_match_independent_high_precision_fractional_parts():
    with mp.workdps(80):
        for k in (0, 1, 169, 4096, 1048575, 2097152):
            expected = tuple(int(mp.floor(128 * mp.frac(k * mp.sqrt(s)))) for s in (2, 3, 5))
            assert integer_box(k, 128) == expected


def test_finite_collision_has_an_independently_checkable_integer_certificate():
    witness = first_collision(q=8)
    assert 0 < witness['n'] <= 8 ** 3
    assert witness['candidate_count'] <= 8 ** 3 + 1
    assert verify_certificate(witness)
    with mp.workdps(80):
        for s, m in zip((2, 3, 5), witness['m']):
            assert abs(witness['n'] * mp.sqrt(s) - m) < mp.mpf(1) / 8
    for key in ('f', 'h'):
        changed = deepcopy(witness)
        changed['roots'][0][key] += 1
        assert not verify_certificate(changed)
    changed = deepcopy(witness)
    changed['m'][0] += 1
    assert not verify_certificate(changed)
    changed = deepcopy(witness)
    changed['roots'].append(changed['roots'][0])
    assert not verify_certificate(changed)


def test_noncollision_cannot_be_promoted_to_a_recurrence_certificate():
    witness = collision_certificate(1, 0, 128)
    assert not verify_certificate(witness)


def test_search_deadline_reports_progress_without_enlarging_the_search():
    with pytest.raises(SearchLimit) as caught:
        first_collision(q=8, seconds=0)
    assert caught.value.candidate_count == 0
    assert caught.value.elapsed >= 0


def test_failed_calculation_keeps_sources_exception_gates_and_manifest(tmp_path, monkeypatch):
    def stop_search():
        raise SearchLimit(0, 0.)

    monkeypatch.setattr(operational_time, 'first_collision', stop_search)
    output = tmp_path / 'failed-record'
    with pytest.raises(RuntimeError, match='complete record is retained'):
        operational_time.run_protocol(output)
    report = json.loads((output / 'report.json').read_text())
    assert not report['all_passed']
    assert report['exception']['type'] == 'SearchLimit'
    assert report['exception']['candidate_count'] == 0
    assert any(not check['passed'] for check in report['checks'])
    assert (output / 'source/studio/operational_time.py').is_file()
    assert 'report.json' in json.loads((output / 'manifest.json').read_text())['files']


@pytest.mark.parametrize('angle', [0., math.pi / 4, math.pi / 2])
def test_actual_helstrom_effect_attains_known_two_level_discrimination(angle):
    first = np.array([1., 0.], dtype=np.complex128)
    second = np.array([math.cos(angle), math.sin(angle)], dtype=np.complex128)
    result, effect, eigenvalues = helstrom(density_of(first), density_of(second))
    np.testing.assert_allclose(result['distance'], math.sin(angle), atol=1e-14)
    np.testing.assert_allclose(result['success'], (1 + math.sin(angle)) / 2, atol=1e-14)
    assert result['success_error'] < 1e-14
    assert result['positivity_violation'] < 1e-14
    np.testing.assert_allclose(effect @ effect, effect, atol=1e-14)
    assert abs(eigenvalues.sum()) < 1e-14


def test_restricted_invariance_also_holds_for_a_mixed_state():
    plus = np.full(4, .5, dtype=np.complex128)
    rho = .7 * density_of(plus) + .3 * np.eye(4) / 4
    U = np.diag([1., 1., 1j, 1j])
    later = U @ rho @ U.conj().T
    P = group_projectors(2, 2)
    np.testing.assert_allclose(restricted_representation(rho, P),
                               restricted_representation(later, P), atol=1e-14)
    assert helstrom(rho, later)[0]['success'] > .7


def test_arbitrary_preprocessing_invalidates_a_diagonal_observation_restriction():
    plus = np.array([1., 1.]) / math.sqrt(2)
    minus = np.array([1., -1.]) / math.sqrt(2)
    rho0, rho1 = density_of(plus), density_of(minus)
    P = group_projectors(2, 1)
    np.testing.assert_allclose(restricted_representation(rho0, P), restricted_representation(rho1, P))
    H = np.array([[1., 1.], [1., -1.]]) / math.sqrt(2)
    effective = H.conj().T @ P[0] @ H
    assert np.max(abs(effective @ P[0] - P[0] @ effective)) > .4
    assert np.trace(effective @ rho0).real > 1 - 1e-14
    assert abs(np.trace(effective @ rho1)) < 1e-14


def test_basis_change_must_transform_the_allowed_algebra_together_with_the_state():
    first = np.full(4, .5, dtype=np.complex128)
    second = first * np.array([1., 1., 1j, 1j])
    rho0, rho1 = density_of(first), density_of(second)
    P, F = group_projectors(2, 2), fourier_basis(4)
    transformed_P = [F @ p @ F.conj().T for p in P]
    transformed0, transformed1 = F @ rho0 @ F.conj().T, F @ rho1 @ F.conj().T
    assert helstrom(transformed0, transformed1)[0]['success'] == pytest.approx(helstrom(rho0, rho1)[0]['success'])
    np.testing.assert_allclose(restricted_representation(transformed0, transformed_P),
                               restricted_representation(transformed1, transformed_P), atol=1e-14)
