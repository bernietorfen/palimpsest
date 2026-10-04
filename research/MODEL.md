# The PALIMPSEST instrument

PALIMPSEST is an authored dynamical instrument. Its material, audible tuning and appearance are designed rules. It is not a calibrated constitutive law, an eigenfrequency solver, a fracture simulation or a model of biological memory.

## State and domain

The numerical domain is a periodic 128 by 128 grid. At every cell it stores displacement `u`, velocity `v`, a plastic rest-shape field `p` and a fatigue field `z`. All four fields are dimensionless. The score uses a timestep of 1/96 second. Spatial differences use a five-point periodic Laplacian, multiplied by `(N/128)^2` when the grid size changes.

Twelve authored spatial patterns provide both force shapes and readout weights. Each pattern is a mean-zero, RMS-normalized mixture of three Fourier components, with a distinct phase offset. They are not asserted to be mutually orthogonal or to be the physical normal modes of the sheet. Their integer wave numbers and exact construction are in `studio/material.py`.

## A single integration step

Let `h` be the timestep and `d = u - p`. Before advancing the state, form the force from the current score envelopes and the entry at the read position of the delay buffer. The motion update is:

```
a = T*Lap(u) - B*Lap(Lap(u))
    - k*(1 - 0.58*z)*d - c*d^3 + F
v_next = (v + h*a) / (1 + h*gamma)
u_next = u + h*v_next
```

The selected film uses `T=1.2`, `B=0.08`, `k=2.4`, `c=0.7` and `gamma=0.38`. The optional variable-tension buckling study is not used in the film.

Writing and wear are then evaluated from the new displacement and the previous rest shape:

```
s = u_next - p
excess = max(abs(s) - 0.095*(1 - 0.35*z), 0)
capacity = max(1 - (p/0.8)^2, 0)
write = 0.32*excess*tanh(s/0.035)
p_next = clip(p + h*(write*capacity - lambda*p + 0.035*Lap(p)), -0.8, 0.8)
z_next = clip(z + h*(0.26*excess^2*(1-z) - 0.001*z), 0, 1)
```

The baseline forgetting rate `lambda` is 0.0008. Between 308 and 358 seconds the score adds a smooth pulse `0.055*sin(pi*(t-308)/50)^2`. Fatigue has its own slower recovery. Wear therefore outlasts this erasure interval; it is not mathematically permanent.

## Memory, pitch and the returning force

For pattern `psi_j`, the signed inscription readout is the spatial mean `m_j = mean(p*psi_j)`. The fatigue readout is `q_j = mean(z*psi_j^2)/mean(psi_j^2)`. The audible carrier frequency is explicitly mapped as:

```
f_j = f0_j * sqrt(1 - 0.58*q_j) * exp(0.65*m_j)
```

The twelve unworn pitches, in Hz, are `110, 137.5, 146.6666667, 165, 183.3333333, 220, 247.5, 275, 293.3333333, 330, 366.6666667, 440`. This is an artistic tuning rule, not an eigenvalue calculation. The simulation does not resolve these audio-rate oscillations.

The phase of each delayed spatial force pattern advances by `h*2*pi*0.018*(f_j-f0_j)`, using the newly updated memory and fatigue, and wraps modulo `2*pi`. The coefficient maps audible frequency differences into slow geometric phase. It does not make the material timestep an audio sample interval.

The returning force combines a shifted pattern and an authored quadrature pattern using the cosine and sine of this phase. The shift is `(N//7, N//11)` cells. For each voice, the amplitude is `tanh(buffer_entry/0.18)`. The score supplies the feedback gain. The external force has gain 1.6. Exact update order is:

1. Read the current delay-buffer entry and phase; evaluate the external and returning forces.
2. Advance `v`, `u`, `p` and `z` in the order above.
3. Advance the echo phases from the new tuning.
4. Write the newly projected velocity into the buffer entry and advance the circular index.

The nominal delay is 0.79 seconds, rounded to an integer number of buffer slots: 76 at 96 steps/s, 152 at 192 steps/s and 303 at 384 steps/s. Temporal refinement therefore also changes delay quantization. The discrete buffer procedure, rather than a continuous-delay approximation, defines the recorded instrument.

## From state to sculpture

The numerical grid remains periodic and intact. A separate authored chart rolls it into an open, twice-turned sheet. Its coordinates are `s` in `[-1,1]` and `phi` in `[-pi,3*pi]`:

```
x = s*(1.34 + 0.055*sin(2*phi))
theta = x*2*pi/2.8
uv = (x/2.8 + 0.5, phi/(4*pi) + 0.5)
r = 0.55 + 0.072*phi + 0.048*sin(3*phi+theta) + 0.038*cos(4*theta+phi)
    + 0.085*tanh(1.6*u(uv)) + 0.13*tanh(2.1*p(uv))
y = 0.22*sin(1.8*x) + r*sin(phi)
z_geometry = 0.13*sin(2.2*x+0.4) + r*cos(phi)
```

Two radial offsets, `r +/- 0.013`, create front and back surfaces. The visible chart is clipped where fatigue exceeds `0.56 + 0.30*sin(2*theta+4*phi) + 0.16*cos(5*theta-phi)`. New boundary walls close every cut. These openings encode wear visually; they are not simulated cracks and do not remove cells from the numerical instrument.

Pigment depends on the retained inscription and a contour phase `47*p + 16*u`. Fourier reconstruction supplies smooth periodic fields for geometry and shading. Camera, light, material palette, focus and captions are composed separately. The returning phrase repeats its opening camera path exactly, offset by 352 seconds.

## Sound

The twelve continuous-phase voices use eight slightly inharmonic partials with a bowed spectral envelope. Fatigue attenuates high partials; material velocity adds a quiet displaced ringing partial. New fatigue controls filtered abrasion noise. A synthetic room response uses seed `20261003`. No recorded samples, trained models or externally generated sound assets are used. The complete synthesis is in `studio/sound.py`.

The delivery soundtrack applies only a measured constant gain of 5.09 dB to the synthesis. It remains 432 seconds, 48 kHz, stereo PCM24. Measured delivery loudness is -18.07 LUFS and true peak -2.67 dBTP. The assistant has not had a supported perceptual audition path; signal checks do not establish listening quality.

## What the experiments establish

The controlled history comparison writes the same five gestures in forward and reverse order. It then resets `u=p`, `v=0`, echo phase and delay to zero before applying the same three-gesture probe. This sets zero local elastic strain; spatial coupling means it is not necessarily a full static equilibrium. The histories have the same input gesture multiset, not proven equal mechanical work.

The forward/reverse pitch difference is 0.933236 Hz RMS at the production timestep. At 1/192 and 1/384 second it is 0.919774 and 0.912437 Hz. These checks support persistence of this finite-grid order effect under temporal refinement. They do not prove continuum convergence or global stability.

Erasing both retained fields reproduces the fresh probe exactly. Erasing only the inscription leaves an 11.655983 Hz RMS difference from fresh; erasing only fatigue leaves a 7.690189 Hz difference. These are interventions on the authored system, with all transient state reset consistently. The two effects interact and should not be added as independent contributions.

The film's first and returning phrase differ by approximately 466 cents RMS across voice/time readouts. That is a comparison inside an evolving composition, not the controlled order experiment. These two results answer different questions and should not be conflated.

All reported results are deterministic numerical records. No statistical population, listening study, physical specimen, universal novelty claim or scientific priority claim is implied.
