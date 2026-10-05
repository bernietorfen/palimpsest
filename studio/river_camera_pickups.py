"""A focused revision of the camera's attention after the composed silence.

The phase state, geometry, light and musical time stay unchanged. Two passages
follow connecting fibres so that the new musical carrier has a visual subject.
"""
from __future__ import annotations

import math
import numpy as np

from studio.river_cinematography import camera_at, model_time, smooth
from studio.river_geometry import phases, woven_relations


PASSAGES = (
    {'start': 136., 'end': 148., 'name': 'An answer held between',
     'relation': [1, 2], 'first_s': .50, 'last_s': .50,
     'first_offset': [4.07, -2.35, -1.71], 'last_offset': [3.91, -2.26, -1.64],
     'lens': 58., 'aperture': 5.6},
    {'start': 160., 'end': 172., 'name': 'The thread takes the phrase',
     'relation': [0, 2], 'first_s': .50, 'last_s': .50,
     'first_offset': [0., 3.195, -1.163], 'last_offset': [0., 3.323, -1.210],
     'lens': 58., 'aperture': 5.6},
    {'start': 172., 'end': 180., 'name': 'A relation opens outward',
     'relation': [1, 2], 'first_s': .50, 'last_s': .50,
     'first_offset': [2.5, 0., 4.330], 'last_offset': [3.25, 0., 5.629],
     'lens': 58., 'aperture': 6.3},
)


def pickup_camera_at(seconds):
    passage = next((item for item in PASSAGES if item['start'] <= seconds < item['end']), None)
    if passage is None:
        return camera_at(seconds)
    amount = smooth((seconds - passage['start']) / (passage['end'] - passage['start']))
    coordinate = (1 - amount) * passage['first_s'] + amount * passage['last_s']
    state = phases(model_time(seconds))
    paths = np.asarray(woven_relations(state, *passage['relation']))
    # Track the centre of the bundle, not one rapidly circling surface strand.
    centre = np.mean(paths, axis=0)
    fractional = coordinate * (len(centre) - 1)
    lower = min(int(math.floor(fractional)), len(centre) - 2)
    blend = fractional - lower
    target = (1 - blend) * centre[lower] + blend * centre[lower + 1]
    offset = ((1 - amount) * np.asarray(passage['first_offset'])
              + amount * np.asarray(passage['last_offset']))
    return {'location': target + offset, 'target': target, 'lens': passage['lens'],
            'aperture': passage['aperture'], 'roll': 0., 'shot': passage['name']}


def pickup_manifest():
    return {'edition': 'connecting-fibres-v1', 'passages': PASSAGES,
            'scope': 'Authored camera revision only. Outside these passages the original camera is used; model time, evolving geometry, light and music are preserved.'}
