# Registered spatial refinement

Protocol fixed before generation, 4 October 2026.

The existing atlas is a finite 128 × 128 instrument. Timestep refinement has been checked; this follow-up asks how its canonical history readings change when the sheet is sampled more finely while preserving the original spatial echo placement.

## Fixed experiment

- All 120 lexicographic permutations of A–E, with exactly the original nominal writing gestures, transient reset and fourteen-second probe.
- Grid sizes 128, 256 and 512, each at 96 and 192 steps per second. No random perturbations, pressure correction or fitted parameters.
- The original model's grid-scaled tension, bending and inscription diffusion remain unchanged.
- Preserve the original 128-grid echo translation as a fraction of the periodic domain: 18/128 in y and 11/128 in x. Thus the integer shifts are (18, 11), (36, 22), (72, 44). This is a declared refinement of the original geometry. The general constructor's `N//7, N//11` shifts are deliberately re-registered at the finer grids so rounding does not move the echo while resolution changes.
- Original analytic force/readout patterns are evaluated at each grid's sample locations and normalized by the existing model. All other model constants remain fixed, including feedback 0.08.
- Record the complete 336 × 12 pitch trajectory for every case, plus retained-field summaries. Preserve writing-stage inscription/fatigue fields for the preselected ABCDE and DEABC histories at every grid and timestep.

## Admission and comparisons

The batched implementation must agree with two independent scalar instances (ABCDE and DEABC) through the full writing and probing sequence at both finer grids and both timesteps. Compare displacement, velocity, retained inscription, fatigue, delay and circular echo phase. The fixed maximum state tolerance is 0.0002; report actual pitch RMS and maximum errors. Abort subsequent production if admission fails.

Re-run the 128-grid canonical atlas in batches at each timestep. Require all 120 cases to identify their own original atlas trajectory as nearest, with no case above 0.001 Hz RMS from that reference. This admits the new recorder and unchanged 128-grid geometry before interpreting finer runs.

For every grid/timestep, compute all 7,140 pairwise full-trajectory RMS distances. For adjacent spatial grids at the same timestep, and 512 against 128, report each finer case's nearest coarse reference, correct count, own-history distances and nearest-other margin. Compare 96 with 192 steps per second at each grid. Preserve complete distance matrices and predictions; no result-dependent selection or relabeling.

For the two preselected retained fields, compare coincident sample sites by exact integer stride and report RMS/max differences separately for inscription and fatigue. This is a sampled-field comparison, not a norm of an interpolated continuum field.

An independent verifier must reopen saved arrays, reconstruct case order and all candidate RMS distances by explicit subtraction, and check every prediction/count. A further original 128-grid atlas remains the reference; do not modify or overwrite it.

## Interpretation

This is a finite three-grid check of a declared spatial lift of the authored instrument. A decreasing difference or stable history label would provide evidence at these tested resolutions; it would not prove continuum convergence, an exact physical constitutive law, or audibility. Registration is part of this experiment and must be stated with its results. It does not silently change the film, live instrument, atlas or pressure studies.
