# A return seen through incomplete relationships

Declared 4 October 2026 at 17:28 UTC, before execution of this experiment.

This study adds a finite unitary phase instrument to PALIMPSEST. It is separate
from the damped, plastic material choir. Its question is operational: when does
a return in selected observations imply a return of the complete modeled state?
The contribution is an authored finite instrument, a specific experiment and a
self-contained graph bound. Finite quantum recurrence, phase synchronization,
trace distance and graph Poincare inequalities are established mathematics.

## State and observation

Use hbar=1, positive populations p_j summing to one and H=diag(E_j):

    psi_j(t) = sqrt(p_j) exp(-i E_j t),   rho(t)=|psi(t)><psi(t)|.

The exact evolution is unitary. It is calculated classically. The same phase
algebra admits a classical complex-wave interpretation; this study does not
establish uniquely quantum behavior or model physical quantum matter.

An observer receives complex coherences rho_jk for selected graph edges jk.
Their real and imaginary parts are expectation values of two Hermitian pair
observables. They describe ensemble measurements on identically prepared
states, not simultaneous, backaction-free monitoring of one unknown specimen.
Populations are known and constant; the reconstruction claim does not extend
to arbitrary mixed states.

For nonnegative edge emphases a_jk, define

    z_j(t) = exp(-i E_j t),
    R_G(t) = sum_edges a_jk |rho_jk(t)-rho_jk(0)|^2
           = sum_edges a_jk p_j p_k |z_j(t)-z_k(t)|^2,
    D(t)^2 = 1 - |sum_j p_j z_j(t)|^2.

D is pure-state trace distance, invariant under a common phase. R_G is a
chosen squared observation discrepancy, not automatically Fisher information
or a physical noise model. Numerically D^2 is evaluated by the equivalent,
nonnegative weighted phase-variance formula to avoid cancellation near return.

## Bound and proof

Give the graph Laplacian L weights a_jk p_j p_k and write P=diag(p). Exact
R_G=0 means every positive-weight edge joins equal phases, so phases are
constant within each connected component. Conversely that condition gives
R_G=0. For c components there are c-1 unobserved relative component phases,
after quotienting by the common phase.

If the graph is connected, let lambda_G be the first positive eigenvalue of
P^(-1/2) L P^(-1/2). Then

    D(t)^2 <= R_G(t)/lambda_G.                         (1)

Indeed, with mu=sum p_j z_j,

    sum p_j |z_j-mu|^2 = 1-|mu|^2
                      = sum_(j<k) p_j p_k |z_j-z_k|^2.

Apply the weighted graph Poincare inequality to the real and imaginary parts
of z-mu and add. With all pairs and unit emphases, the last identity gives
R_complete=D^2 exactly. These formulas hold for any fixed phase differences
in the specified family, not just for a sampled trajectory.

If measured coherence changes have weighted Euclidean error at most eta,
the triangle inequality gives

    D <= min(1, (sqrt(R_measured)+eta)/sqrt(lambda_G)). (2)

A weakly connected graph can have a very small lambda_G. A small R_G alone
therefore need not certify an accurate global return. Equation (2) assumes
the stated deterministic error bound; it is not a quantum shot-noise result.

## Declared cases

The four-level reference has p=(1,1,1,1)/4 and
E=(0,1,sqrt(2),1+sqrt(2)). The restricted observer has edges (0,1),(2,3).
At t=2*pi its observations return exactly, while

    D(2*pi)=|sin(pi*sqrt(2))| > 0.9.

Add edge (1,2) with emphasis epsilon and keep the others at one. For epsilon>0,

    R_G(2*pi) = epsilon*D(2*pi)^2/4,
    lambda_G = [1+epsilon-sqrt(1+epsilon^2)]/4
             = epsilon/[2*(1+epsilon+sqrt(1+epsilon^2))].

Use the final expression for numerical stability and also evaluate the graph
spectrum independently. Test epsilon in (0,1e-6,1e-4,1e-2,1). The graph with
epsilon=0 is disconnected and receives no connected-graph certificate.
As a matched-weight control, give the two disconnected edges emphasis 1.5
each. Their total emphasis then equals the unit-emphasis connected graph's
three, but the unobserved relative component phase remains hidden. This
matches the algebraic sum of weights, not an unmodeled physical shot budget.

