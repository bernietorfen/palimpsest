"""Authored camera and light score, separate from the finite phase dynamics."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
import numpy as np
from studio.river_geometry import woven_internal_relations, woven_membrane, phases


@dataclass(frozen=True)
class Shot:
    start: float
    end: float
    name: str
    first: tuple
    last: tuple
    target_first: tuple
    target_last: tuple
    lens: float
    aperture: float = 5.6
    roll: float = 0.
    lens_end: float | None = None
    aperture_end: float | None = None


# These are world-space camera positions, not state variables. The repeated
# intimate framing is exactly the same at 0,104,208; light matching is explicit.
def model_time(seconds):
    return (float(seconds)/104.)*(2*math.pi)


def reference_target(seconds):
    state=phases(model_time(seconds))
    return np.asarray(woven_internal_relations(state,5,6)[3][48])


REFERENCE_OFFSET = np.asarray((-.55,-2.65,.58))
MATCH_TARGET = tuple(reference_target(0))
MATCH_POSITION = tuple(reference_target(0)+REFERENCE_OFFSET)
OPENING_END = tuple(reference_target(8)+REFERENCE_OFFSET+(.18,-.25,.18))
OPENING_TARGET_END = tuple(reference_target(8)+(.15,.05,.10))
WHOLE_POSITION = (4.4,-12.4,7.)
WHOLE_TARGET = (-.3,0,3.8)
SHOTS = (
    Shot(0,8,'A first fold',MATCH_POSITION,OPENING_END,MATCH_TARGET,OPENING_TARGET_END,68,4.),
    Shot(8,20,'A world answers',OPENING_END,WHOLE_POSITION,OPENING_TARGET_END,WHOLE_TARGET,68,4.,lens_end=52,aperture_end=8.),
    Shot(20,32,'The crossing',(1.0,-4.0,2.4),(-1.2,-3.5,3.2),(-.3,0,2.6),(-1.3,0,3.0),68,4.),
    Shot(32,44,'Inside the current',(-5.3,-6.5,3.7),(-4.8,-4.7,4.2),(-2.4,0,3.6),(-2.6,0,4.),60,5.6),
    Shot(44,56,'An ascending line',(-1.8,-6.4,6.5),(2.8,-6.0,7.5),(-.8,0,5.),(1.2,0,5.4),62,5.6),
    Shot(56,72,'Shared architecture',(7.5,-15.0,8.),(3.5,-14.,9.5),(0,0,3.6),(-.25,0,3.7),52,8.),
    Shot(72,84,'The space between',(1.1,-7.,3.6),(.6,-3.2,3.7),(0,0,3.7),(-.2,.5,3.7),45,8.),
    Shot(84,96,'Approaching the crest',(-6.0,-9.,3.6),(-4.4,-11.,6.2),(-.4,0,3.4),(-.3,0,3.6),54,6.3),
    Shot(96,101,'A returning edge',(-3.8,-4.2,5.4),tuple(reference_target(101)+REFERENCE_OFFSET),(-2.9,0,5.1),tuple(reference_target(101)),72,4.,lens_end=68),
    Shot(101,106,'The first exact fragment return',MATCH_POSITION,MATCH_POSITION,MATCH_TARGET,MATCH_TARGET,68,4.),
    Shot(106,112,'Its changed surroundings',tuple(reference_target(106)+REFERENCE_OFFSET),WHOLE_POSITION,tuple(reference_target(106)),WHOLE_TARGET,68,4.,lens_end=52,aperture_end=8.),
    Shot(112,119.6,'Withdrawing light',WHOLE_POSITION,WHOLE_POSITION,WHOLE_TARGET,WHOLE_TARGET,52,8.),
    Shot(119.6,122.2,'An unobserved interval',WHOLE_POSITION,WHOLE_POSITION,WHOLE_TARGET,WHOLE_TARGET,52,8.),
    Shot(122.2,136,'A remaining strand',(-1.4,-4.,1.35),(-2.4,-4.4,2.0),(-.6,0,1.8),(-1.5,0,2.3),78,4.),
    Shot(136,148,'The answer elsewhere',(3.8,-5.5,4.2),(4.3,-5.4,5.1),(2.1,0,3.8),(2.3,0,4.3),64,5.6),
    Shot(148,160,'A new continuity',(-4.5,-7.7,5.),(-3.4,-6.5,4.8),(-1.5,0,4.),(-.6,0,3.8),56,5.6),
    Shot(160,180,'Along what remains',(.6,-8.,3.6),(.1,2.2,3.7),(0,1.,3.65),(0,5.,3.7),48,8.),
    Shot(180,196,'The other side',(-3.7,12.,7.3),(3.8,11.,6.7),(0,0,3.6),(0,0,3.6),52,8.),
    Shot(196,204,'The world gathers',(6.8,-12.5,8.6),(3.3,-10.,7.2),(0,0,3.6),(0,0,3.6),52,8.),
    Shot(204,210,'The second exact fragment return',MATCH_POSITION,MATCH_POSITION,MATCH_TARGET,MATCH_TARGET,68,4.),
    Shot(210,222,'Carried by the whole',tuple(reference_target(210)+REFERENCE_OFFSET),WHOLE_POSITION,tuple(reference_target(210)),WHOLE_TARGET,68,4.,lens_end=52,aperture_end=8.),
    Shot(222,228,'The relation remains',WHOLE_POSITION,WHOLE_POSITION,WHOLE_TARGET,WHOLE_TARGET,52,8.),
    Shot(228,240,'What remains',WHOLE_POSITION,WHOLE_POSITION,WHOLE_TARGET,WHOLE_TARGET,52,8.),
)


def smooth(x):
    x=float(np.clip(x,0.,1.))
    return x*x*(3-2*x)


def camera_at(seconds):
    t=float(np.clip(seconds,0.,240.))
    shot=next((item for item in SHOTS if item.start <= t < item.end),SHOTS[-1])
    x=smooth((t-shot.start)/(shot.end-shot.start))
    location=(1-x)*np.asarray(shot.first)+x*np.asarray(shot.last)
    target=(1-x)*np.asarray(shot.target_first)+x*np.asarray(shot.target_last)
    if t < 8 or 101 <= t < 106 or 204 <= t < 210:
        target=reference_target(t)
        location=target+REFERENCE_OFFSET
        if t < 8:
            location=location+x*np.asarray((.18,-.25,.18))
            target=target+x*np.asarray((.15,.05,.10))
    # The intimate tours track a real moving membrane. A guessed fixed target
    # can otherwise leave most of a shot staring through the aperture at air.
    tracking={
        'An ascending line': (1,5,.22,.30,(0.,-4.,1.)),
        'The space between': (2,3,.42,.50,(-1.4,-5.2,.6)),
        'A remaining strand': (2,5,.67,.61,(-.8,-4.2,.7)),
        'The answer elsewhere': (3,2,.10,.16,(1.2,-5.5,1.6)),
        'Along what remains': (1,5,.60,.22,None),
    }
    if shot.name in tracking:
        group,band,first,last,offset=tracking[shot.name]
        u=(1-x)*first+x*last
        grid=woven_membrane(phases(model_time(t)),group,band,along=513,across=3)[0]
        at=u*len(grid)
        index=int(at)%len(grid)
        fraction=at-int(at)
        target=(1-fraction)*grid[index,1]+fraction*grid[(index+1)%len(grid),1]
        if offset is None:
            offset=(2*math.cos(2*math.pi*u),-4.,1.8*math.sin(2*math.pi*u))
        location=target+np.asarray(offset)
    lens=shot.lens if shot.lens_end is None else (1-x)*shot.lens+x*shot.lens_end
    aperture=shot.aperture if shot.aperture_end is None else (1-x)*shot.aperture+x*shot.aperture_end
    return {'location':location,'target':target,'lens':lens,
            'aperture':aperture,'roll':shot.roll,'shot':shot.name}


def observation_light(seconds):
    """An authored blackout, not an interruption or destruction of the state."""
    t=float(seconds)
    if 112 <= t < 119.6:
        return 1-smooth((t-112)/7.6)
    if 119.6 <= t <= 122.2:
        return 0.
    if 122.2 < t < 123.8:
        return smooth((t-122.2)/1.6)
    return 1.


def reference_focus(seconds):
    """An isolated reference view at each matched shot; no state is changed."""
    t=float(seconds)
    if t < 8:
        return 1.
    if t < 20:
        return 1-smooth((t-8)/12)
    if 96 <= t < 101:
        return smooth((t-96)/5)
    if 101 <= t <= 106 or 204 <= t <= 210:
        return 1.
    if 106 < t < 112:
        return 1-smooth((t-106)/6)
    if 210 < t < 222:
        return 1-smooth((t-210)/12)
    return 0.


def manifest():
    return {'title':'A River Twice','duration':240.,'shots':[asdict(s) for s in SHOTS],
            'model_time':'2*pi*film_seconds/104', 'exact_local_returns':[0.,104.,208.],
            'blackout':[119.6,122.2],
            'tracking':'Reference shots follow the actual copper stitch; five intimate tours follow moving membrane coordinates. Endpoint arrays are the static fallback score; camera_at supplies the executed tracking.',
            'scope':'Camera, light and shot changes are authored observation and composition; the phase evolution continues through the blackout.'}
