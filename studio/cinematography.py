"""Authored camera score. The returning question repeats its original view."""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class View:
    camera: tuple[float,float,float]
    target: tuple[float,float,float] = (0.,0.,0.)
    turn: float = .55
    light_angle: float = .25
    focal_length: float = 2.05
    lens_radius: float = .008
    exposure: float = 1.10
    camera_roll: float = 0.


@dataclass(frozen=True)
class Shot:
    start: float
    end: float
    name: str
    first: View
    last: View


def blend(a,b,t):
    if isinstance(a,tuple):
        return tuple(x+(y-x)*t for x,y in zip(a,b))
    return a+(b-a)*t


SHOTS=(
    Shot(0,16,"Before the first impression",
         View((6.5,3.8,6.5),lens_radius=.003,exposure=.48),
         View((5.,2.9,5.3),lens_radius=.004)),
    Shot(16,43,"The question / portrait",
         View((5.,2.9,5.3),lens_radius=.004),
         View((4.4,2.6,5.0),(.04,.03,0.),lens_radius=.005)),
    Shot(43,72,"The question / inscription",
         View((2.8,1.65,3.35),(.43,.13,.18),lens_radius=.009),
         View((2.6,1.48,3.15),(.44,.10,.19),lens_radius=.009,camera_roll=.018)),
    Shot(72,100,"Another side of the same skin",
         View((-3.9,2.1,5.1),(.03,.04,0.),turn=.55,lens_radius=.005),
         View((-3.3,1.7,5.0),(.07,.02,0.),turn=.62,lens_radius=.006)),
    Shot(100,126,"The opening",
         View((3.7,1.8,2.2),(.54,.12,.08),turn=.78,lens_radius=.010),
         View((3.35,1.55,2.1),(.55,.12,.1),turn=.83,lens_radius=.010)),
    Shot(126,150,"An accumulated shape",
         View((5.1,1.65,4.6),turn=.83,lens_radius=.005),
         View((4.8,1.95,4.8),turn=.85,lens_radius=.005)),
    Shot(150,180,"The chamber answers",
         View((2.8,1.5,3.1),(.35,.1,.1),turn=.65,lens_radius=.008),
         View((2.6,1.42,3.15),(.31,.12,.09),turn=.7,lens_radius=.008)),
    Shot(180,216,"A moving boundary",
         View((4.9,3.1,-3.2),(.02,.03,0.),turn=.7,lens_radius=.005),
         View((4.8,2.45,-3.65),(.02,.02,0.),turn=.8,lens_radius=.005)),
    Shot(216,240,"New wear",
         View((2.8,1.1,3.4),(.35,-.04,.15),turn=.8,lens_radius=.008),
         View((2.6,1.3,3.2),(.34,.02,.14),turn=.85,lens_radius=.008)),
    Shot(240,272,"Too much to hold",
         View((4.7,2.5,4.7),turn=.85,lens_radius=.004),
         View((4.4,2.8,4.6),turn=.98,lens_radius=.004)),
    Shot(272,296,"The last dense inscription",
         View((3.,.75,3.),(.28,-.08,.11),turn=.98,lens_radius=.009),
         View((3.25,.92,3.2),(.26,-.07,.09),turn=1.03,lens_radius=.008)),
    Shot(296,320,"Holding",
         View((4.8,2.8,4.8),turn=.72,lens_radius=.004),
         View((4.65,2.7,4.9),turn=.67,lens_radius=.004)),
    Shot(320,345,"The inscription recedes",
         View((2.8,1.7,3.1),(.35,.1,.1),turn=.55,lens_radius=.008),
         View((2.9,1.72,3.2),(.33,.11,.09),turn=.55,lens_radius=.008)),
    Shot(345,368,"What remains",
         View((4.8,2.8,5.1),turn=.55,lens_radius=.004),
         View((5.,2.9,5.3),turn=.55,lens_radius=.004)),
    # 368-424 deliberately reuses 16-72, rather than a visually similar copy.
    Shot(424,432,"After the question",
         View((4.7,2.7,5.0),turn=.55,lens_radius=.004),
         View((5.6,3.25,6.0),turn=.55,lens_radius=.003)),
)


def camera_at(time: float) -> dict:
    t=time-352 if 368 <= time < 424 else time
    shot=next((s for s in SHOTS if s.start <= t < s.end),SHOTS[-1])
    u=min(1.,max(0.,(t-shot.start)/(shot.end-shot.start)))
    # Slow acceleration and deceleration keep the material's motion distinct.
    eased=u*u*(3-2*u)
    params={name:blend(getattr(shot.first,name),getattr(shot.last,name),eased)
            for name in View.__dataclass_fields__}
    return {"design":3,"style":0,"aperture":0.,**params}


def shot_name(time: float) -> str:
    if 368 <= time < 424:
        return "The same question / "+("portrait" if time<395 else "inscription")
    return next((s.name for s in SHOTS if s.start<=time<s.end),SHOTS[-1].name)


def fade_at(time: float, duration: float=432.) -> float:
    fadein=min(1.,max(0.,time/2.))
    fadeout=min(1.,max(0.,(duration-time)/6.))
    return math.sin(fadein*math.pi/2)**2*math.sin(fadeout*math.pi/2)**2


def manifest() -> dict:
    from dataclasses import asdict
    return {"shots":[asdict(s) for s in SHOTS],"return":"368-424 reuses camera time 16-72 exactly",
            "effective_shot_boundaries":sorted(set([s.start for s in SHOTS]+[368,395])),
            "surface":"Fatigue opens the skin; rest-shape memory carries its contour inscription."}
