# An explicit clock for frozen mechanical forgetting

Declared at 14:15 UTC on 4 October 2026, after the two-act work and its complete
GitHub restoration were finished. This is an analytical follow-up to
`CHOIR-ENERGY.md`, with computational cross-checks. The model, performance,
received-history data and published editions remain fixed.

Question: can the finite, frozen, unforced choir receive an explicit global
mechanical-energy decay bound while its retained coordinates remain constant?
The general method is established damped-gradient Lyapunov analysis. The
contribution here will be a self-contained bound for this project's actual
body/port/bridge normalization, with declared conservative constants.

Proposed argument: bound each bead chain's mass norm by its two endpoint
readings and spring differences. RMS-normalized ports bound the readings by
their body norms. Combine this with the grounded stiffness lower bound 1.008
to obtain a mass-metric strong-convexity constant. For displacement eta from
the frozen equilibrium, add epsilon*eta^T M v and epsilon/2*eta^T C eta to
mechanical excess energy. The derivative cancels the damping cross term and
can be bounded by negative multiples of kinetic and potential energy.

Use only the existing seven-body scene, its 16-bead bridges and declared
material constants. Study (a) every link fixed at strength one, and (b) all
links omitted, including their mechanically disconnected bead coordinates.
Do not infer an ordering of actual trajectories by comparing conservative
upper bounds. Select epsilon=min(2*gamma_min/3,sqrt(mu)/2), where mu is the
admitted stiffness bound. Use rounded-down mu=0.20 for the complete scene and
mu=1.00 for separate bodies only if the analytical chain bound supports them.

Verification before publication:

1. Derive the endpoint/chain inequality and modified-energy identity in full.
2. Independently test the chain inequality as a positive-semidefinite matrix
   for 4, 16 and 64 beads, with explicit endpoint coordinates.
3. Check the full-grid stiffness inequality at 16, 32 and 64 samples per side
   using constant, port-shaped and seeded mixed perturbations. This is a
   numerical cross-check; the written inequality supplies the general proof.
4. Reconstruct the existing nonlinear Galerkin potential from the saved
   228-second fields, then differentiate it independently. Check the modified
   energy derivative and both comparison inequalities at declared seeded
   perturbations, including nonzero inscription and the quartic term.
5. Report every residual and scope limit. If a bound fails, retain the failure
   and narrow or withdraw the claim. Do not describe the result as a new
   general theorem, a finite-step guarantee, actual film decay, audibility,
   a continuum result or a claim about the active plastic instrument.

Retain compact source, exact source/input hashes and results in GitHub.
