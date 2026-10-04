"""Original listening shells and wave ribbons for the second-act sculpture.

These are artistic embeddings of the numerical fields. The protected rim,
pleating and wear apertures are geometry rules, not a fracture simulation.
"""
from dataclasses import dataclass
import functools
import math
import time

import numpy as np
from scipy.interpolate import CubicSpline

from studio.mesh_geometry import SheetMesh, boundary_edges, clipped_chart, field_samples, unit
from studio.reconstruction import periodic_field


@dataclass(frozen=True)
class ListenerShape:
    opening: float = .91
    flare: float = 1.0
    height: float = 1.0
    pleats: int = 7
    twist: float = .44
    thickness: float = .012
    deformation: float = 1.0


@functools.lru_cache(maxsize=12)
def listener_grid(nu, nv, opening):
    angle, radial = np.meshgrid(np.linspace(-math.pi * opening, math.pi * opening, nv),
                               np.linspace(0, 1, nu), indexing='ij')
    parameters = np.column_stack((radial.ravel(), angle.ravel()))
    corners = np.arange(nu * nv, dtype=np.int64).reshape(nv, nu)[:-1, :-1].ravel()
    faces = np.concatenate((np.column_stack((corners, corners + 1, corners + nu)),
                            np.column_stack((corners + 1, corners + nu + 1, corners + nu))))
    return parameters, faces


def listener_positions(parameters, field, shape=ListenerShape()):
    s, phi = parameters.T
    uv = np.column_stack((s, phi / (2 * math.pi) + .5))
    f = field_samples(field, uv)
    moving = np.tanh(f[:, 0] * 1.8)
    memory = np.tanh(f[:, 1] * 2.3)
    edge = .18 + .82 * s
    pleat = (.045 + .12 * np.maximum(s, 0) ** 1.5) * np.sin(shape.pleats * phi + 1.6 * s)
    radius = (.25 + 1.10 * s + .34 * s * s + pleat) * shape.flare
    radius += shape.deformation * edge * (.23 * moving + .27 * memory)
    theta = phi + shape.twist * s + shape.deformation * .24 * s * memory
    y = (-.96 + 2.02 * s - .24 * s * s) * shape.height
    y += .19 * s * s * np.sin(3 * phi + .6) + shape.deformation * s * (.18 * moving + .12 * memory)
    x = radius * np.cos(theta)
    z = radius * np.sin(theta)
    return np.column_stack((x, y, z)), uv


def listener_normal(parameters, field, shape):
    du = np.array([.0004, 0.])
    dv = np.array([0., .0006])
    a = listener_positions(parameters + du, field, shape)[0] - listener_positions(parameters - du, field, shape)[0]
    b = listener_positions(parameters + dv, field, shape)[0] - listener_positions(parameters - dv, field, shape)[0]
    return unit(np.cross(a, b))


def close_surface(center, normal, uv, front, thickness, stats):
    used, inverse = np.unique(front.ravel(), return_inverse=True)
    front = inverse.reshape(-1, 3)
    center, normal, uv = center[used], normal[used], uv[used]
    count = len(used)
    boundary = boundary_edges(front, count)
    a, b = boundary.T
    back = front[:, ::-1] + count
    walls = np.concatenate((np.column_stack((b, a, a + count)), np.column_stack((b, a + count, b + count))))
    positions = np.concatenate((center + thickness * normal, center - thickness * normal)).astype(np.float32)
    normals = np.concatenate((normal, -normal)).astype(np.float32)
    triangles = np.concatenate((front, back, walls)).astype(np.uint32)
    stats = {**stats, 'vertices': len(positions), 'triangles': len(triangles), 'boundary_segments': len(boundary)}
    return SheetMesh(positions, normals, np.concatenate((uv, uv)).astype(np.float32), triangles, 2 * len(front), stats)


