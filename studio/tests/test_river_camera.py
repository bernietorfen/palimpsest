"""Contracts whose failure would invalidate expensive film renders. RunPod only."""
import math
import numpy as np
import pytest
from studio.river_cinematography import SHOTS, camera_at, model_time, observation_light, reference_focus
from studio.river_geometry import ENERGIES, phases, validate_embedding


def test_camera_score_covers_the_composition_without_gaps():
    assert SHOTS[0].start == 0 and SHOTS[-1].end == 240
    assert all(a.end == b.start for a, b in zip(SHOTS, SHOTS[1:]))
    assert all(shot.end > shot.start for shot in SHOTS)


@pytest.mark.parametrize('boundary', [8,101,106,112,119.6,210,222,228])
def test_continuous_moves_have_no_position_target_or_lens_pop(boundary):
    before, after = camera_at(boundary-1e-7), camera_at(boundary)
    np.testing.assert_allclose(before['location'],after['location'],atol=1e-6,rtol=0)
    np.testing.assert_allclose(before['target'],after['target'],atol=1e-6,rtol=0)
    assert abs(before['lens']-after['lens']) < 1e-6
    assert abs(before['aperture']-after['aperture']) < 1e-6


@pytest.mark.parametrize('seconds', [104,208])
def test_reference_visits_match_the_opening_observer(seconds):
    initial, returned = camera_at(0), camera_at(seconds)
    for key in ('location','target','lens','aperture'):
        np.testing.assert_allclose(initial[key],returned[key],atol=1e-12,rtol=0)
    assert reference_focus(seconds) == reference_focus(0) == 1
    assert observation_light(seconds) == observation_light(0) == 1
    assert model_time(seconds) == seconds/104*2*math.pi


def test_the_final_observer_rests_while_the_state_changes():
    first, last = camera_at(228), camera_at(240)
    for key in ('location','target','lens','aperture'):
        np.testing.assert_array_equal(first[key],last[key])
    assert np.max(np.abs(phases(model_time(228))-phases(model_time(240)))) > .5


def test_blackout_is_an_observation_change_with_continued_phase_evolution():
    assert all(observation_light(t) == 0 for t in (119.6,120,121,122.2))
    assert observation_light(119.5) > 0 and observation_light(122.3) > 0
    assert np.max(np.abs(phases(model_time(119.6))-phases(model_time(122.2)))) > .1


def test_geometry_supports_the_three_matched_visits():
    result=validate_embedding()
    assert result['reference_stitch_return_and_gauge_error'] < 1e-12
    assert result['reference_stitch_departure'] > .1
    assert result['woven_surrounding_world_difference'] > .5


def test_argument_reduction_preserves_the_declared_unitary_evolution():
    for time in (0,.01,.73,math.pi,2*math.pi,4*math.pi,model_time(240)):
        np.testing.assert_allclose(phases(time),np.exp(-1j*ENERGIES*time),atol=4e-14,rtol=0)
    np.testing.assert_array_equal(phases(model_time(104))[:8],np.ones(8))
    np.testing.assert_array_equal(phases(model_time(208))[:8],np.ones(8))
