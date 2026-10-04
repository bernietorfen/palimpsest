"""One shared scene description for the studio and browser choir."""
import json
from pathlib import Path

import numpy as np

from studio.choir_geometry import ListenerShape, build_listener, build_wave_ribbon, listener_anchor
from studio.choir_material import Bridge, Port
from studio.choir_render import SceneObject, floor_object, transform, world_point
from studio.reconstruction import periodic_field


def load_scene(path='site/choir-scene.json'):
    scene = json.loads(Path(path).read_text())
    if scene.get('format') != 'palimpsest-choir-scene' or scene.get('version') != 1:
        raise ValueError('Unsupported choir scene')
    return scene


def bridge_specs(scene):
    defaults = scene['bridge']
    return tuple(Bridge(Port(*edge['first'], defaults['port_width']),
                        Port(*edge['second'], defaults['port_width']),
                        tension=edge['tension'], mass=defaults['mass'], damping=defaults['damping'])
                 for edge in scene['connections'])


def build_scene(scene, fields, wave_u, wave_v, endpoints, gates, *, nu=96, nv=144,
                include_floor=True, pose_overrides=None):
    if len(fields) != len(scene['bodies']) or len(wave_u) != len(scene['connections']):
        raise ValueError('The recorded choir and scene inventories differ')
    shapes = {key: ListenerShape(**value) for key, value in scene['shapes'].items()}
    # Reconstruct each periodic field once for its skin, ports and texture.
    fields = [periodic_field(field, max(256, *field.shape[:2])) for field in fields]
    objects, models, body_shapes = [], [], []
    for index, body in enumerate(scene['bodies']):
        pose = {**body, **((pose_overrides or {}).get(index, {}))}
        shape = shapes[pose['shape']]
        model = transform(pose['position'], turn=pose['turn'], tilt=pose['tilt'], lean=pose['lean'], scale=pose['scale'])
        models.append(model)
        body_shapes.append(shape)
        objects.append(SceneObject(build_listener(fields[index], nu, nv, shape), fields[index], model))
    for index, edge in enumerate(scene['connections']):
        if gates[index] < .005:
            continue
        first, second = edge['first'], edge['second']
        a = world_point(listener_anchor(first[1:], fields[first[0]], body_shapes[first[0]]), models[first[0]])
        b = world_point(listener_anchor(second[1:], fields[second[0]], body_shapes[second[0]]), models[second[0]])
        mesh, texture = build_wave_ribbon(a, b, wave_u[index], endpoints[index], bead_velocity=wave_v[index],
                                         arch=edge['arch'], twist=edge['twist'], width=.068 * float(gates[index]) ** .7)
        objects.append(SceneObject(mesh, texture, np.eye(4), kind=1))
    if include_floor:
        objects.append(floor_object(scene['floor']))
    return objects
