# An imperfect hand

PALIMPSEST / Study III / 4 October 2026

The original atlas establishes distinct answers for 120 exactly prescribed writing orders. This follow-up asks how those identities survive uneven writing pressure, and whether a fixed reading rule can account for that variation.

Two experiments were performed. Their protocols were committed before their respective generation runs. The second protocol follows the first experiment's observed failures; its evaluation uses a new seed. The two sets of counts must not be combined or treated as the same cases.

## Pressure variation

The material, five gestures, 24-second writing interval, transient reset, fourteen-second probe and 4,032-value pitch metric match the original atlas. Each complete writing gesture receives a multiplier `1 + severity × error`, where the independent error is uniform on [−1, 1]. Errors are indexed by history, realization and writing position. The same errors are reused across severity levels, pairing those comparisons. Timing remains fixed. Changing pressure changes the norm of the writing input.

The 128 × 128 experiment runs at 96 steps per second with eight realizations for every history and severity. The first realization of every history is repeated at 192 steps per second. All canonical references use the matching timestep.

The first experiment uses PCG64 seed 2026100403 and the nearest canonical answer by full-trajectory RMS distance.

| Pressure limit | Correct / 960, 96 Hz | Correct / 120, 192 Hz |
|---|---:|---:|
| 1% | 960 | 120 |
| 3% | 906 | 112 |
| 10% | 343 | 43 |

Protocol: `PRESSURE-STUDY.md`, privately committed as `a8cf312` before generation. The saved record is `artifacts/studies/pressure-study-001`. Its report SHA-256 is `2956c785fe9d11c810e2a3b0f2cebb3ba723deb2cb34384d7dfba434eebe1973`.

## A pressure-aware reading rule

For each canonical history, separately generate the responses to ten controlled writes: each of the five gesture multipliers is perturbed by nominal −0.002 and +0.002. Central differences, divided by the actual float32 multiplier separation, produce five directions in the 4,032-dimensional response space. Divide response coordinates by √4032 so Euclidean length is measured in Hz RMS.

For candidate history h, let c_h be its canonical response and J_h the five pressure derivatives. The reader scores an observed response q by

`r_h = min_a ||q − c_h − J_h a||₂`.

It selects the candidate with the smallest residual. A thin SVD supplies the directions; singular values below 10⁻⁶ of the largest are discarded. No true history, exact pressure multipliers or severity are inputs to this rule. The adjustment a is unconstrained. It need not be a physically valid pressure realization or lie within the test's pressure limit.

This is established local linear / least-squares geometry applied to the authored instrument, not a proposed new general classification algorithm.

The fresh evaluation uses PCG64 seed 2026100404. Directions are generated independently of all evaluation cases. The rule and thresholds were fixed in `PRESSURE-READING.md`, privately committed as `7a1648a` before these derivative and evaluation runs.

| Pressure limit | Nearest / 960 | Allow pressure / 960 | Nearest / 120, finer step | Allow pressure / 120, finer step |
|---|---:|---:|---:|---:|
| 1% | 960 | 960 | 120 | 120 |
| 3% | 904 | 960 | 112 | 120 |
| 10% | 374 | 881 | 46 | 108 |

At the 10% level, 365 cases are correct under both rules, 516 are recovered by the pressure-aware rule, 9 are lost, and 70 are wrong under both. Thus 79 of 960 corrected readings remain wrong. In 209 of those 960 cases the winning linear adjustment exceeds the actual ±10% bound; its maximum absolute component is 0.361127. These adjustments are not estimates certified to recover the original hand pressure.

At the 1% and 3% levels, all 120 first-trial labels agree between timesteps for both readers. At 10%, 119 of 120 labels agree for each reader. The coarse first trial has 47 nearest-reference and 107 corrected successes; the finer trial has 46 and 108 respectively. Timestep refinement is not a spatial-continuum test.

Saved record: `artifacts/studies/pressure-reading-001`. Report SHA-256: `010aa9da09bd8a90f8500952f154d0da74d2c2736f47465d293eac11207c92c3`.

## Independent checks

The batched material preserves the scalar implementation's equations and update order. Admission compares four full writing/probe trajectories at each timestep against the scalar solver. The largest recorded state difference is 2.8611 × 10⁻⁶, below the fixed 0.0002 tolerance; all 120 canonical batch controls at each timestep identify their own original atlas reference within the required 0.001 Hz RMS tolerance.

The first experiment's independent verifier reopens all 79 manifest files, reconstructs the declared seed, factors and case order, and recomputes every candidate RMS distance by explicit NumPy subtraction and averaging. Predictions and confusion matrices match; the largest distance difference is 4.4409 × 10⁻¹⁶ Hz.

The second experiment's verifier reopens all 116 manifest files, reconstructs every derivative from its saved measurements, and independently solves all candidate least-squares problems with SciPy's `gelsd`. It reconstructs the complete residual vectors rather than reusing the saved SVD basis or subtracting squared projection lengths. Every prediction, confusion matrix and refinement count matches. The largest residual difference is 2.1611 × 10⁻¹⁰ Hz; the largest winning-adjustment difference is 1.0745 × 10⁻¹³.

The verification JSON files and the smaller paired-outcome record accompany the public source and study edition. Raw trajectories, pressure factors, numerical derivatives, reader matrices, all candidate residuals and original generation source snapshots are preserved in the scientific archive.

## The visual record

The 6000 × 8000 print and interactive map project every fresh case onto the first two components of the original canonical atlas. These two components retain 65.5196% of canonical variation. The same coordinates appear under both reading rules; only the outcome colors change. Neither reader classifies from this two-dimensional picture.

Each paired drawing uses four moments, at 0, 4, 8 and 12 seconds, and twelve voice directions. Values are centered on the canonical ensemble mean at the matching time and voice. All measured and ideal glyphs share one scale. Periodic cubic curves are an authored interpolation of the twelve samples.

The browser stores these display samples as signed 16-bit deviations. Their maximum measured quantization error is 0.0001060547 Hz. Classification uses the full unrounded trajectories. SVG exports retain their four sampled moments, shared scale, actual case and source-report hash as metadata. They are compact drawings of the experiment, not substitutes for its complete scientific record.

## Scope

These finite cases support identification counts for this invented material and this bounded pressure protocol. They do not establish human audibility, timing-noise robustness, physical storage capacity, global invertibility, a population-level success probability, or universal artistic priority. The material and coupled composition are original to PALIMPSEST; the numerical and statistical ingredients are acknowledged as established tools.
