"""Closed and finite geometry under strong field and wear changes, on RunPod."""
import numpy as np
import pytest

from studio.choir_geometry import ListenerShape, build_listener, build_wave_ribbon
from studio.mesh_geometry import topology_report


@pytest.mark.parametrize('wear', [0., .55, 1.])
def test_listening_shell_keeps_closed_rim_and_finite_boundaries(wear):
    y, x = np.meshgrid(np.arange(32) * (2 * np.pi / 32), np.arange(32) * (2 * np.pi / 32), indexing='ij')
    field = np.zeros((32, 32, 4), dtype=np.float32)
    field[:, :, 0] = .7 * np.sin(x + 2 * y)
    field[:, :, 1] = .6 * np.sin(2 * x - y)
    field[:, :, 2] = wear
    report = topology_report(build_listener(field, 48, 72))
    assert report['finite']
    assert report['watertight_edges']
    assert report['boundary_edges'] == report['nonmanifold_edges'] == report['degenerate_faces'] == 0
    assert report['signed_volume'] > 0


def test_wave_ribbon_is_closed_with_displaced_anchors_and_moving_beads():
    nodes = np.linspace(0, 1, 18)[1:-1]
    displacement = .3 * np.sin(3 * np.pi * nodes) + .2 * nodes
    velocity = .5 * np.cos(2 * np.pi * nodes)
    mesh, texture = build_wave_ribbon([-2., 0., -.8], [2., .6, .4], displacement, [0., .2], bead_velocity=velocity, nv=100)
    report = topology_report(mesh)
    assert report['finite'] and report['watertight_edges']
    assert report['degenerate_faces'] == report['nonmanifold_edges'] == 0
    assert report['signed_volume'] > 0
    assert np.isfinite(texture).all()
    assert abs(float(texture[0, 0, 0])) < 1e-7
    assert abs(float(texture[-1, 0, 0])) < 1e-7
