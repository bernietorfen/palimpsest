"""Authored phase sculpture for A River Twice.

Four eight-mode families are mapped to folded membranes. The reference family's
shape uses only its intra-family phase differences. The surrounding families
also use their coherence with the reference, and joining fibres use cross-family
phases. Both phase quadratures affect geometry. This is an artistic embedding,
not the shape of a quantum state or a material simulation. Run on the production
host.
"""
from __future__ import annotations

import math
import numpy as np

OFFSETS = np.array([0., math.sqrt(2.), math.sqrt(3.), math.sqrt(5.)])
ENERGIES = (OFFSETS[:, None] + np.arange(8)[None, :]).reshape(-1)
CENTRES = np.array([[-2.4, -1.1, 2.5], [2.25, .2, 2.4],
                    [-.3, 3.4, 2.7], [.5, -4.1, 2.2]])
SCALES = np.array([1., .88, 1.08, .73])
TURNS = np.array([.24, -.82, .7, 1.2])


def phases(time: float) -> np.ndarray:
    # Factor the integer harmonics from the irrational group offsets. Reducing
    # the integer turns before exponentiation preserves their exact recurrence
    # in a controlled rendered comparison, without replacing any mesh or state.
    time=float(time)
    turns=time/(2*math.pi)
    local=np.exp(-2j*math.pi*np.remainder(np.arange(8)*turns,1.))
    group=np.exp(-1j*OFFSETS*time)
    return (group[:,None]*local[None,:]).reshape(-1)


def unit(a):
    return a / np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-15)


def rotation(angle):
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, 0.], [s, c, 0.], [0., 0., 1.]])


def membrane(state, group, band, *, along=193, across=25, shape='river'):
    """A satin ribbon with fine integral pleats and an open, folded silhouette."""
    if shape == 'weave':
        return woven_membrane(state, group, band, along=along, across=across)
    q = state[group * 8 + band] * state[group * 8].conjugate()
    # No phase-angle unwrap: the two quadratures stay smooth through +/- pi.
    cr, si = float(q.real), float(q.imag)
    u = np.linspace(0., 1., along)
    v = np.linspace(-1., 1., across)
    alpha = 2 * math.pi * band / 8
    if shape == 'bloom':
        theta = (2.3 * math.pi * u + alpha + .26 * si * np.sin(math.pi * u))
        radius = .34 + .84 * np.sin(math.pi * u) ** .8 + .20 * u
        radius += .14 * (cr - 1) * np.sin(2 * math.pi * u + alpha)
        center = np.column_stack((radius * np.cos(theta), radius * np.sin(theta),
                                  -2.05 + 4.1 * u + .24 * si * np.sin(math.pi * u)))
        width = .065 + .22 * np.sin(math.pi * u) ** .8
    else:
        # A sheaf of bent leaves crosses an open central interval. Its two
        # unequally curved ends avoid a vase or a regular mathematical torus.
        a = (u - .5) * (1.6 + .10*group) * math.pi
        radius = 1.1 + .13 * math.cos(alpha) + .13 * cr * np.cos(2 * a + alpha)
        center = np.column_stack((radius * np.cos(a) - .30,
                                  .30 * math.sin(alpha) + .36 * np.sin(a + alpha),
                                  1.85 * np.sin(a) + .25 * np.sin(2 * a + alpha)))
        center[:, 0] += .62 * si * np.sin(2 * a + alpha)
        center[:, 1] += .64 * (cr-1) * np.sin(a + .5 * alpha)
        center[:, 2] += .38 * si * np.cos(3*a + alpha)
        center = center @ rotation(alpha * .13 + .12 * si).T
        width = .009 + .28 * np.sin(math.pi * u) ** .65
    tangent = unit(np.gradient(center, axis=0))
    reference = np.broadcast_to([0., 1., .07], center.shape)
    transverse = unit(np.cross(tangent, reference))
    normal = unit(np.cross(tangent, transverse))
    # A gently changing frame makes broad silk surfaces and narrow lit edges.
    twist = .50 * np.sin(2 * math.pi * u + alpha) + .28 * si
    side = transverse * np.cos(twist[:, None]) + normal * np.sin(twist[:, None])
    face_normal = unit(np.cross(tangent, side))
    grid = center[:, None, :] + width[:, None, None] * v[None, :, None] * side[:, None, :]
    pleat = (.004 + .006 * np.sin(math.pi * u))[:, None] * np.sin(8 * math.pi * v)[None, :]
    pleat += .027 * (1-v*v)[None, :] * np.sin(8 * math.pi * u + alpha)[:, None]
    grid += pleat[:, :, None] * face_normal[:, None, :]
    transform = rotation(TURNS[group])
    grid = (grid @ transform.T) * SCALES[group] + CENTRES[group]
    uv = np.stack(np.meshgrid(u, (v+1)/2, indexing='ij'), axis=-1)
    corners = np.arange(along * across).reshape(along, across)[:-1, :-1].ravel()
    faces = np.column_stack((corners, corners + across, corners + across + 1, corners + 1))
    return grid, uv, faces


