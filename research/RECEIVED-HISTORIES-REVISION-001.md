# Received histories: numerical execution revision

4 October 2026. The initial packed-chain admission stopped before the order
evaluation. In `artifacts/studies/received-histories-001/admission.json`, all
body-field errors are below 9.84e-7 and the pitch error is zero, but the maximum
bridge-velocity discrepancy is 6.73532486e-6. This exceeds the locked 2e-6 limit.
The complete failed admission, original code and reference arrays are retained.

Reject the eight-chain packing for this experiment. Execute each three-body
writing history alone, using the same MaterialChoir equations and float32
precision. Do not increase the numerical tolerance. Before evaluation, run the
first chain alone for six seconds and compare every body field, both bridge
fields and all pitches against the saved *single-chain* reference in that
failed admission. The original limits still apply: 2e-6 on fields and 1e-4 Hz
on pitch. Save both sides of this comparison and the reference digest.

After writing each history separately, the two receivers' four field conditions
and one fresh control may share the already used independent-body probe solver:
nine unconnected bodies, no bridge and no source. There is no packing of different
writing histories. Record every probe's complete initial state and check its
field interventions independently.

All four gestures, the 24 permutations, timings, grid, timesteps, retained-field
interventions, response metric, pairwise threshold, cross-timestep criterion
and exact-erasure gate in RECEIVED-HISTORIES-PROTOCOL.md are unchanged. No order
result from the failed run was available or used in this decision. This is a
recorded execution change following an unsuccessful numerical admission,
not a successful result under the original packed implementation.
