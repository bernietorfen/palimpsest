"""Narrative continuity and camera safety, executed only on RunPod."""
import numpy as np

from studio.cinematography import camera_at


def test_identical_questions_have_identical_camera_and_light_paths():
    for age in np.linspace(0,46,97):
        first=camera_at(float(18+age))
        returning=camera_at(float(370+age))
        assert first.keys()==returning.keys()
        for key in first:
            np.testing.assert_allclose(first[key],returning[key],rtol=0,atol=2e-13)


def test_camera_stays_outside_geometry_and_looks_along_a_valid_direction():
    for t in np.linspace(0,431.999,1000):
        params=camera_at(float(t))
        camera=np.asarray(params["camera"])
        target=np.asarray(params["target"])
        assert np.linalg.norm(camera)>2.5
        direction=target-camera
        assert np.linalg.norm(direction)>1
        assert np.linalg.norm(np.cross(direction,[0,1,0]))>.5
        assert np.isfinite(direction).all()