def woven_membrane(state, group, band, *, along=257, across=33, spatial=True):
    """One interleaved family in a single irregular architecture around a void.

    The reference family is locally periodic. Other families' placements also
    carry their phase relative to its reference mode. Thus its exact local
    recurrence leaves the surrounding weave free to differ substantially.
    """
    local = state[group*8+band] * state[group*8].conjugate()
    relative = state[group*8] * state[0].conjugate()
    u = np.linspace(0., 1., along, endpoint=False)
    v = np.linspace(-1., 1., across)
    a = 2*math.pi*u
    alpha = 2*math.pi*(4*band+group)/32
    phi = alpha + .90*np.sin(a+.4) + .30*np.sin(2*a)
    cp = np.cos(phi)*relative.real - np.sin(phi)*relative.imag
    sp = np.sin(phi)*relative.real + np.cos(phi)*relative.imag
    bundle = .23+.77*((1-np.cos(a-.7))/2)**1.3
    radius = 2.45 + .42*np.cos(a+.3) + .25*np.sin(3*a-.4)
    radius += .56*cp*bundle
    radius += .34*local.imag*np.sin(3*a+alpha)*bundle
    radius += .21*(local.real-1)*np.sin(2*a+alpha)*bundle
    center = np.column_stack((1.40*radius*np.cos(a),
                              .85*sp*bundle + .50*np.sin(2*a+.3),
                              3.55 + radius*np.sin(a) + .32*np.sin(2*a+alpha)))
    center[:, 1] += .32*local.imag*np.cos(3*a+alpha)*bundle
    tangent = unit(np.roll(center,-1,axis=0)-np.roll(center,1,axis=0))
    outward = unit(np.column_stack((np.cos(a)/1.4, np.zeros_like(a), np.sin(a))))
    side = unit(np.cross(tangent, outward))
    normal = unit(np.cross(tangent, side))
    twist = .60*np.sin(2*a+alpha) + .36*local.imag
    side = side*np.cos(twist[:,None]) + normal*np.sin(twist[:,None])
    normal = unit(np.cross(tangent, side))
    width = (.10+.055*(1+np.cos(2*a+alpha))/2)*(.3+.7*bundle)
    grid = center[:,None,:] + width[:,None,None]*v[None,:,None]*side[:,None,:]
    pleats = (.0038+.0025*np.sin(2*a+alpha)**2)[:,None]*np.sin(8*math.pi*v)[None,:]
    pleats += .010*np.sin(9*a+alpha)[:,None]*(1-v*v)[None,:]
    grid += pleats[:,:,None]*normal[:,None,:]
    if spatial:
        # The changing relation between families opens a common folded body.
        # The lower seam is a hinge, while the upper arc can part and cross.
        # This is a smooth authored map of both quadratures, not a force law.
        hinge = (.18+.82*(1+np.sin(a))/2)[:,None]
        opening = .80*float(relative.imag)*hinge
        x,y = grid[:,:,0].copy(),grid[:,:,1].copy()
        grid[:,:,0] = np.cos(opening)*x-np.sin(opening)*y
        grid[:,:,1] = np.sin(opening)*x+np.cos(opening)*y
        grid[:,:,1] += 1.20*float(1-relative.real)*hinge
        grid[:,:,2] += .35*float(relative.imag)*np.sin(a+alpha)[:,None]
    uv = np.stack(np.meshgrid(u, (v+1)/2, indexing='ij'), axis=-1)
    corners = np.arange(along*across).reshape(along,across)[:,:-1].ravel()
    after = (corners+across) % (along*across)
    faces = np.column_stack((corners,after,after+1,corners+1))
    return grid, uv, faces


