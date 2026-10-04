# PALIMPSEST: imperfect writing pressure

Protocol fixed before the perturbed trajectories are generated, 4 October 2026.

The exhaustive atlas establishes distinct responses to exactly specified histories. This follow-up asks how those history labels survive bounded variation in the pressure used to write them. It is a numerical identification experiment on the authored instrument, not an auditory discrimination test or a material-memory capacity theorem.

## Inputs and controls

Use all 120 orders of the existing five gestures. Keep their voices, start times, attack, hold, release, the 24-second writing interval, the transient reset and the 14-second probe unchanged. The grid remains 128 × 128 and effective feedback remains 0.08.

Multiply each writing gesture's complete force envelope by `1 + severity * error`, where each error is drawn uniformly from [-1, 1]. Severities are 0.01, 0.03 and 0.10: bounded relative pressure changes of at most 1%, 3% or 10%. Timing is not perturbed. There are eight realizations for every history. NumPy's PCG64 generator is seeded with 2026100403. Errors have shape [120 histories, 8 realizations, 5 gesture positions]; the same error array is reused across severities to pair the three pressure levels. Different histories and realizations have independent draws. Exact factors are preserved with the output.

The primary run uses timestep 1/96 second: 120 canonical controls and 2,880 perturbed histories. A refinement check uses timestep 1/192 second for all canonical controls and the first realization of every history at each severity, 360 perturbed histories. This subset is specified before observing any result.

## Measurement

After writing, reset displacement to inscription and zero velocity, echo phase and delayed feedback. Keep inscription and fatigue. Apply the unchanged common probe. Record 336 pitch samples at 24 Hz across all twelve voices, including voices not excited by the probe.

Assign each perturbed record to the nearest unperturbed atlas history using RMS pitch difference over those 4,032 values. Use the canonical atlas recorded at the matching timestep. Report counts correct out of cases tested, the full confusion matrix, per-history results, and the distance margin between the correct and nearest other history. Numeric closeness does not establish audibility. Variation in gesture pressure also changes the input norm; this is explicitly an imperfect-writing test, not the equal-input-norm comparison of the original atlas.

## Implementation and admission checks

A batch implementation may evaluate independent materials together on the GPU. It must first agree with the original scalar implementation for selected complete histories, including retained fields, delay and phase, within a maximum absolute tolerance of 0.0002. Its 120 unperturbed probe trajectories at each timestep must match their respective original atlas records within 0.001 Hz RMS and identify all 120 labels correctly. TensorFloat-32 matrix multiplication is disabled. A failed admission check stops the experiment for investigation; the tolerance is not silently relaxed.

Archive the source snapshot, exact factors, all pitch trajectories, checksums, admission checks and analysis. No large preview frames or local-laptop computation are needed. Results remain scoped to this finite set, these bounded pressure perturbations and this numeric readout.

Echo-phase differences in the implementation check are measured modulo 2π; the ordinary absolute difference is recorded separately. State-field tolerances apply to displacement, velocity, inscription, fatigue, delay and phase. Probe-pitch agreement uses the separate 0.001 Hz RMS admission bound above.
