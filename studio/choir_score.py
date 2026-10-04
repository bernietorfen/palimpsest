"""A choir of absences: an original 288-second composition for seven bodies.

Only B receives writing contacts. Six listeners receive the same small modal
question at the beginning and end. The source leaves after the bridges are cut.
The composition examines retained state, restricted observation and apparent
return in a nonlinear numerical material.
"""
from dataclasses import asdict
import math
import numpy as np
from studio.score import Gesture


class ChoirScore:
    duration=288.
    questions=(5.,248.)
    phrase=((0.,0,.025),(6.5,4,.022),(14.,2,.026),(23.,7,.019),(31.,3,.024))
    contacts=((1,.22,.5),(1,.70,.30),(1,.70,.70))
    chapters=((0.,'I. Before an encounter'),(48.,'II. A voice enters'),(96.,'III. What passes between'),
              (144.,'IV. An exchange'),(228.,'V. The source leaves'),(248.,'VI. The returning question'))

    def __init__(self):
        events=[]
        for t,level,sign in ((60,1.08,1),(71,1.25,1),(83,.92,-1)):
            events.append((0,Gesture(t,0,level,1.1,1.1,5.4,polarity=sign)))
        for t,level,sign in ((108,1.17,1),(120,.88,-1),(132,1.28,1)):
            events.append((1,Gesture(t,0,level,.9,1.3,5.5,polarity=sign)))
        for t,level,sign in ((149,1.22,1),(160,1.02,-1),(172,1.32,1),(184,.87,1)):
            events.append((2,Gesture(t,0,level,.7,1.1,5.7,polarity=sign)))
        # A short braided exchange: distinct points on the same source, not
        # additional directly played bodies. Space remains between the gestures.
        for k,t in enumerate((196,200.5,205.5,211,217)):
            events.append((k%3,Gesture(t,0,.64+.08*(k%3),.6,.8,5.0,polarity=-1 if k==2 else 1)))
        self.events=tuple(events)
        self.probes=tuple(Gesture(start+offset,mode,level,.8,.3,2.8) for start in self.questions for offset,mode,level in self.phrase)

    def connection_strengths(self,t):
        smooth=lambda a,b:float(np.clip((t-a)/(b-a),0,1))**2*(3-2*float(np.clip((t-a)/(b-a),0,1)))
        fade=1-smooth(228,236)
        return np.array([smooth(48,58)*fade]*6+[smooth(96,108)*fade]*6,dtype=np.float32)

    def excitation(self,t):
        result=np.zeros((7,12),dtype=np.float32)
        for event in self.probes:
            value=event.at(t)
            if value:result[[0,2,3,4,5,6],event.voice]+=value
        return result

    def contact_strengths(self,t):
        values=np.zeros(len(self.contacts),dtype=np.float32)
        for index,event in self.events:values[index]+=event.at(t)
        return values

    def manifest(self):
        return {'title':'A choir of absences','duration':self.duration,'chapters':self.chapters,
                'source_body':1,'receivers':[0,2,3,4,5,6],'contacts':self.contacts,
                'contact_events':[{'contact':i,**asdict(event)} for i,event in self.events],
                'question_starts':self.questions,'question':self.phrase,
                'question_events':[asdict(e) for e in self.probes],
                'connections':'Six spokes enter at 48–58 s; the outer circle at 96–108 s. All links leave at 228–236 s.',
                'transient_intervention':'At 242 s, set u=p and clear velocity, delayed feedback, echo phase and bridge motion. Retained inscription and wear are kept. The score clock continues.',
                'departure':'Body B is moved out of the camera composition only after every physical connection is zero. This pose change is an artistic embedding; no extra material force is applied.',
                'scope':'A composed performance. Its beginning/end comparison includes the retained material dynamics after the disclosed reset; the separate transfer protocol supplies controlled validation.'}
