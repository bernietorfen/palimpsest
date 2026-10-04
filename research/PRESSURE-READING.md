# PALIMPSEST: reading through pressure variation

Follow-up protocol, fixed before generating its derivative or evaluation trajectories, 4 October 2026. This experiment is motivated by the completed pressure study: its nearest canonical trajectory reader identified 343 of 960 histories at the largest tested pressure variation. The new experiment uses a separate evaluation seed.

## Reader

For each of the 120 canonical histories, compute five central finite differences of the complete probe-pitch trajectory with respect to the five gesture-pressure multipliers. Use multiplier offsets of ±0.002 around the original pressure. All other inputs and the reset/probe protocol remain unchanged.

These five response directions form a local linear approximation to how pressure changes that history's answer. Divide trajectories by the square root of 4,032 so Euclidean norm retains the original Hz RMS units. Use the thin singular-value decomposition of each 4,032 × 5 derivative matrix. Retain singular directions whose value exceeds 10⁻⁶ times that matrix's largest singular value. Subtract the query's projection onto those retained directions when measuring its distance to that history. Identify the history with the smallest remaining residual.

This is a local linear nuisance-response correction using established linear algebra. It is not a newly invented general inference algorithm. No pressure-error realization from the first study is used to fit the directions. The reader does not receive the query's true history, exact pressure factors, severity or future result. Its five-dimensional correction is unconstrained; inferred pressure adjustments can be reported, but they are not used to reject or relabel queries.

## Independent evaluation

Use NumPy PCG64 seed 2026100404, distinct from the first pressure study. Generate eight new independent bounded uniform pressure realizations per history at each of the same severities, 1%, 3% and 10%. Pair the errors across severities as before. Compare the original nearest-reference reader and the corrected reader on exactly the same 2,880 cases at timestep 1/96 second.

Repeat derivative construction and the first realization of every history and severity at timestep 1/192 second. This refinement subset is fixed before observing the new results. The original canonical atlas at each matching timestep supplies the centers. The already admitted batched implementation supplies derivatives and queries; its source and original admission record are pinned by checksum.

Report both confusion matrices, case-level labels and residuals, derivative singular values/ranks, and the agreement of the predefined refinement subset. Report successes and failures of both readers. The experiment tests a specific approximate reading rule over a finite set of authored histories; it does not establish human audibility, a globally invertible memory, robustness to timing errors, or a physical information-capacity bound. Any later change to the reader requires a new protocol and fresh evaluation cases.
