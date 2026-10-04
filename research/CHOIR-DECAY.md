# A clock for frozen mechanical forgetting

This is a quantitative continuation of `CHOIR-ENERGY.md`. It concerns the
finite, continuous-time mechanical equations with p and z held fixed and
0<=z<=1, no external drive or delayed feedback, nonnegative tension, bending
and cubic coefficient, and zero buckling. Every included bridge has a fixed positive strength. Disconnected
bridge coordinates are omitted. It leaves the active artwork and every
published experiment unchanged.

Exponential decay for strongly convex damped-gradient systems is established
mathematics. For context, Aujol, Dossal and Rondepierre study convergence rates
of heavy-ball dynamics in [SIAM Journal on Optimization (2022)](https://doi.org/10.1137/21M1403990).
The following conservative argument is supplied in full for this project's
particular mass normalization and reciprocal ports. It does not claim a new
general theorem or an optimal rate.

## A mass-metric lower bound without a modal truncation

Use the body spatial mean as its squared norm, and let each port footprint
have RMS one. Thus its reading obeys |q_a|² <= ||u_a||² by Cauchy–Schwarz.
Consider one chain with K beads, total bead mass m, spring coefficient k,
and fixed gate g>0. Its endpoints are q_a and q_b. Set

    l_j = (1-j/(K+1))*q_a + (j/(K+1))*q_b,
    r_j = w_j-l_j,      r_0 = r_(K+1) = 0.

Jensen's inequality gives sum_j l_j² <= K*(q_a²+q_b²)/2. Write each r_j as

    r_j = ((K+1-j)/(K+1))*sum_(i<j) Δr_i
          - (j/(K+1))*sum_(i>=j) Δr_i.

The squared norm of these coefficients is j*(K+1-j)/(K+1). Cauchy–Schwarz,
followed by summing j=1,...,K, therefore gives

    sum_j r_j² <= K*(K+2)/6 * sum_(i=0)^K (Δr_i)².

The constant increments of l are orthogonal to Δr, whose sum is zero.
Consequently sum (Δr)² <= sum (Δw)². Combining the preceding inequalities
with (l+r)² <= 2*l²+2*r² yields the endpoint-and-chain bound

    (m/K)*sum_j w_j²
        <= m*(q_a²+q_b²) + m*(K+2)/3 * sum_i (Δw_i)².       (1)

For the complete scene let

    d_max = max over bodies of sum of incident bridge masses,
    B = sum over bodies of ||u_b||²,
    S = sum over bridges of k_e*g_e*sum_i (Δw_e,i)².

Applying (1) to a perturbation of all coordinates gives

    ||delta q||_M² <= (1+d_max)*B
                     + max_e[m_e*(K_e+2)/(3*k_e*g_e)]*S.

The body's grounded stiffness is at least kappa_0=1.008. Its tension, bending
and quartic Hessian contributions are nonnegative. The bridge potential has
Hessian quadratic form S. Hence the potential obeys, at every configuration,

    Hess V >= mu_* M,
    mu_* = min(kappa_0/(1+d_max),
               min_e[3*k_e*g_e/(m_e*(K_e+2))]).             (2)

With no included bridges, simply use mu_*=kappa_0 on the body coordinates.
This is a full finite-grid inequality. It uses no eigenvalue estimate,
equilibrium calculation, modal truncation or sampled trajectory. It does not
by itself establish convergence of a continuum discretization.

## An explicit modified energy

Let q_* be the unique frozen equilibrium, eta=q-q_*, v=q', and

    U(q) = V(q)-V(q_*),       K(v) = v^T M v / 2,
    E = K+U.

Suppose gamma*M <= C <= Gamma*M with gamma>0, and choose any admitted
mu>0 with Hess V >= mu*M. Strong convexity gives

    U >= mu*||eta||_M²/2,
    eta^T grad V(q) >= U + mu*||eta||_M²/2.                 (3)

For 0<epsilon<min(gamma,sqrt(mu)), define

    L = E + epsilon*eta^T M v + epsilon*eta^T C eta/2.

The cross term satisfies |eta^T M v| <= E/sqrt(mu), and
eta^T C eta/2 <= Gamma*U/mu. Therefore

    a*E <= L <= b*E,
    a = 1-epsilon/sqrt(mu),
    b = 1+epsilon/sqrt(mu)+epsilon*Gamma/mu.                (4)

Differentiate along M*v'=-C*v-grad V. The two mixed damping terms cancel:

    L' = -v^T C v + epsilon*v^T M v
         - epsilon*eta^T grad V
       <= -2*(gamma-epsilon)*K - epsilon*U
       <= -beta*E <= -(beta/b)*L,
    beta = min(2*(gamma-epsilon),epsilon).                 (5)

The compact energy sublevels from `CHOIR-ENERGY.md` ensure that solutions
exist for every t>=0. Integrating (5) and using (4) proves

    E(t) <= (b/a)*exp(-(beta/b)*t)*E(0).                   (6)

The ordinary mechanical energy is nonincreasing as well, so the minimum of
one and the factor in (6) is also a valid normalized upper bound. Nothing in
this proof requires an upper bound on the potential Hessian; the quartic
term is permitted globally.

For a definite reproducible choice use

    epsilon = min(2*gamma/3, sqrt(mu)/2).

It satisfies the required strict inequalities and keeps a>=1/2.

## The two frozen scenes

For all twelve bridges at strength one, K=16, m=0.65 and the least bridge
tension is 1.04, with k=tension*(K+1). The largest incident total mass is 3.9.
Equation (2) therefore permits the conservative choice mu=0.20. The damping
bounds are gamma=0.24 and Gamma=0.38. For the separate bodies, omit every
bridge coordinate and use mu=1.00, gamma=Gamma=0.38. These values are rounded
conservatively from the analytical parameter bounds, rather than fitted to
observed motion. `CHOIR-DECAY-RESULTS.md` supplies evaluated constants and
computational cross-checks.

Equation (6) bounds excess mechanical energy about the equilibrium for the
chosen fixed p,z. The retained coordinates themselves are constant by the
frozen assumptions. The active material continues to write, diffuse and
slowly forget; its film includes drive, changing connections and a disclosed
motion-clearing intervention. The bound is not a prediction of that film,
a discrete-integrator theorem, a hearing threshold, or a comparison theorem
saying that cutting links accelerates every particular trajectory.
