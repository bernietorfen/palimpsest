# Encounter and absence: second-act validation protocol

Fixed on 4 October 2026 after the three explicitly exploratory transfer studies,
and before running the held-out phrase set below. This is an internal locked
validation plan, not an independently preregistered experiment.

## Question

Can a body that receives no direct gesture retain an altered response after its
connections are removed, all transient motion is cleared, and the original
source is absent from the probe?

The spring chains and standard spatial projections are established numerical
ideas. The authored contribution is this material law, reciprocal spatial-port
coupling, score, sculptural embedding and experiment. This study does not assert
world priority, biological memory, continuum convergence, physical acoustics or
passivity of the full active plastic system.

## Fixed setup

Use three 64 by 64 materials, sixteen masses per bridge, step 1/96 second,
feedback 0.08, total bridge mass 0.65, damping 0.24 and tension 1.6. Port width is
0.16 with unit spatial RMS. Connect source 0 at (0.19, 0.37) to receiver 1 at
(0.71, 0.53), then receiver 1 at (0.58, 0.50) to receiver 2 at (0.71, 0.53).
These settings were informed by exploration 002; none is a held-out discovery.

Write for 30 seconds using only source 0. Twelve held-out phrases use four
onsets at 2, 8, 15 and 22 seconds, with 0.7-second raised-cosine attack,
0.8-second hold and 3.0-second raised-cosine release. For phrase index j from
0 through 11 and event k from 0 through 3:

- amplitude = 0.65 + 0.07 * ((j + 2*k) mod 5)
- polarity = -1 when (j + 3*k) mod 4 equals 0, otherwise +1
- source contact x = 0.19 + 0.025 * (((j + k) mod 3) - 1)
- source contact y = 0.37 + 0.025 * (((2*j + k) mod 3) - 1)

The held-out set is deterministic and fully disclosed. It is not a random
sample from a population, and no population significance test will be reported.

Simulate these writing conditions separately for every phrase:

1. Both links active.
2. Both links absent throughout.
3. The second link absent throughout.

After writing, cut every link. From the connected written state construct
additional probe conditions by clearing only inscription p, only wear z, or
both p and z. For every probe condition, initialize displacement u to its own
retained p, clear velocity, delay and echo phase, and reset the clock. The
source receives no further gestures and remains disconnected. No source signal
is mixed into the receivers' measured responses.

Apply the same low-amplitude modal question to receivers 1 and 2: modes 0, 4
and 8 at 1, 4 and 7 seconds, each with amplitude 0.025, 0.5-second attack,
0.4-second hold and 1.6-second release. Probe for twelve seconds; capture all
twelve pitches at 24 Hz, including the initial state. No fitted readout.

## Outcomes and reporting

Primary: for each receiver and phrase, RMS pitch difference in hertz between
connected-write and isolated-write responses across all times and twelve
modes. Report every case, the minimum, median and maximum. Do not discard weak
or negative cases. A retained-transfer demonstration requires nonzero retained
fields before the probe and a primary difference above 0.01 Hz in both
receivers for every held-out phrase.

Negative controls: the both-erased connected state and the isolated-write
receiver must match within 1e-6 Hz. Receiver 2 with the second writing link
absent must also match the isolated-write receiver within 1e-6 Hz. Partial
field erasure is an attribution ablation; it has no predeclared monotonicity
requirement. Report its entire result even if the effects cancel or reverse.

Sensitivity: repeat all twelve phrases at step 1/192 second. Report paired
primary differences and the largest relative discrepancy. This is timestep
sensitivity for this finite model, not a proof of a continuum limit.

Preserve exact generation source and protocol before execution, full written
states, all probe readouts, metadata and per-file SHA-256 values. Verify the
reported measures independently from saved arrays, with separately written
analysis code. Record failed admission criteria and reruns explicitly.
