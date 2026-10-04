# A clock for the quiet choir — results

The declared 14:15 UTC analysis gives a conservative global bound for the
finite, continuous-time frozen equations. With all twelve links held at full
strength, the excess mechanical energy obeys

    E(t) <= min(1, 2.59*exp(-0.096*t))*E(0).

It is below one percent of its initial value by 60 seconds. For the separate
bodies, with mechanically disconnected bead coordinates omitted,

    E(t) <= min(1, 1.81*exp(-0.187*t))*E(0),

which is below one percent by 30 seconds. These are upper bounds about each
fixed history's own equilibrium. They neither order actual trajectories nor
prove contraction between different retained histories.

The proof in `CHOIR-DECAY.md` uses the complete finite grid and its actual
RMS-normalized ports. It does not use the modal reduction to establish its
stiffness bound. The body contribution gives 0.2057142857 and the chain
contribution gives 4.5333333333, so the admitted mass-metric lower bound 0.20
is conservative. The separate bodies admit the rounded lower bound 1.00.

## Exact arithmetic behind the rounded statements

For the full scene, the modified-energy proof gives exactly

    rate = 20/(163+20*sqrt(5)),
    prefactor = (163+20*sqrt(5))/(125-20*sqrt(5)).

The elementary bounds 2.236<sqrt(5)<2.237 certify rate>0.096 and
prefactor<2.59. For separate bodies, the exact values are rate=950/5061>0.187
and prefactor=5061/2800<1.81. Thirteen positive terms of the exponential
series, evaluated as exact rational numbers, certify the stated one-percent
ceilings at 60 and 30 seconds. The final report stores their complete integer
numerators and denominators. The rounded statements do not depend on trusting
a floating-point exponential near a threshold.

The unrounded modified-energy constants give respective one-percent upper
bound times of approximately 57.704 and 27.687 seconds. These evaluated times
are descriptive; the simple rounded statements above have the rational checks.

## Independent computational checks

- Endpoint/chain inequality matrices for 4, 16 and 64 beads have minimum
  eigenvalues 0.187505, 0.269683 and 0.293819 respectively.
- Thirty-six full-grid perturbations, across 16, 32 and 64 samples per side,
  satisfy the baseline stiffness and chain mass inequalities. The largest
  port RMS-squared discrepancy is 4.45e-16.
- The existing 228-second retained fields and nonlinear Galerkin potential
  reproduce the equilibrium with maximum gradient residual 1.102e-13.
- Twenty-six nonlinear modified-energy checks include pure bead velocity,
  pure body velocity, displacement-only cases and seeded mixed perturbations.
  All comparison and dissipation inequalities pass. The largest normalized
  derivative-identity error is 1.980e-16.

`choir-decay-bound-003.json` records all cases and exact input/source hashes.
The earlier two records remain in the private production history. The last
revision adds explicit guards for the declared damping and wear domain; it
does not change the bound or any observed numerical result.

The retained fields are fixed by the assumptions. The active material has
writing, diffusion, slow forgetting, delayed feedback and changing links.
No bound for its complete driven motion, numerical timestep, hearing response
or continuum limit is claimed. The numerical cross-checks support the written
algebra; they are not a formal proof assistant certificate.
