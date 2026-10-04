# The observer's offset: a declared follow-up

Declared 4 October 2026, after reading the complete received-history result.
This is an openly post-result investigation. The original protocol, controls,
18/24 nearer matches and 24/24 distant matches remain unchanged and published
in v2.0.0. No diagnostic here retroactively improves that original score.

## Question

Does a displacement shared by all finer-step trajectories account for the
nearer receiver's six cross-timestep matching errors? Does another timestep
halving retain the selected order distinctions? These are two different checks.
Neither is a claim about a generic advantage of distance or human perception.

## A fixed diagnostic on existing data

For each receiver, use the connected retained replies for all 24 histories,
with the same twelve pitches and 289 times. Treat a reply as a vector with the
RMS inner product. Let C_h be its 96-step reply, F_h its 192-step reply,
delta_h = F_h - C_h, mu = mean_h(delta_h), eta_h = delta_h - mu.

Report the exact finite decomposition

    mean_h ||delta_h||^2 = ||mu||^2 + mean_h ||eta_h||^2.

Translate every fine reply by the single vector -mu and repeat the same
nearest-history lookup. Report every predicted label, every distance and the
number of own-history matches, whether it improves or worsens. This uses the
complete balanced collection to define its origin; it is not a new reader of
one unknown history, a held-out test or a perceptual comparison.

For each original wrong match j of history h, decompose its squared-distance
advantage using d = C_h - C_j:

    ||F_h-C_j||^2 - ||F_h-C_h||^2
      = ||d||^2 + 2<mu,d> + 2<eta_h,d>.

Retain all three terms and check the algebra numerically. A positive value
favours the true history. Translation preserves every within-rate pair distance.
No fitted rotation, rescaling, feature selection or alternative metric is added.

## A fixed third timestep

Repeat the same four contacts, all 24 orders, two receivers, four field
conditions and 12-second probe at 192 and 384 steps per second, still on the
64 by 64 body grid and sixteen-bead bridges. Writing histories continue to run
individually. All material constants, probe times, readouts and erasure rules
stay fixed. The producing code may parameterize the two rates; it must capture
that exact source and this plan.

Before running the new 384-step cases, the regenerated 192-step arrays must
match every saved field, probe initial condition, readout and distance array
of received-histories-002 exactly. A mismatch stops the extension. The original
six-second single-chain admission is also retained.

Report the original numerical criterion on the new 192/384 pair: all distant
pair distances above 0.001 Hz RMS, all 24 finer replies uniquely closest to
their own coarse history, finite states and both-erased maximum error <=1e-6 Hz.
Report the nearer receiver and all partial erasures regardless of outcome.
Repeat the declared offset diagnostic on 192/384 without altering its rule.

This third rate is another finite timestep observation. It is not a proof of
spatial or temporal convergence, and it does not test gesture noise or pressure
robustness. Both the original and new raw-reader results will remain visible.
