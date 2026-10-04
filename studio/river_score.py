"""A River Twice: authored musical events, roles and dramatic cues.

This is composition, not measured sonification. Execute only on the RunPod.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path


INSTRUMENTS = {
    "felt": "Close warm modal pluck; the source that does not return.",
    "breath": "Soft harmonic breath; answering and inheriting voice.",
    "bow": "Slow low harmonic support with a quiet friction component.",
    "glass": "Sparse inharmonic resonances and high remembered fragments.",
    "pulse": "Short pitched contact; the motion of the woven passage.",
}


@dataclass(frozen=True)
class NoteEvent:
    id: str
    instrument: str
    start: float
    duration: float
    pitch: float
    velocity: float
    pan: float = 0.0
    brightness: float = 0.5
    attack: float = 0.02
    release: float = 0.4
    detune_cents: float = 0.0
    phase: float = 0.0
    phrase: str = ""


@dataclass(frozen=True)
class Cue:
    time: float
    name: str
    description: str


@dataclass
class RiverScore:
    duration: float
    events: list[NoteEvent]
    cues: list[Cue]
    sections: list[tuple[float, float, str]]
    silence: tuple[float, float]
    source_leaves: float
    seed: int = 26100417
    title: str = "A River Twice / Music miniature"
    preset: str = "miniature"
    extra_instruments: dict[str, str] = field(default_factory=dict)
    withdrawn_roles: tuple[str, ...] = ("felt", "pulse")
    mute_after: dict[str, float] = field(default_factory=dict)

    @property
    def instruments(self) -> dict[str, str]:
        return {**INSTRUMENTS, **self.extra_instruments}

    def validate(self) -> None:
        assert self.duration > 0
        assert len({e.id for e in self.events}) == len(self.events)
        for event in self.events:
            assert event.instrument in self.instruments
            assert 0 <= event.start < self.duration
            assert event.duration > 0 and event.release > 0
            assert 0 < event.attack <= event.duration
            assert 0 < event.velocity <= 1 and -1 <= event.pan <= 1
            assert 0 <= event.brightness <= 1
            assert 21 <= event.pitch <= 100
            assert not self.silence[0] <= event.start < self.silence[1]
            if event.instrument in self.withdrawn_roles:
                assert event.start < self.source_leaves
            if event.instrument in self.mute_after:
                assert event.start+event.duration+event.release <= self.mute_after[event.instrument]
        assert all(0 <= cue.time <= self.duration for cue in self.cues)
        assert self.sections[0][0] == 0 and self.sections[-1][1] == self.duration
        assert all(a[1] == b[0] for a, b in zip(self.sections, self.sections[1:]))

    def manifest(self) -> dict:
        self.validate()
        result = {
            "format": "palimpsest-river-score",
            "version": 1,
            "title": self.title,
            "duration": self.duration,
            "seed": self.seed,
            "motif": {"notes": ["D4", "F4", "E4", "A4", "D5"],
                      "midi": [62, 65, 64, 69, 74],
                      "relative_onsets": [0, 0.66, 1.27, 2.43, 4.05]},
            "source_leaves": self.source_leaves,
            "exact_silence": list(self.silence),
            "instruments": self.instruments,
            "sections": [{"start": a, "end": b, "name": name}
                         for a, b, name in self.sections],
            "cues": [asdict(cue) for cue in self.cues],
            "events": [asdict(event) for event in sorted(self.events, key=lambda e: (e.start, e.id))],
            "scientific_controls": None,
            "scope": "An original composed musical work. Timbral and narrative mappings are authored; no quantum sound or strict measured sonification is claimed.",
        }
        if self.preset != "miniature":
            result.update(preset=self.preset, withdrawn_roles=list(self.withdrawn_roles),
                          role_mute_after=self.mute_after,
                          withdrawal_scope="An authored choice of musical voice and visibility. The separate unitary model does not irreversibly destroy its state.")
        return result


def miniature() -> RiverScore:
    events: list[NoteEvent] = []

    def note(instrument, start, pitch, duration, velocity, *, pan=0., brightness=.5,
             attack=None, release=None, phrase="", detune=0.):
        default_attack = {"felt": .008, "breath": .24, "bow": .42,
                          "glass": .005, "pulse": .003}[instrument]
        default_release = {"felt": .35, "breath": .52, "bow": .8,
                           "glass": .65, "pulse": .11}[instrument]
        events.append(NoteEvent(
            id=f"{instrument}-{sum(e.instrument == instrument for e in events)+1:03d}",
            instrument=instrument, start=round(start, 6), duration=round(duration, 6),
            pitch=float(pitch), velocity=velocity, pan=pan, brightness=brightness,
            attack=default_attack if attack is None else attack,
            release=default_release if release is None else release,
            detune_cents=detune, phrase=phrase))

    def call(start, instrument="felt", *, stretch=1., transpose=0, strength=.78,
             pan=-.2, phrase="the first call", missing=(), register_last=0):
        offsets = (0., .66, 1.27, 2.43, 4.05)
        pitches = (62, 65, 64, 69, 74+register_last)
        durations = (1.05, .82, 1.6, 1.38, 2.5)
        emphases = (.86, .69, .75, .83, 1.)
        for k, (offset, pitch, duration, emphasis) in enumerate(zip(offsets, pitches, durations, emphases)):
            if k not in missing:
                note(instrument, start+offset*stretch, pitch+transpose,
                     duration*stretch, strength*emphasis, pan=pan+.035*k,
                     brightness=.42 if instrument == "felt" else .48, phrase=phrase)

    # A clear, slightly uneven call with an isolated low fifth underneath.
    call(1.1)
    note("bow", 5.2, 38, 3.1, .25, pan=-.06, brightness=.22, phrase="first ground")
    note("glass", 7.35, 81, 2., .18, pan=.40, brightness=.38, phrase="a distant reply")

    # Another timbre repeats the relation rather than simply doubling it.
    call(9.35, "breath", stretch=1.13, transpose=-12, strength=.50,
         pan=.23, phrase="someone answers")
    note("felt", 12.15, 57, 1.5, .34, pan=-.26, phrase="listening punctuation")
    note("felt", 14.3, 62, 1.6, .38, pan=-.21, phrase="listening punctuation")
    note("bow", 12.7, 34, 3.4, .30, pan=.04, brightness=.25, phrase="B flat ground")
    note("breath", 16.15, 65, 1.65, .40, pan=.24, phrase="answer lifts")
    note("felt", 16.8, 69, 1.15, .45, pan=-.14, phrase="shared fragment")
    note("felt", 18.05, 64, .95, .40, pan=.06, phrase="shared fragment")
    note("glass", 18.2, 74, 2.1, .20, pan=-.42, phrase="one bright trace")

    # Four unequal groups make the interlock breathe instead of looping.
    harmony = [
        (19., 38, (62, 69, 74, 76, 77, 69, 64, 69)),
        (23., 34, (62, 65, 69, 74, 77, 76, 65, 69)),
        (27., 43, (62, 67, 69, 74, 77, 74, 69, 65)),
        (31., 45, (61, 64, 69, 74, 76, 73, 69, 64)),
    ]
    for section, (start, bass, pitches) in enumerate(harmony):
        note("bow", start, bass, 3.45, .32+.035*section, pan=-.05,
             brightness=.27+.035*section, phrase="moving ground")
        for k, pitch in enumerate(pitches):
            # Staggered eighth-note cells with deliberate short rests.
            onset = start+k*.48+(0.07 if k in (3, 6) else 0)
            note("felt", onset, pitch, .7 if k % 3 else .94,
                 .37+.035*section+(.10 if k in (0, 4) else 0),
                 pan=-.30+.075*(k % 5), brightness=.45+.045*section,
                 phrase="the woven passage")
        for k in (0, 3, 5):
            note("pulse", start+k*.48, bass+12, .16,
                 .28+.045*section+(.10 if k == 0 else 0),
                 pan=(-.18, .15, -.05)[(k+section) % 3], brightness=.36,
                 phrase="motion between")
    for start, pitch, duration, velocity in [
        (20.2, 65, 1.5, .37), (22.0, 64, .95, .32),
        (24.2, 69, 1.6, .42), (26.05, 74, 1.45, .44),
        (28.15, 70, 1.25, .44), (29.6, 69, 1.1, .39),
        (31.5, 67, 1.4, .48), (33., 64, 1.35, .40),
    ]:
        note("breath", start, pitch, duration, velocity, pan=.27,
             brightness=.52, phrase="a voice crosses the braid")
    for start, pitch in [(24.68, 81), (29.45, 86), (32.42, 88)]:
        note("glass", start, pitch, 1.8, .23, pan=(-.4 if pitch == 86 else .4),
             brightness=.6, phrase="brief lights")

    # The call arrives over an open D sonority; the high strand is suspended E.
    call(34.15, strength=.81, stretch=.80, phrase="the last complete source call", pan=-.12)
    note("bow", 34.0, 38, 5.8, .53, pan=-.03, brightness=.38, phrase="the crest ground")
    note("bow", 34.12, 45, 5.0, .28, pan=.11, brightness=.34, phrase="the open fifth")
    note("breath", 34.7, 77, 1.85, .51, pan=.25, brightness=.64, phrase="register opens")
    note("breath", 36.9, 76, 3.2, .54, pan=.22, brightness=.60, phrase="a held ninth")
    note("breath", 38.7, 69, 2.05, .40, pan=-.23, brightness=.42, phrase="the remaining fifth")
    for k, pitch in enumerate((74, 77, 81, 86, 81, 76, 74)):
        note("felt", 38.2+k*.46, pitch, .68, .54-.025*k,
             pan=-.13+.055*k, brightness=.61, phrase="the source thins")
    for start, pitch, strength in [(34.0, 50, .50), (35.45, 50, .41),
                                  (37.4, 57, .47), (39.2, 50, .39)]:
        note("pulse", start, pitch, .2, strength, phrase="the final pulse")
    note("glass", 37.43, 86, 3.5, .32, pan=-.43, brightness=.54, phrase="the high crossing")
    note("glass", 40.45, 81, 2.1, .19, pan=.38, brightness=.35, phrase="the last reflection")
    note("felt", 41.45, 62, 1.10, .40, pan=-.2, brightness=.18, phrase="the source's last word")
    note("breath", 42.2, 64, 1.05, .21, pan=.22, brightness=.20,
         release=.5, phrase="an unfinished answer")

    # The original source is absent. Others distribute the same five notes.
    inherited = [(47.35, "breath", 62, 1.6, .40, .24),
                 (48.22, "glass", 77, 2.1, .20, -.34),
                 (48.93, "breath", 64, 1.7, .38, .24),
                 (50.56, "bow", 57, 2.0, .32, -.1),
                 (52.4, "breath", 74, 2.9, .46, .18)]
    for start, instrument, pitch, duration, strength, pan in inherited:
        note(instrument, start, pitch, duration, strength, pan=pan,
             brightness=.36, phrase="the familiar question elsewhere")
    note("bow", 48.0, 38, 4.15, .22, pan=-.03, brightness=.17, phrase="ground after absence")
    note("glass", 54.4, 81, 3.2, .16, pan=-.4, brightness=.30, phrase="the remembered edge")
    note("breath", 56.05, 69, 2.15, .29, pan=.17, brightness=.30, phrase="what remains")
    note("bow", 57.25, 38, 5.0, .25, pan=-.08, brightness=.21, phrase="the final ground")
    note("breath", 59.1, 62, 3.45, .29, pan=.17, brightness=.24, release=1.1,
         phrase="an open ending")
    note("glass", 60.55, 69, 3.0, .13, pan=-.3, brightness=.20, release=1.4,
         phrase="the last light")

    score = RiverScore(
        duration=66., events=events, silence=(45.4, 47.05), source_leaves=43.1,
        sections=[(0., 9., "A first mark"), (9., 19., "Someone answers"),
                  (19., 34., "What passes between"), (34., 43.1, "The almost-return"),
                  (43.1, 45.4, "The source leaves"), (45.4, 47.05, "No answer"),
                  (47.05, 61.8, "The familiar question, elsewhere"),
                  (61.8, 66., "What remains")],
        cues=[Cue(1.1, "first-contact", "First intimate D; show a tangible consequence."),
              Cue(5.15, "first-reach", "The call reaches its high D; reveal another body."),
              Cue(9.35, "answer", "A clearly different voice begins the same relation."),
              Cue(19., "interlock", "The quiet relationship becomes a moving weave."),
              Cue(27., "shared-motion", "Harmony and register broaden without a camera-only change."),
              Cue(34., "crest", "Open the visual scale as the low D returns."),
              Cue(37.43, "crossing", "High resonant accent over a suspended E."),
              Cue(41.45, "last-source", "The original voice's final low D."),
              Cue(43.1, "departure", "The source is gone; only the interrupted reply decays."),
              Cue(45.4, "silence", "Both music and synthetic room are exactly silent."),
              Cue(47.35, "altered-return", "The first note returns in another body."),
              Cue(52.4, "recognition", "The familiar high D arrives without the source."),
              Cue(61.8, "residue", "Stop new events; keep the changed image while resonance dies.")])
    score.validate()
    return score


def full_score() -> RiverScore:
    """A four-minute composition with separately written first and second arcs."""
    events: list[NoteEvent] = []
    counts: dict[str, int] = {}

    def n(role, start, pitch, duration, velocity, *, pan=0., bright=.5,
          attack=None, release=None, phrase="", detune=0.):
        attacks={"felt":.008,"breath":.24,"bow":.48,"glass":.005,"pulse":.003,"thread":.095}
        releases={"felt":.38,"breath":.6,"bow":.95,"glass":.72,"pulse":.12,"thread":.42}
        counts[role]=counts.get(role,0)+1
        events.append(NoteEvent(f"{role}-{counts[role]:03d}",role,round(start,6),round(duration,6),
                                float(pitch),velocity,pan,bright,
                                attacks[role] if attack is None else attack,
                                releases[role] if release is None else release,
                                detune,0.,phrase))

    def melody(role,start,pitches,spacing,durations,strength,*,pan=0.,bright=.5,phrase="",offsets=None):
        for k,pitch in enumerate(pitches):
            onset=start+(offsets[k] if offsets is not None else k*spacing)
            duration=durations[k] if isinstance(durations,(tuple,list)) else durations
            emphasis=(.88,.74,.80,.92,.78,.86,.76,.90)[k%8]
            n(role,onset,pitch,duration,strength*emphasis,pan=pan+.018*((k%3)-1),
              bright=bright,phrase=phrase)

    def call(start,role="felt",*,scale=1.,transpose=0,strength=.76,pan=-.20,
             phrase="the call",pitches=(62,65,64,69,74)):
        melody(role,start,[p+transpose for p in pitches],1.,
               [1.05*scale,.88*scale,1.45*scale,1.55*scale,2.3*scale],
               strength,pan=pan,bright=.43 if role=="felt" else .45,phrase=phrase,
               offsets=[x*scale for x in (0.,.66,1.27,2.43,4.05)])

    def ground(start,pitch,duration,strength=.30,*,fifth=False,phrase="ground"):
        n("bow",start,pitch,duration,strength,pan=-.04,bright=.27,phrase=phrase)
        if fifth:
            n("bow",start+.13,pitch+7,max(.6,duration-.4),strength*.44,
              pan=.16,bright=.23,phrase=phrase+" / fifth")

    def light(start,pitch=81,strength=.2,duration=2.1,pan=.4,phrase="a passing light"):
        n("glass",start,pitch,duration,strength,pan=pan,bright=.46,phrase=phrase)

    # I. An intelligible relation exists before the audience is asked for patience.
    call(1.1,phrase="the first intimate call")
    ground(5.2,38,3.3,.23,phrase="a first shared ground")
    light(7.3,81,.15,2.4)
    call(10.25,"breath",scale=1.12,transpose=-12,strength=.48,pan=.24,
         phrase="a distinct answering body")
    n("felt",13.75,57,1.5,.29,pan=-.18,phrase="a quiet acknowledgement")
    ground(15.4,34,3.9,.27,phrase="the relation changes colour")
    n("breath",17.2,65,1.65,.33,pan=.22,bright=.36,phrase="an answer remains")
    n("felt",18.65,64,1.2,.34,pan=-.2,phrase="an answer remains")
    call(21.4,scale=1.33,strength=.61,phrase="the shared form")
    melody("breath",22.75,(57,60,62,65),1.,(1.6,1.2,1.7,2.4),.37,
           pan=.25,bright=.38,phrase="contrary to the shared call",offsets=(0.,2.2,4.,5.8))
    ground(22.2,38,5.2,.26,fifth=True,phrase="held together")
    light(28.7,76,.16,2.8,pan=-.36)
    n("felt",30.0,57,1.1,.25,pan=-.16,phrase="breath before movement")

    # II. Three small cells; rests and a sung counterline interrupt the pattern.
    cells=[(32.,(62,69,65,64,57),(0.,.68,1.46,2.1,3.5),38),
           (37.5,(62,65,69,67,65),(0.,.65,1.65,2.4,3.45),43),
           (43.,(64,69,62,65),(0.,.8,1.7,3.1),45)]
    for start,pitches,offsets,bass in cells:
        melody("felt",start,pitches,1.,(.95,1.25,.9,1.1,1.45)[:len(pitches)],.54,
               pan=-.22,bright=.46,phrase="first interlocking cells",offsets=offsets)
        ground(start+.1,bass,3.8,.28,phrase="the changing ground")
        for k,offset in enumerate((0.,1.46,3.5)):
            n("pulse",start+offset,bass+12,.16,.20+(.06 if k==0 else 0),
              pan=.13 if k%2 else -.16,bright=.30,phrase="a spare shared pulse")
    melody("breath",34.4,(65,64,62,60,62,64),1.,(1.4,1.6,2.1,1.25,1.8,1.8),.37,
           pan=.26,bright=.40,phrase="the moving answer",offsets=(0.,2.25,4.1,6.7,8.6,11.3))
    light(40.15,81,.19,2.4,pan=.41)
    light(46.5,86,.17,2.2,pan=-.35)

    # The texture opens: separated pairs answer longer phrases, not a perpetual ostinato.
    harmony=[(48.,34),(54.,36),(60.,41),(66.,43),(72.,34),(78.,45)]
    felt_lines=[(62,65,69,74),(64,67,72,69),(65,69,72,76),
                (67,70,74,69),(65,69,74,77),(64,69,73,76)]
    for block,((start,bass),pitches) in enumerate(zip(harmony,felt_lines)):
        ground(start,bass,4.55,.30+.016*block,fifth=block in (2,4),phrase="harmonic direction")
        melody("felt",start+.25,pitches,1.,(1.0,1.35,1.05,1.55),.54+.025*block,
               pan=-.23,bright=.48+.02*block,phrase="spaced pairs",offsets=(0.,.76,2.7,3.54))
        n("felt",start+5.0,pitches[1]-12,.9,.31,pan=-.08,bright=.32,phrase="a lower punctuation")
        if block%2==0:
            n("pulse",start,bass+12,.18,.30,pan=-.14,phrase="a displaced footing")
            n("pulse",start+3.54,bass+12,.15,.25,pan=.15,phrase="a displaced footing")
    melody("breath",49.5,(69,67,65,64,62,65,67,69,70,69,67,64),1.,
           (1.8,1.5,2.2,1.5,2.6,1.4,2.4,1.3,1.5,2.8,1.3,2.1),.47,
           pan=.26,bright=.46,phrase="a long independent answer",
           offsets=(0.,2.4,5.1,7.6,10.1,13.7,16.5,19.8,22.4,24.5,28.1,31.0))
    for start,pitch in ((53.1,81),(64.0,84),(70.8,86),(80.1,88)):
        light(start,pitch,.19 if start<70 else .24,2.6,pan=-.39 if pitch==84 else .39)
    # The last approach gathers rhythm, then leaves a short inhalation before the crest.
    melody("felt",83.0,(64,67,69,73,76,81,76),1.,(.75,.7,.62,.85,.82,.92,.7),.68,
           pan=-.10,bright=.64,phrase="the first approach",offsets=(0.,.48,1.,1.54,2.05,2.7,3.55))
    n("breath",84.1,67,2.2,.43,pan=.23,bright=.52,phrase="held against the approach")
    n("pulse",84.0,57,.18,.36,phrase="the last small step")
    n("pulse",85.55,57,.15,.31,pan=.14,phrase="the last small step")

    # III. First crest: the source leads while the answering line reaches a ninth.
    ground(88.,38,7.2,.48,fifth=True,phrase="first wide D")
    call(88.3,scale=1.18,strength=.86,pan=-.12,phrase="the complete call at the first crest")
    melody("breath",88.9,(77,76,74,81,79,77),1.,(2.1,2.25,1.55,2.6,1.4,2.1),.56,
           pan=.23,bright=.64,phrase="an upper suspended answer",offsets=(0.,2.45,5.2,7.6,10.8,12.9))
    ground(96.0,41,4.1,.40,phrase="a first glimpse of warmth")
    ground(101.,34,4.2,.38,fifth=True,phrase="crest broadens")
    melody("felt",96.2,(74,77,81,79,76,74,69,65),1.,(1.15,1.0,.9,1.25,1.05,1.2,1.15,1.4),.72,
           pan=-.13,bright=.61,phrase="the source's broad descending line",
           offsets=(0.,.9,1.9,3.0,4.6,5.6,7.05,8.55))
    for start,pitch,level in ((89.1,86,.28),(94.6,88,.28),(99.5,81,.24),(104.2,86,.20)):
        light(start,pitch,level,3.0,pan=-.4 if pitch==88 else .4,phrase="first crest glints")
    for k,start in enumerate((88.,90.4,92.0,94.4,97.1,100.,102.6)):
        n("pulse",start,50 if start<96 else 53,.19,.39 if k%3==0 else .29,
          pan=-.13 if k%2 else .12,phrase="crest articulation")
    ground(106.,43,3.2,.30,phrase="the first thinning")
    melody("breath",105.5,(74,72,69,67),1.,(1.5,1.25,1.75,1.15),.36,
           pan=.20,bright=.37,phrase="the answer descends",offsets=(0.,1.85,3.5,5.4))
    melody("felt",107.0,(62,65,64,69),1.,(1.1,.9,1.25,1.3),.48,
           pan=-.18,bright=.36,phrase="a call becoming incomplete",offsets=(0.,.8,1.6,3.4))

    # IV. The last phrase never reaches its high D. Felt and its room cease at 118 s.
    ground(112.3,45,3.8,.22,phrase="the unsupported question")
    melody("felt",112.4,(62,65,64,69),1.,(.85,.70,1.15,1.0),.39,
           pan=-.21,bright=.23,phrase="the source's last incomplete call",offsets=(0.,.85,1.65,3.5))
    n("breath",114.75,64,2.8,.25,pan=.25,bright=.24,release=.7,phrase="an unfinished answer")
    light(116.65,81,.09,1.4,pan=.38,phrase="the last residual light")

    # V. A stretched familiar call passes between bodies; the original source never returns.
    inherited=[("breath",122.65,62,2.4,.34,.24),
               ("glass",124.50,77,3.0,.16,-.34),
               ("breath",126.206,64,3.1,.31,.20),
               ("bow",129.454,57,3.3,.26,-.1),
               ("breath",133.99,74,3.75,.38,.18)]
    for role,start,pitch,duration,level,pan in inherited:
        n(role,start,pitch,duration,level,pan=pan,bright=.30,phrase="the augmented call elsewhere")
    ground(126.6,38,4.9,.18,phrase="a fragile returned ground")
    light(138.15,81,.13,3.1,pan=-.38,phrase="one retained edge")
    melody("breath",139.2,(69,67,65,64),1.,(2.5,1.8,2.3,2.2),.29,
           pan=.22,bright=.30,phrase="the changed answer",offsets=(0.,3.15,5.5,9.25))
    ground(140.5,34,3.9,.19,phrase="a quiet B flat")
    ground(149.0,41,4.15,.22,phrase="the new ground is offered")
    light(152.0,84,.13,2.7,pan=.38,phrase="a warmer possibility")
    n("breath",153.25,69,1.55,.25,pan=.2,bright=.33,phrase="a handoff")

    # VI. A new bowed thread leads; F major recasts the old D-minor call as an added-sixth relation.
    # Longer shaped lines alternate with short replies. This arc has different ownership and metre.
    warm_ground=[(156.,41),(164.,34),(172.,36),(180.,38),(188.,43),(196.,34),(204.,36)]
    for k,(start,bass) in enumerate(warm_ground):
        ground(start,bass,6.4,.25+.025*k,fifth=k in (3,5),phrase="the collective warm ground")
    thread_phrases=[
        (156.25,(62,69,65,64,62),(0.,1.9,3.4,5.0,6.3),(1.65,1.25,1.35,1.1,1.7),.37),
        (164.3,(65,69,74,72,69),(0.,1.45,2.9,4.6,6.2),(1.2,1.15,1.4,1.3,1.6),.40),
        (172.2,(67,72,76,74,72,69),(0.,1.1,2.5,4.0,5.25,6.5),(1.0,1.2,1.3,1.0,1.0,1.4),.45),
        (180.15,(74,72,69,67,65,64),(0.,1.3,2.75,4.0,5.25,6.55),(1.1,1.25,1.1,1.1,1.1,1.1),.48),
        (188.15,(67,70,74,77,76,74),(0.,1.15,2.45,3.9,5.2,6.55),(1.0,1.15,1.3,1.1,1.15,1.35),.53),
        (196.25,(74,77,81,79,77,74),(0.,1.25,2.6,4.25,5.65,6.65),(1.1,1.2,1.5,1.3,.9,1.3),.56),
        (204.1,(76,79,81,84),(0.,.9,1.9,3.0),(.8,.9,1.0,1.4),.57),
    ]
    for start,pitches,offsets,durations,level in thread_phrases:
        melody("thread",start,pitches,1.,durations,level,pan=-.15,
               bright=.39+(start-156.)/160.,phrase="a new shared line",offsets=offsets)
    melody("breath",157.5,(69,72,77,76,74,72,69,67,65,69,74,76),1.,
           (2.2,2.1,2.8,2.3,2.6,2.0,2.4,1.6,2.5,2.3,2.0,2.1),.40,
           pan=.25,bright=.44,phrase="a companion rather than a double",
           offsets=(0.,3.3,7.2,11.0,15.4,19.1,22.8,26.3,29.2,33.0,36.6,40.2))
    melody("breath",198.55,(77,79,81,79,77),1.,(1.6,1.8,2.0,1.3,1.5),.52,
           pan=.24,bright=.59,phrase="a collective answering crest",offsets=(0.,2.0,4.1,6.65,8.35))
    for k,(start,bass) in enumerate(warm_ground[1:]):
        for j,offset in enumerate((.35,2.8,5.1)):
            n("pulse",start+offset,bass+12,.16,.18+.024*k+(.045 if j==0 else 0),
              pan=-.15 if j%2==0 else .16,bright=.31,phrase="motion belongs to the group")
    for start,pitch,level in ((160.8,81,.14),(170.9,86,.17),(177.7,84,.20),
                            (186.7,81,.20),(194.65,86,.24),(202.75,89,.26),(207.05,88,.23)):
        light(start,pitch,level,2.7,pan=-.40 if pitch in (84,89) else .4,phrase="a collective high edge")

    # VII. Recognition in a changed harmonic context, not resurrection of the missing source.
    ground(208.,41,6.5,.39,fifth=True,phrase="the same call has another home")
    call(208.35,"thread",scale=1.8,strength=.57,pan=-.13,
         phrase="the familiar call in F's light")
    melody("breath",209.25,(72,69,67,65,64),1.,(2.6,2.2,2.8,2.0,2.6),.39,
           pan=.23,bright=.42,phrase="the recognition counterline",offsets=(0.,3.0,5.75,9.2,12.0))
    light(215.65,86,.20,3.3,pan=.37,phrase="the recognized high D")
    ground(216.,34,4.5,.30,phrase="the response holds the change")
    melody("thread",218.4,(77,76,74,69),1.,(1.3,1.45,1.8,2.0),.37,
           pan=-.15,bright=.37,phrase="the new voice lets go",offsets=(0.,1.6,3.4,5.9))
    ground(222.,45,4.8,.25,phrase="an open bridge to the end")

    # VIII. The last attacks precede the final held image. Twelve seconds are allowed to release.
    ground(227.5,38,7.5,.24,fifth=True,phrase="the final held world")
    n("breath",227.7,64,5.5,.20,pan=.21,bright=.22,attack=.6,release=2.6,
      phrase="the remembered ninth")
    n("thread",227.8,62,5.6,.22,pan=-.13,bright=.21,attack=.42,release=2.4,
      phrase="the last carried note")
    light(227.65,69,.11,5.0,pan=-.32,phrase="one remaining reflection")

    score=RiverScore(
        duration=240.,events=events,silence=(119.6,122.2),source_leaves=118.,
        title="A River Twice / Full film score",preset="full",withdrawn_roles=("felt",),
        mute_after={"felt":118.},
        extra_instruments={"thread":"A softly articulated bowed harmonic strand; enters only after the source has withdrawn."},
        sections=[(0.,32.,"A first shared form"),(32.,88.,"What passes between"),
                  (88.,112.,"The first large return"),(112.,119.6,"Withdrawal"),
                  (119.6,122.2,"No answer"),(122.2,156.,"The familiar call, elsewhere"),
                  (156.,208.,"A collective rising"),(208.,228.,"Recognition in another light"),
                  (228.,240.,"The held world")],
        cues=[Cue(1.1,"first-contact","A close D begins and leaves a visible mark."),
              Cue(5.15,"first-reach","The high D reaches another place."),
              Cue(10.25,"answer","A different breath-like voice answers."),
              Cue(21.4,"shared-form","The material relation can be seen as a shared form."),
              Cue(32.,"interlock","Short cells begin to pass between bodies."),
              Cue(48.,"open-texture","The accompaniment separates into pairs and a sustained answer."),
              Cue(64.,"higher-edge","A new high edge accompanies the wider field."),
              Cue(78.,"gather","The harmonic ground turns toward A."),
              Cue(88.,"first-crest","D returns at the first large visual scale."),
              Cue(96.,"crest-turn","The phrase descends while the answering register stays open."),
              Cue(106.,"thinning","The first crest gives way to incomplete statements."),
              Cue(112.4,"last-source-phrase","The source begins a call that never reaches its high D."),
              Cue(115.9,"last-source-note","The last felt A has no final answer."),
              Cue(118.,"source-absent","Both source and its room are fully absent."),
              Cue(119.6,"silence","Exact zero in all music and synthetic room."),
              Cue(122.65,"altered-return","The familiar call begins in another voice."),
              Cue(133.99,"inherited-high-D","The distributed augmented call reaches its high D."),
              Cue(149.,"new-ground","A low F offers another harmonic reading."),
              Cue(156.25,"new-thread","A different bowed strand begins a collective line."),
              Cue(172.,"collective-motion","The new phrase acquires direction and a shared pulse."),
              Cue(188.,"second-rise","The collective counterpoint expands its register."),
              Cue(202.75,"collective-high-edge","The highest glint in the new harmonic field."),
              Cue(208.,"recognition","The old call returns in the warmer new context."),
              Cue(215.65,"recognized-high-D","The familiar high D is carried without its source."),
              Cue(227.8,"last-attack","No new musical attack follows this point."),
              Cue(228.,"held-world","A twelve-second release leaves the changed image.")])
    score.validate()
    return score


def get_score(preset="miniature") -> RiverScore:
    if preset == "miniature":
        return miniature()
    if preset == "full":
        return full_score()
    raise ValueError(f"Unknown score preset: {preset}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--preset",choices=("miniature","full"),default="miniature")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(get_score(args.preset).manifest(), indent=2)+"\n")


if __name__ == "__main__":
    main()
