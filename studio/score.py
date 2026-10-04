"""The authored excitation score for PALIMPSEST.

This file composes control gestures, not pre-existing audio. Audible carriers
will be synthesized from the material's readout and the resulting score.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import math
import numpy as np


@dataclass(frozen=True)
class Gesture:
    time: float
    voice: int
    strength: float
    attack: float
    hold: float
    release: float
    polarity: float = 1.0

    def at(self, time: float) -> float:
        age = time - self.time
        if age < 0 or age > self.attack + self.hold + self.release:
            return 0.0
        if age < self.attack:
            envelope = math.sin(math.pi * age / (2 * self.attack)) ** 2
        elif age < self.attack + self.hold:
            envelope = 1.0
        else:
            envelope = math.cos(math.pi * (age - self.attack - self.hold)
                                / (2 * self.release)) ** 2
        return self.polarity * self.strength * envelope


class Score:
    """Six movements; seed phrase and final probe are deliberately identical."""

    duration = 432.0
    names = ("I. An impression", "II. What is kept", "III. A reply",
             "IV. Too much to hold", "V. What is lost", "VI. The same question")

    def __init__(self) -> None:
        gestures: list[Gesture] = []
        # An authored five-note question, including its irregular breathing spaces.
        self.phrase = ((0., 0, .34), (7.5, 4, .24), (16.5, 2, .31),
                       (27., 7, .18), (39., 3, .29))
        for start in (18., 370.):
            for offset, voice, level in self.phrase:
                gestures.append(Gesture(start + offset, voice, level, 1.4, .4, 4.5))
        # Written strata: the question returns in fragments and changing registers.
        for cycle, start in enumerate((77., 96., 118., 140.)):
            for j, (offset, voice, level) in enumerate(self.phrase[:4]):
                gestures.append(Gesture(start + offset * .42, (voice + cycle * 2) % 12,
                                        level * (.82 + cycle * .12), 1.1, .8, 5.,
                                        -1 if (cycle + j) % 5 == 0 else 1))
        # Response: interlocking calls leave a real interval for the delayed sheet.
        for j in range(18):
            gestures.append(Gesture(154. + j * 3.1, (j * 5 + 2) % 12,
                                    .13 + .035 * (j % 4), .45, .25, 2.2,
                                    -1 if j % 3 == 0 else 1))
        # Saturation has an explicit arc; density is not uniform random triggering.
        for j in range(34):
            phase = j / 33
            gestures.append(Gesture(224. + 1.42 * j, (j * 7 + j // 5) % 12,
                                    .16 + .37 * math.sin(math.pi * phase) ** 2,
                                    .16 + .35 * (1 - phase), .25, 2.3,
                                    -1 if j % 4 in (1, 2) else 1))
        gestures.append(Gesture(280., 0, .16, 2., 1., 7.))
        self.gestures = tuple(sorted(gestures, key=lambda g: g.time))

    def excitation(self, time: float) -> np.ndarray:
        values = np.zeros(12, dtype=np.float32)
        for gesture in self.gestures:
            if gesture.time > time:
                break
            values[gesture.voice] += gesture.at(time)
        return values

    def controls(self, time: float) -> dict[str, float]:
        if time < 72:
            feedback = .08
        elif time < 144:
            feedback = .08 + .12 * (time - 72) / 72
        elif time < 216:
            feedback = .20 + .12 * math.sin(math.pi * (time - 144) / 72) ** 2
        elif time < 288:
            feedback = .23
        elif time < 360:
            feedback = .17 * max(0, 1 - (time - 288) / 54)
        else:
            feedback = .08
        forgetting = .0008
        if 308 < time < 358:
            forgetting += .055 * math.sin(math.pi * (time - 308) / 50) ** 2
        return {"feedback": feedback, "forgetting": forgetting}

    def manifest(self) -> dict:
        return {"duration": self.duration, "movements": list(self.names),
                "gestures": [asdict(g) for g in self.gestures],
                "note": "Original control score; synthesis is driven by material readouts."}