def woven_relations(state, first, second, *, strands=18, samples=193):
    """Short inter-family crossings integrated into the architecture."""
    s = np.linspace(0.,1.,samples)
    where = (.075+.19*first+.037*second) % 1.
    first_grid = woven_membrane(state,first,2,along=257,across=3)[0]
    second_grid = woven_membrane(state,second,2,along=257,across=3)[0]
    a = first_grid[round(where*256),1]
    b = second_grid[round(((where+.13)%1)*256),1]
    delta = b-a
    across = unit(np.cross(delta,np.array([0.,1.,0.])))
    up = unit(np.cross(across,delta))
    envelope = np.sin(math.pi*s)
    fibers=[]
    for k in range(strands):
        q=state[first*8+(k%8)]*state[second*8+(k%8)].conjugate()
        turn=2*math.pi*s+k*2*math.pi/strands
        cr=q.real*np.cos(turn)-q.imag*np.sin(turn)
        si=q.imag*np.cos(turn)+q.real*np.sin(turn)
        center=a[None,:]+s[:,None]*delta[None,:]
        center+=(envelope*(.12+.12*cr))[:,None]*across
        center+=(envelope*(.08+.09*si))[:,None]*up
        fibers.append(center)
    return fibers


def group_pose(state, group):
    """Global placement depends on cross-family phase; local shape does not."""
    if group == 0:
        return CENTRES[0], np.eye(3)
    q = state[group*8] * state[0].conjugate()
    c, s = float(q.real), -float(q.imag)
    turn = np.array([[c, -s, 0.], [s, c, 0.], [0., 0., 1.]])
    center = CENTRES[group] @ turn.T
    center[2] += .72*s
    lean = .48*s
    cp, sp = math.cos(lean), math.sin(lean)
    tilt = np.array([[cp,0.,sp],[0.,1.,0.],[-sp,0.,cp]])
    return center, turn @ tilt


def woven_internal_relations(state, first, second, *, strands=7, samples=97):
    """Fine stitches between adjacent reference modes, exactly locally periodic."""
    s=np.linspace(0.,1.,samples)
    where=.53+.025*first
    one=woven_membrane(state,0,first,along=257,across=3)[0]
    two=woven_membrane(state,0,second,along=257,across=3)[0]
    a=one[round(where*256),1]
    b=two[round((where+.045)*256),1]
    delta=b-a
    across=unit(np.cross(delta,np.array([0.,1.,0.])))
    up=unit(np.cross(across,delta))
    q=state[first]*state[second].conjugate()
    envelope=np.sin(math.pi*s)
    paths=[]
    for k in range(strands):
        turn=2*math.pi*s+k*2*math.pi/strands
        real=q.real*np.cos(turn)-q.imag*np.sin(turn)
        imag=q.imag*np.cos(turn)+q.real*np.sin(turn)
        center=a[None,:]+s[:,None]*delta[None,:]
        center+=(envelope*(.10+.055*real))[:,None]*across
        center+=(envelope*.055*imag)[:,None]*up
        paths.append(center)
    return paths


def place_membrane(grid, state, group):
    center, orientation = group_pose(state, group)
    return (grid-CENTRES[group]) @ orientation.T + center


