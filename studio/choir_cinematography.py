"""Original camera and listening score for A choir of absences."""
import math
import numpy as np


def ease(x):
    x=float(np.clip(x,0,1));return x*x*(3-2*x)


def blend(a,b,x):
    x=ease(x);return tuple((1-x)*np.asarray(a)+x*np.asarray(b))


def witness(t):
    # Reused exactly, with the same local clock, for the returning view of E.
    return {'camera':(6.1-.004*t,1.65+.0015*t,.1+.003*t),'target':(3.2,.57,-2.),
            'focal_length':1.65,'lens_radius':.020,'focus_distance':3.7}


def camera_at(t):
    base={'exposure':1.05,'backdrop':1,'light_angle':.1,'shadow_extent':8.5,'shadow_softness':1.}
    if t<28:settings=witness(t)
    elif t<48:
        a=witness(28);x=(t-28)/20
        settings={'camera':blend(a['camera'],(10.4,7.2,13.5),x),'target':blend(a['target'],(0,.25,0),x),
                  'focal_length':1.65+(2.35-1.65)*ease(x),'lens_radius':.014}
    elif t<96:
        x=(t-48)/48;angle=.58-.20*x;distance=16.8
        settings={'camera':(distance*math.sin(angle),7.2-.5*x,distance*math.cos(angle)),
                  'target':(0,.25,0),'focal_length':2.35,'lens_radius':.014}
    elif t<144:
        x=(t-96)/48
        settings={'camera':blend((-6.3,2.7,5.5),(-5.7,1.7,4.7),x),'target':(-2.9,.30,1.7),
                  'focal_length':1.45,'lens_radius':.022,'focus_distance':4.4}
    elif t<192:
        x=(t-144)/48;angle=.44+.35*x
        settings={'camera':(9.8*math.sin(angle),10.2,9.8*math.cos(angle)),
                  'target':(0,.2,0),'focal_length':2.2,'lens_radius':.012}
    elif t<228:
        x=(t-192)/36
        settings={'camera':blend((4.5,2.7,6.8),(3.8,2.2,5.8),x),'target':(-.1,.25,.1),
                  'focal_length':1.65,'lens_radius':.018,'focus_distance':7.7}
    elif t<248:
        x=(t-228)/20
        settings={'camera':blend((10.4,6.8,13.5),(10.,6.4,13.),x),'target':(0,.25,0),
                  'focal_length':2.35,'lens_radius':.012}
    elif t<272:settings=witness(t-243)
    else:
        a=witness(29);x=(t-272)/14
        settings={'camera':blend(a['camera'],(10.4,7.2,13.5),x),'target':blend(a['target'],(0,.25,0),x),
                  'focal_length':1.65+.70*ease(x),'lens_radius':.014}
    return {**base,**settings}


def pose_at(t):
    departed=ease((t-236)/10)
    if departed==0:return None
    return {1:{'position':[-3.2-17*departed,-.05+9*departed,1.8+2*departed]}}


def listening_weights(t):
    # Observation changes the mix, never the state of the underlying materials.
    weights=np.ones(7,dtype=np.float32)
    if t<28:
        weights[:]=.04;weights[4]=1.
    elif t<48:
        weights[:]=.04+.96*ease((t-28)/18);weights[4]=1.
    elif 248<=t<272:
        weights[:]=.04;weights[4]=1.;weights[1]=0.
    elif t>=272:
        weights[:]=.04+.96*ease((t-272)/12);weights[4]=1.;weights[1]=0.
    if t>=228:weights[1]*=1-ease((t-228)/8)
    return weights


def shot_name(t):
    return ('Witness E' if t<28 else 'The first widening' if t<48 else 'The spokes' if t<96 else
            'The source' if t<144 else 'The circle' if t<192 else 'Through the inscription' if t<228 else
            'Departure' if t<248 else 'The witness returns' if t<272 else 'The second widening')


def manifest():
    return {'cuts_seconds':[48,96,144,192,228,248],
            'matched_witness_views':'For 5 <= initial t < 28 and 248 <= final t < 271, the camera function and local time match exactly. The two widenings have separately authored durations.',
            'listener':'E is foregrounded in the opening and returning close views; other bodies retain 4 percent mix weight. Both widenings restore the ensemble. Source B fades from the mix during disconnection and stays absent.',
            'light':'Two fixed area lights, pale gallery floor; no lighting change is used to manufacture the return.',
            'departure':'B leaves only after bridge strengths have reached zero; this is a visual pose, not a dynamical body force.'}
