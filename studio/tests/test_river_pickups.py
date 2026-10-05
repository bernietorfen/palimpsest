"""The camera revision must preserve the scientific and musical timeline."""
import numpy as np
import pytest

from studio.river_camera_pickups import PASSAGES, pickup_camera_at
from studio.river_cinematography import camera_at


@pytest.mark.parametrize('seconds', [0., 104., 132., 135.9, 148., 156.25, 180., 208., 239.9])
def test_every_unrevised_view_is_the_original_observer(seconds):
    original, revised = camera_at(seconds), pickup_camera_at(seconds)
    assert original['shot'] == revised['shot']
    for key in ('location', 'target', 'lens', 'aperture'):
        np.testing.assert_array_equal(original[key], revised[key])


@pytest.mark.parametrize('passage', PASSAGES)
def test_tracking_is_finite_and_moves_continuously_inside_each_passage(passage):
    times = np.arange(passage['start'], passage['end'], 1 / 24)
    states = [pickup_camera_at(float(seconds)) for seconds in times]
    locations = np.asarray([state['location'] for state in states])
    targets = np.asarray([state['target'] for state in states])
    assert np.isfinite(locations).all() and np.isfinite(targets).all()
    assert all(state['shot'] == passage['name'] for state in states)
    assert np.min(np.linalg.norm(locations - targets, axis=1)) > 2
    # A one-frame jump would be conspicuous in an otherwise slow tracking shot.
    assert np.max(np.linalg.norm(np.diff(locations, axis=0), axis=1)) < .05
    assert np.max(np.linalg.norm(np.diff(targets, axis=0), axis=1)) < .05
    assert np.min(locations[:, 2]) > .2
