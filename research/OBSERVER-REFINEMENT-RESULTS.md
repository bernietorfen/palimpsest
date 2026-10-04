# A moving origin and a third timestep

The nearer receiver's six original cross-timestep matching errors are explained
by a specific geometric effect in this data: a shift common to the complete
collection moves those comparisons across their equal-distance boundaries.
A further timestep halving also removes those six raw-reader errors. The earlier
18/24 result remains unchanged in the published v2.0.0 record.

This investigation was explicitly declared after the original result in
`OBSERVER-REFINEMENT-PLAN.md`. It adds an openly post-result diagnostic and a
fixed third timestep. It does not change the original gate or claim a new
reader of one unknown history.

## The collection's origin

Use the RMS inner product on the 3,468 coordinates of each reply: twelve pitches
at 289 times. Let C_h and F_h be paired coarse and fine replies. For all 24
histories, define delta_h = F_h - C_h, the common shift mu = mean_h(delta_h),
and the remainder eta_h = delta_h - mu. The ordinary Euclidean identity is

    mean_h ||delta_h||^2 = ||mu||^2 + mean_h ||eta_h||^2.

| Rates | Receiver | Total discrepancy RMS Hz | Common shift RMS Hz | Remainder RMS Hz | Common share of mean squared discrepancy |
|---|---|---:|---:|---:|---:|
| 96 / 192 | Near | 0.008470617 | 0.008435617 | 0.000769228 | 99.1753% |
| 96 / 192 | Distant | 0.002069465 | 0.002031243 | 0.000395898 | 96.3403% |
| 192 / 384 | Near | 0.004174057 | 0.004151771 | 0.000430747 | 98.9351% |
| 192 / 384 | Distant | 0.001017142 | 0.000998896 | 0.000191793 | 96.4445% |

Translate every fine reply by the same -mu and repeat the original nearest-
history comparison. This preserves all differences within that fine collection.
The mean needs the complete balanced set of twenty-four histories. It is not
estimated from one unknown response, and is not a held-out test.

| Comparison | Near raw | Distant raw | Near aligned | Distant aligned |
|---|---:|---:|---:|---:|
| 96 to 192 | 18 / 24 | 24 / 24 | 24 / 24 | 24 / 24 |
| 192 to 384 | 24 / 24 | 24 / 24 | 24 / 24 | 24 / 24 |

The diagnostic therefore does not establish that distance gives a better
memory. The original raw count differs between the two chosen receivers; that
count difference disappears in the new timestep pair. Neither observation is
a general comparison of receivers or a causal account of the dynamical origin
of numerical bias.

## The six decisions, without a fitted model

For an original wrong choice j of history h, set d = C_h - C_j. Its squared-
distance advantage decomposes exactly as

    ||F_h-C_j||^2 - ||F_h-C_h||^2
      = ||d||^2 + 2<mu,d> + 2<eta_h,d>.

A negative left side favours the wrong history. All six original pairs have a
negative value before alignment and a positive value after removing the common
term. Every term, raw choice, aligned choice, full distance matrix and margin
is retained. The print projects each reply onto its own/rival direction. The
midpoint is the exact equal-distance boundary for that pair in the full space;
the drawing does not fit a classifier or select a favourable feature subset.

This is elementary finite Euclidean geometry. Shared translation acts on the
whole collection; centering chooses its unique zero-mean representative and
retains every pair difference. It is not a new general mathematical theorem.

## The further timestep

The producing code parameterizes the two rates and captures the declared
follow-up plan. All writing histories still run individually. The full repeated
192-step calculation passes an exact admission against the earlier record:
488 arrays agree, including every written field, complete probe initial
condition, readout and distance array. The new 384-step histories run only after
that admission. The original six-second single-chain admission also passes.

| Steps per second | Near minimum pair separation Hz | Distant minimum pair separation Hz |
|---|---:|---:|
| 96 | 0.004690258 | 0.002101487 |
| 192 | 0.004685738 | 0.002121531 |
| 384 | 0.004679307 | 0.002128870 |

The closest near pair remains BDCA / DBCA; the closest distant pair remains
CBDA / CDBA. At 384, the distant minimum among pairs sharing their last two
tokens is 0.005287400 Hz. Every both-erased reply still equals its fresh control
exactly. All partial erasures and their pair distances remain in the record.

The original distant-receiver gate passes on the new 192/384 pair: all 276 pair
distances exceed 0.001 Hz, all 24 finer replies are uniquely closest to their own
coarse histories, states are finite, and both-erased error is zero. An independent
verifier reconstructs the field interventions, repeated-rate admission, distances
and choices. This is another finite timestep comparison; no continuum,
gesture-noise, human-audibility or physical-memory capacity claim follows.

## Reproduction

`received-refinement-001` contains the two-rate follow-up. `observer-offset-001`
and `observer-offset-002` contain the 96/192 and 192/384 diagnostics. A separate
per-pair norm verifier reconstructs their matrices to a maximum discrepancy of
1.11e-16 Hz and checks the contrast identities. The original records, rejected
packed-chain admission and all raw-reader outcomes remain available.

This finite material experiment and authored geometric print distinguish
retained state from its observation. No quantum recurrence theorem is claimed
for the nonlinear model.
