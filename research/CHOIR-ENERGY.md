# Where persistence lives in the material choir

This note separates an exact structural statement from the behaviour of the
complete artwork. It distinguishes damped motion, retained state and restricted
observation in the finite material model. The choir is not a quantum simulation.
No quantum spectral-saturation or recurrence exponent is claimed for it.

## Frozen mechanical system

Fix a finite periodic grid. Use the spatial mean as each body's inner product,
`<a,b> = mean(a*b)`, and write `A = -L` for the nonnegative, grid-scaled periodic
Laplacian. Freeze the retained inscription `p` and wear `z`, with `0 <= z <= 1`.
Disable external drive and delayed feedback. Hold every included bridge at a
strictly positive connection strength. Omit disconnected bridge coordinates;
uncoupled numerical beads do not carry force into a body.

For one body define

```
V_body(u) = tension/2 <u,A u> + bending/2 <A u,A u>
          + 1/2 <kappa (u-p)^2> + cubic/4 <(u-p)^4>
kappa = stiffness * (1 - 0.58 z).
```

In this work `kappa >= 2.4 * 0.42 = 1.008`. For a bridge with endpoint readers
`q_a = <phi_a,u_a>` and `q_b = <phi_b,u_b>`, put these coordinates on either side
of its bead displacements `w_1,...,w_K`. Its potential is

```
V_bridge = k*g/2 * sum_{j=0}^{K} (w_{j+1}-w_j)^2,
w_0=q_a, w_{K+1}=q_b, k=tension_bridge*(K+1).
```

The endpoints return the negative potential gradient through the same
footprints `phi_a, phi_b`. This equality between reader and force footprint is
what makes the interface reciprocal. A positive Gaussian is a design choice;
the energy identity itself does not require a Gaussian.

Collect all body samples and active beads in `q`. The mass matrix `M` has body
sample masses `1/N^2` and bead masses `mass_bridge/K`. Let `C` multiply these
masses by their positive damping rates. The continuous-time equations of this
finite spatial discretization are

```
M q'' + C q' + grad V(q; p,z) = 0.
E(q,q') = 1/2 q'^T M q' + V(q; p,z).
dE/dt = -q'^T C q' <= 0.
```

This is an identity of the frozen, unforced continuous-time model. The actual
artwork uses a finite time integrator, plastic updates and active delayed
feedback; the identity is not a passivity claim about that complete system.

## A unique equilibrium and no persistent mechanical carrier

**Proposition.** Under the preceding assumptions, `V` is coercive and strictly
convex on all body samples and active beads. It has a unique equilibrium
`q*(p,z)`. Every solution of the frozen damped mechanical system tends to this
equilibrium. Its linearization has no undamped or neutral mechanical mode.

**Proof.** The body Hessian is bounded below in the spatial-mean metric by
`kappa_min > 0`: the Laplacian and bending terms are nonnegative, and the cubic
term contributes `3*cubic*(u-p)^2 >= 0`. The bridge Hessians are nonnegative.
If a vector has zero total Hessian quadratic form, its body components vanish.
Every active chain then has zero endpoint perturbations and zero adjacent
bead differences, so all its bead perturbations vanish too. The full Hessian
is positive definite. The same grounded body terms, together with the chain
difference terms, make sublevel sets bounded, giving existence and uniqueness.

Positive damping makes `dE/dt=0` possible only when `q'=0`. The largest invariant
subset with zero velocity has `grad V=0`, hence consists of the unique
equilibrium. Compact energy sublevels and the invariance principle give
convergence. This argument concerns the finite-dimensional autonomous ODE.

At equilibrium let `H=Hess V(q*)`, which is positive definite. For displacement
`eta=q-q*` the linear generator and an energy metric are

```
G = [ 0             I       ],     P = diag(H,M),
    [ -M^-1 H      -M^-1 C  ]
G^T P + P G = diag(0,-2C).
```

Thus `exp(tG)` is a contraction in the `P` norm. A hypothetical imaginary-axis
eigenvector has zero velocity by the dissipation identity. The first block
then excludes a nonzero imaginary eigenvalue; for eigenvalue zero the second
block and `H>0` exclude nonzero displacement. All eigenvalues have strictly
negative real part. Therefore every positive-time propagator has its spectrum
strictly inside the unit circle. Its persistent mechanical carrier is zero.

## Retained history supplies the surviving directions

Now include the frozen retained variables `r=(p,z)` as state coordinates with
`r'=0`. Locally the equilibrium depends smoothly on `r`, because `H` is
invertible. Write `Q = d q*/d r`. Linearizing about a fixed retained state and
changing variables to

```
eta = delta q - Q delta r
```

separates the generator into a damped mechanical block and a constant retained
block. For any positive definite metric `W` on the independent retained
coordinates, the positive-time map in these coordinates is

```
T_t = diag(exp(tG), I),       norm metric = diag(P,W).
```

It is a contraction. Its unit-modulus eigenspace is exactly the retained block.
For an initial perturbation `(eta_0,v_0,delta r)`, the return inner product tends
to `delta r^T W delta r`: the mechanical contribution decays to zero. The
lasting part is a changed configuration, not an indefinitely ringing
mechanical oscillation.

A chosen observation can miss some or all of these retained directions. In
the recorded second-act performance, the pitch response of E is unchanged in
the saved finite-precision comparison while A, C and G change substantially.
That observation is finite and specific. It does not identify an infinite-time
relation lattice or establish an exact arithmetic invariant from finite data.

## Scope and checks

The reciprocal bridge force/potential gradient and instantaneous power balance
are independently checked in `studio/tests/test_choir.py`. The full frozen body
and bridge potential is also differentiated independently by automatic
differentiation in `studio/tests/test_choir_energy.py`. On three bodies and two
active chains, its gradient reproduces the actual old-state acceleration rule
to within 3e-12, the instantaneous dissipation identity holds, and the retained
fields remain unchanged. The test completed successfully on RunPod.

The saved Galerkin calculation in `artifacts/studies/choir-frozen-001` uses
thirteen body coordinates per body and all 192 beads: 283 positions and 566
mechanical state coordinates. It checks the equilibrium, Hessian, generator
and finite-step stability using the performance's retained fields at 228
seconds with all bridges reconnected. The largest generator real part is
-0.1200000547 per second and the 1/96-second step has spectral radius
0.9987523383. Its energy-metric identity residual is 1.4211e-14. This declared
reduction is a numerical cross-check, not a full-grid spectral proof.

The full performance deliberately lies outside the frozen theorem: contacts
write into p and z, feedback can supply energy, links change, and a disclosed
intervention clears transient motion. The controlled transfer experiment cuts
all bridges and clears motion before probing retained history. Neither this
note nor that experiment claims physical fracture, biological memory or a
world-first mathematical principle.