def joining_fibres(state, first, second, *, strands=18, samples=193, placed=False):
    """Bundle of real cross-family phase relations, rendered as curved fibres."""
    s = np.linspace(0., 1., samples)
    a, b = CENTRES[first].copy(), CENTRES[second].copy()
    if placed:
        a, b = group_pose(state, first)[0].copy(), group_pose(state, second)[0].copy()
    a[2] += .15
    b[2] += .15
    delta = b - a
    across = unit(np.cross(delta, np.array([0., 0., 1.])))
    up = unit(np.cross(across, delta))
    fibers = []
    for k in range(strands):
        r = k % 8
        q = state[first*8+r] * state[second*8+r].conjugate()
        phase = k * 2 * math.pi / strands
        envelope = np.sin(math.pi * s)
        turn = 2 * math.pi * s + phase
        real = q.real * np.cos(turn) - q.imag * np.sin(turn)
        imag = q.imag * np.cos(turn) + q.real * np.sin(turn)
        center = a[None, :] + s[:, None] * delta[None, :]
        center += (.62 * envelope)[:, None] * up
        center += (envelope * (.13+.22*real))[:, None] * across
        center += (envelope * (.13*imag))[:, None] * up
        center += ((k/(strands-1)-.5)*.10) * across
        fibers.append(center)
    return fibers


def distance(state):
    # Stable fixed-population pure-state phase variance.
    mean = np.mean(state)
    return float(np.sqrt(np.mean(np.abs(state - mean)**2)))


def validate_embedding():
    first, returned = phases(0), phases(2*math.pi)
    maximum = 0.
    for g in range(4):
        for r in range(8):
            a = membrane(first, g, r, along=33, across=9)[0]
            b = membrane(returned, g, r, along=33, across=9)[0]
            c = membrane(first*np.exp(.713j), g, r, along=33, across=9)[0]
            maximum = max(maximum, float(np.max(np.abs(a-b))), float(np.max(np.abs(a-c))))
    x = np.array(joining_fibres(first, 0, 1))
    y = np.array(joining_fibres(returned, 0, 1))
    common = np.array(joining_fibres(first*np.exp(.713j), 0, 1))
    assert maximum < 1e-12
    assert np.max(np.abs(x-y)) > .1
    assert np.max(np.abs(x-common)) < 1e-12
    weave_error = 0.
    weave_difference = 0.
    for g in range(4):
        for r in range(8):
            a = woven_membrane(first,g,r,along=33,across=9)[0]
            b = woven_membrane(returned,g,r,along=33,across=9)[0]
            c = woven_membrane(first*np.exp(.713j),g,r,along=33,across=9)[0]
            assert np.isfinite(a).all() and np.isfinite(b).all()
            weave_error = max(weave_error,float(np.max(np.abs(a-c))))
            if g == 0:
                weave_error = max(weave_error,float(np.max(np.abs(a-b))))
            else:
                weave_difference = max(weave_difference,float(np.max(np.abs(a-b))))
    assert weave_error < 1e-12 and weave_difference > .5
    # The repeated copper seam must really return, rather than being replaced
    # by an earlier mesh at the three authored camera visits.
    stitch_error = 0.
    stitch_departure = 0.
    for first_mode in range(7):
        baseline = np.array(woven_internal_relations(first,first_mode,first_mode+1))
        for state in (returned,phases(4*math.pi),first*np.exp(.713j)):
            candidate = np.array(woven_internal_relations(state,first_mode,first_mode+1))
            assert np.isfinite(candidate).all()
            stitch_error = max(stitch_error,float(np.max(np.abs(candidate-baseline))))
        moving = np.array(woven_internal_relations(phases(.73),first_mode,first_mode+1))
        stitch_departure = max(stitch_departure,float(np.max(np.abs(moving-baseline))))
    assert stitch_error < 1e-12 and stitch_departure > .1
    return {'local_periodic_and_global_phase_error': maximum,
            'cross_relation_geometry_difference': float(np.max(np.abs(x-y))),
            'woven_reference_return_and_gauge_error': weave_error,
            'woven_surrounding_world_difference': weave_difference,
            'reference_stitch_return_and_gauge_error': stitch_error,
            'reference_stitch_departure': stitch_departure,
            'full_state_distance_at_fragment_return': distance(returned)}