def build_listener(field, nu=128, nv=192, shape=ListenerShape()):
    began = time.monotonic()
    if nu < 12 or nv < 16 or not .2 <= shape.opening < 1 or not .003 <= shape.thickness <= .05:
        raise ValueError('Unsupported listening-shell chart')
    field = periodic_field(field, max(256, *field.shape[:2]))
    parameters, faces = listener_grid(nu, nv, shape.opening)
    s, phi = parameters.T
    uv = np.column_stack((s, phi / (2 * math.pi) + .5))
    f = field_samples(field, uv)
    window = 2.4 * f[:, 2] - (.90 + .30 * np.sin(5 * phi + 4 * s) + .15 * np.cos(3 * phi - 6 * s))
    # The continuous collar and rim survive even where the central skin is worn.
    protected = (s < .065) | (s > .955) | (np.abs(phi) > math.pi * shape.opening * .975)
    window[protected] = -1.
    parameters, front, _, _ = clipped_chart(parameters, faces, window)
    center, uv = listener_positions(parameters, field, shape)
    normal = listener_normal(parameters, field, shape)
    mesh = close_surface(center, normal, uv, front, shape.thickness,
                         {'kind': 'listening-shell', 'nu': nu, 'nv': nv,
                          'visible_chart_fraction': float((window <= 0).mean())})
    mesh.stats['seconds_to_build'] = time.monotonic() - began
    return mesh


def listener_anchor(uv, field, shape=ListenerShape()):
    smooth = periodic_field(field, max(256, *field.shape[:2]))
    parameters = np.array([[uv[0], (uv[1] - .5) * 2 * math.pi]])
    point = listener_positions(parameters, smooth, shape)[0][0]
    normal = listener_normal(parameters, smooth, shape)[0]
    return point + normal * shape.thickness


def build_wave_ribbon(first, second, bead_displacement, endpoints, *, bead_velocity=None,
                      arch=.75, width=.065, twist=1.2, nu=5, nv=160, thickness=.008):
    """Embed the chain's deviation from its endpoint chord in an authored ribbon."""
    began = time.monotonic()
    first, second = np.asarray(first, dtype=float), np.asarray(second, dtype=float)
    if np.linalg.norm(second - first) < .1:
        raise ValueError('Ribbon anchors are too close')
    t = np.linspace(0, 1, nv)
    control_t = np.linspace(0, 1, len(bead_displacement) + 2)
    q = np.concatenate(([endpoints[0]], bead_displacement, [endpoints[1]]))
    wave = CubicSpline(control_t, q, bc_type='natural')(t)
    deviation = wave - ((1 - t) * endpoints[0] + t * endpoints[1])
    velocity = np.zeros_like(t) if bead_velocity is None else CubicSpline(control_t, np.r_[0., bead_velocity, 0.], bc_type='natural')(t)
    chord = second - first
    horizontal = np.cross(chord, [0., 1., 0.])
    if np.linalg.norm(horizontal) < .001:
        horizontal = np.cross(chord, [0., 0., 1.])
    horizontal = unit(horizontal)
    center = (1 - t[:, None]) * first + t[:, None] * second
    center += (4 * t * (1 - t) * arch)[:, None] * np.array([0., 1., 0.])
    center += deviation[:, None] * (np.array([0., .8, 0.]) + .35 * horizontal)
    tangent = unit(np.gradient(center, axis=0))
    across = unit(np.cross(tangent, np.broadcast_to(horizontal, tangent.shape)))
    turn = twist * math.pi * t + .23 * np.tanh(velocity)
    across = across * np.cos(turn[:, None]) + np.cross(tangent, across) * np.sin(turn[:, None])
    radius = width * (.55 + .45 * np.sin(math.pi * t) ** .65)
    spread = np.linspace(-1, 1, nu)
    grid = center[:, None, :] + across[:, None, :] * (radius[:, None] * spread)[..., None]
    dt, ds = np.gradient(grid, axis=(0, 1), edge_order=2)
    normals = unit(np.cross(ds, dt)).reshape(-1, 3)
    along, side = np.meshgrid(t, np.linspace(0, 1, nu), indexing='ij')
    uv = np.column_stack((side.ravel(), along.ravel()))
    corners = np.arange(nu * nv, dtype=np.int64).reshape(nv, nu)[:-1, :-1].ravel()
    faces = np.concatenate((np.column_stack((corners, corners + 1, corners + nu)),
                            np.column_stack((corners + 1, corners + nu + 1, corners + nu))))
    mesh = close_surface(grid.reshape(-1, 3), normals, uv, faces, thickness,
                         {'kind': 'wave-ribbon', 'beads': len(bead_displacement), 'nu': nu, 'nv': nv})
    mesh.stats['seconds_to_build'] = time.monotonic() - began
    # The bridge has instantaneous wave state, not an invented retained memory.
    texture = np.zeros((nv, 2, 4), dtype=np.float32)
    texture[:, :, 0] = deviation[:, None]
    texture[:, :, 1] = np.gradient(wave, t)[:, None]
    texture[:, :, 2] = (velocity ** 2)[:, None]
    texture[:, :, 3] = velocity[:, None]
    return mesh, texture