Evaluate special times 0,2*pi,4*pi and 2*pi*n for n=(5,12,29,70,169), plus
4097 uniformly spaced times on [0,20*pi]. The n=169 point is a declared near
global return with D<0.01. A separate positive control uses commensurate
energies (0,1,2,3), whose full state returns at 2*pi. Zero energies give a
stationary control. Add the common energy shift 3.75 as a global-phase control.

The 32-level extension has indices (g,r), g=0,...,3 and r=0,...,7,
E_(g,r)=r+b_g with b=(0,sqrt(2),sqrt(3),sqrt(5)) and p=1/32. Compare four
disconnected within-group paths, the same paths joined by edges (7,8),
(15,16),(23,24), and the complete graph. Use the same time grid and special
times. Every observer must consume the same immutable state array.

For the connected four-level graphs, bounded-noise checks use eta in
(0,1e-6,1e-3,0.1) and a deterministic complex error direction normalized in
the weighted observation norm. Also test a cancellation error equal to the
negative true coherence-change vector at 2*pi: measured discrepancy then
vanishes, while the declared error norm must keep (2) valid. Errors affect
only observation copies, never the underlying state. Retain both useful and
uninformative certificates.

## Independent routes and advancement gates

The production route uses direct phases and selected indexed coherences. The
reference route constructs a dense Hermitian H, applies SciPy's matrix
exponential, forms density matrices, obtains trace distance from Hermitian
eigenvalues, and evaluates explicit Hermitian observation operators by traces.
A fixed Fourier basis change transforms H, state and observables together.
It must preserve all physical results. Vertex relabeling is a separate check.

Advance only if:

1. Four-level norm conservation and dense-exponential state agreement have
   maximum absolute error below 1e-12 at the special times.
2. R_disconnected(2*pi)<1e-24 while independent full trace distance exceeds
   0.9; the bridge formula agrees within 1e-12.
3. Complete-graph R agrees with independently formed density-matrix D^2
   within 1e-12 for four levels and 2e-12 for 32 levels. The generic phase
   variance identity is also checked throughout both recorded time grids.
4. Connected-graph bound (1) and all bounded-noise certificates (2) have
   numerical slack no worse than -2e-11. The analytical bridge spectral gap
   agrees with the independent generalized eigenvalue within 1e-12.
5. The commensurate positive return has independent trace distance below
   1e-12. The irrational n=169 near return has independent D<0.01. The
   stationary, common energy shift, Fourier basis and relabeling controls
   agree within 2e-12.
6. All observer variants use byte-identical underlying states, and those
   arrays remain unchanged after noise injection and certificate evaluation.

The mathematical proof supplies the universal bound under its assumptions;
finite checks validate this implementation. A failed gate is retained and
diagnosed, not silently loosened. No hypothesis concerns human audibility,
perceived similarity, a thermodynamic arrow, continuum physics or a universal
law of time. Exact global recurrence is absent at positive times for the
specified irrational four-level spectrum, although arbitrarily close returns
exist. A chosen finite near return is not an exact one.

## Reproduction and sources

Run `python -m studio.relational_clock --output artifacts/studies/relational-clock-001`
on the remote computation host. The producing program captures the protocol,
source, tests, numerical arrays, all admission results and SHA-256 hashes in a
new output directory. It refuses to overwrite a prior record. Keep CPU threads
bounded; no GPU is required. The initial record is expected to remain below
50 MiB. Those are resource estimates until measured.

- [Bocchieri and Loinger, Quantum Recurrence Theorem (1957)](https://doi.org/10.1103/PhysRev.107.337): original recurrence context.
- [Watrous, The Theory of Quantum Information, Chapters 1 and 3](https://cs.uwaterloo.ca/~watrous/TQI/): trace distance, pure-state formulas and discrimination.
- [Singer, Angular Synchronization by Eigenvectors and Semidefinite Programming (2011)](https://arxiv.org/abs/0905.3174): established recovery of phases from pair offsets, up to a common phase.

The geometric observation network is distinct from a dynamical physical memory.
If a narrative introduces an included record, partial-trace contraction implies
that an exact return of the complete system also returns that record. An external
saved plot does not demonstrate a surviving internal witness of global recurrence.
