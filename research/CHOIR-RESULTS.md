# Encounter and absence: results

The locked protocol asks whether a body that receives no direct writing gesture
can retain a changed reply after the connection and transient motion are gone.
The answer is yes in all 48 evaluated receiver cases of this finite model.

The plan in `CHOIR-PROTOCOL.md` was fixed after three exploratory studies and
before the twelve evaluation phrases. It is an internal locked plan, not an
independent preregistration or a random sample from a population.

The exploratory record includes the weak outcomes. In exploration 001, case 0
at bridge tension 0.35 gives receiver 1 a difference of 0.008017 Hz RMS and
receiver 2 exactly zero. Exploration 002 increases contact/port overlap and
drive while changing more than one parameter; its corresponding case gives
1.209268 and 0.060814 Hz. Exploration 003 checks timestep sensitivity before
the formal plan. These trials informed the construction. They neither isolate
which parameter caused the improvement nor count as held-out successes.

## Controlled transfer

Only source 0 receives the four writing contacts. Two reciprocal spring chains
join source 0 to receiver 1 and receiver 1 to receiver 2. After 30 seconds every
link is cut. Each condition sets its displacement to its own retained
inscription, clears velocity, delayed feedback and phase, then receives the same
quiet twelve-second modal question. The source stays disconnected and receives
no probe. A never-connected writing control receives the same later question.

The primary number is the RMS difference of all twelve saved pitches across
289 probe times, relative to the isolated-write control.

| Steps per second | Receiver | Minimum Hz | Median Hz | Maximum Hz |
|---|---|---:|---:|---:|
| 96 | First neighbour | 1.447102 | 1.704590 | 2.107750 |
| 96 | Second neighbour | 0.250035 | 0.424034 | 0.622229 |
| 192 | First neighbour | 1.441132 | 1.696467 | 2.098791 |
| 192 | Second neighbour | 0.248210 | 0.422229 | 0.619778 |

Every receiver contains nonzero inscription and wear before the probe. All 48
primary values exceed the declared 0.01 Hz admission threshold. Erasing both
retained fields reproduces the isolated control exactly. Cutting the second
link throughout writing makes receiver 2 match that control exactly too.

The largest paired relative difference on halving the timestep is 0.735157%.
This is timestep sensitivity at one fixed spatial grid, not a continuum proof.
An independently written analysis checks 104 files, reconstructs every field
erasure and recomputes the numbers. Its largest discrepancy from the generation
reports is 4.45e-16 Hz. It does not independently reimplement the dynamics.

Partial erasure is not an additive decomposition. Both retained fields alter
later dynamics and pitch; their effects can oppose each other. For example,
phrase 0 at 96 steps per second gives receiver 1 primary difference 1.553793 Hz,
inscription-erased difference 1.397061 Hz and wear-erased difference 0.608499 Hz.
With the second link absent, that first receiver changes by 2.472227 Hz instead:
the outgoing load changes how the first neighbour is written. All partial
ablation results remain in the record, without a monotonicity claim.

## The composed seven-body performance

The film is a separate 288-second composition on seven 64 x 64 bodies. B receives
all writing contacts. The six other bodies receive the same small question at
5 and 248 seconds. The first question leaves exactly zero retained inscription
in the six listeners. Connections enter, transmit gestures and fade to zero by
236 seconds. The source's visual departure begins only after that cut.

At 242 seconds a disclosed intervention sets displacement to retained
inscription and clears velocity, delayed feedback, phase and bridge motion.
The material then evolves for six seconds before the returning question.
The following RMS values compare the half-open forty-second windows at 96 Hz:

| Listener | Changed pitch, RMS Hz |
|---|---:|
| A | 3.410914 |
| C | 4.052326 |
| D | 0.006422 |
| E | 0.000000 |
| F | 0.010063 |
| G | 4.694452 |

These are observations within a score, rather than additional controlled
transfer cases. The film's mix and camera are composed. The separate listening
piece removes the camera mix and uses common synthesis phases, filtering and
one common gain. E's saved pitch, amplitude and fatigue controls agree exactly;
its synthesized PCM does too. Both E choices intentionally point to the same
encoded file. The portraits use common lighting and a common pose for each
before/after pair. Their geometry is an artistic embedding of recorded fields.

## Where persistence lives

`CHOIR-ENERGY.md` gives a restricted structural result: with inscription and
wear frozen, feedback and drive disabled, and positive bridge strengths held
fixed, the continuous finite-grid mechanical system has a strictly convex
potential and positive damping. It approaches a unique equilibrium. Its
linearized mechanical propagator has no unit-modulus carrier. Adding frozen
retained coordinates supplies the identity block that survives.

The accompanying Galerkin calculation retains thirteen coordinates per body
and all 192 beads: 283 positions and 566 mechanical state coordinates. It uses
the performance's retained fields at 228 seconds, with all bridges reconnected.
The equilibrium gradient is below 1.09e-13. The continuous energy identity agrees
within 1.43e-14; the largest generator real part is -0.12000005. The 1/96-second
linearized step has spectral radius 0.99875234. A separately computed discrete
Lyapunov metric is positive definite, with residual below 3.75e-8.

This numerical reduction is explicitly not a full-grid spectrum. The energy
argument does not cover the driven, plastic, delayed-feedback artwork.
No quantum recurrence conclusion is claimed for this material.
