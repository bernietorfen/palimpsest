# A mark, at three scales

PALIMPSEST / registered spatial-refinement study / 4 October 2026

All 120 writing histories retain their nearest own label in every tested spatial and timestep comparison. At 192 steps per second, the aggregate same-history pitch difference decreases from 0.00335587 Hz for 128 → 256 samples per side to 0.000794747 Hz for 256 → 512. This is evidence for the finite identification result under the declared refinement, not a proof of continuum convergence.

## Construction fixed before generation

The protocol in `SPATIAL-STUDY.md` was committed before the experiment ran. The study contains all 120 permutations of A B C D E, at grids 128, 256 and 512, with timesteps 1/96 and 1/192 second: 720 canonical trajectories. Gesture pressure is nominal throughout. The 24-second writing phase, transient reset and 14-second common probe match the original history atlas. Each answer contains 336 samples of twelve pitches. Distances are RMS differences over all 4,032 values.

The existing analytic force patterns are re-evaluated and RMS-normalized on each grid. The existing Laplacian scaling preserves the spatial coefficients. The feedback strength is 0.08, as in the original history atlas.

The original constructor shifts its echo by integer offsets `N//7` and `N//11`. Simply changing N would slightly move the echo in domain coordinates. This study instead registers its position to the original 128-grid fractions: 18/128 vertically and 11/128 horizontally. The shifts are therefore (18,11), (36,22) and (72,44). This deliberate registered construction is documented separately; it does not retroactively change the film, live instrument or earlier experiments.

Admission checks compare selected batched trajectories with the scalar implementation and all original-grid trajectories with the saved atlas. The original-grid controls retain all 120 nearest own labels, with maximum pitch-record differences below the declared 0.001 Hz admission threshold. The scalar state checks pass the declared 0.0002 tolerance.

## Recorded comparisons

“Aggregate RMS” combines all histories, probe times and voices. “Maximum own RMS” is the largest single-history distance to its own reference. Identification compares each query against all 120 references, without supplying its history to the distance calculation.

| Steps per second | Grids | Aggregate RMS, Hz | Maximum own RMS, Hz | Own history nearest |
|---:|:---|---:|---:|---:|
| 96 | 128 → 256 | 0.003368860 | 0.005492286 | 120 / 120 |
| 96 | 256 → 512 | 0.000803860 | 0.001309487 | 120 / 120 |
| 96 | 128 → 512 | 0.004156508 | 0.006796942 | 120 / 120 |
| 192 | 128 → 256 | 0.003355872 | 0.005464316 | 120 / 120 |
| 192 | 256 → 512 | 0.000794747 | 0.001289574 | 120 / 120 |
| 192 | 128 → 512 | 0.004134716 | 0.006748923 | 120 / 120 |

The ratio between successive adjacent-grid aggregate differences is approximately 4.19 at 96 steps per second and 4.22 at 192. An observed decrease across these three grids is not an established asymptotic order or a continuum error bound.

All 7,140 history pairs remain distinct at every condition, using the declared threshold of 0.000001 Hz. The closest pair is ACBED / ACDEB throughout. Minimum pair distances range from 0.170342 to 0.175995 Hz.

The three same-grid timestep comparisons also identify all 120 histories. Their aggregate differences are 0.0428621, 0.0428651 and 0.0428680 Hz for grids 128, 256 and 512 respectively. Timestep sensitivity remains larger than the tested spatial differences. Delay-buffer length is rounded separately at each timestep, as in the original implementation.

## The print

*A mark, at three scales* shows the retained inscription after the preselected history DEABC at 192 steps per second. The top row uses one common inscription scale, -0.8 to +0.8. The lower maps subtract values at coincident sample sites: 256 minus 128, and 512 minus 256. Both differences use the same enlarged scale, ±0.001805976. No field is independently normalized.

The 6000 × 4500 PNG contains 27 million pixels. Its companion PDF retains vector typography and layout around the sampled field images. A separate plot follows all 120 same-history pitch differences through the adjacent refinements. Fields after ABCDE are also saved in the scientific record; they were selected in the protocol, not after seeing a favorable picture.

## Independent reconstruction

`studio/verify_spatial_study.py` checks all 71 file digests, reconstructs combined records from the saved batches, and independently calculates every pairwise and cross-grid distance using explicit NumPy residuals. It reproduces every nearest label and count. The maximum discrepancy from the generation distances is 4.440892098500626e-16 Hz.

The verifier separately evaluates the shifted analytic patterns at their declared coordinates, rather than using the generator's array-roll operation to construct the expectation. The largest difference is approximately 1.565e-5, within the declared 2e-5 float32 tolerance. Retained-field shapes, bounds and coincident-site differences are also reconstructed.

Study report SHA-256: `b96bd8256875cd06d97de19f6d5d62ca438cc039f7ba95d29aa4086c87f98902`.

## Limits

This study concerns one authored instrument, five nominal writing gestures and a common numerical probe. It does not test the pressure-corrected reader on finer grids, establish human audibility, prove global stability, or model a physical material. The controlled transient reset is an intervention in the mathematical state. Three grids and two timesteps cannot establish universal behavior.

The complete records preserve all pitch trajectories, retained summaries, selected fields, comparison matrices, admission checks and the exact generation-source snapshot. The complete notebook places these results alongside the original film, playable instrument and pressure experiment. The first notebook remains preserved as its own edition.
