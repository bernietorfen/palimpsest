# How much isolation does a return require?

Proposed preregistration, 4 October 2026 at 20:03 UTC. No calculation or
implementation of this extension has run. Scientific review precedes execution.

## Scope and resource ceiling

One 32-by-2 unitary model, six declared times and three environment
preparations. Use six isolated-clock references, no time scan, no coupling
sweep and no search for another joint near return. The existing studies,
browser instrument and film remain separate from this proposed stress test.

Compute on CPU with at most two BLAS threads, no GPU, a 120-second total
calculation limit, a 256 MiB target for peak process memory and at most
2 MiB of retained scientific data, source and receipts. The expected
calculation is substantially smaller than these limits. Preserve failed
gates and stop rather than enlarging the study. Do not add figures or
companion pages before review of the actual evidence.

## Why this could matter

The isolated state nearly returns at cycle 4109. Does that claim survive
when its relationships include one additional degree of freedom? The
proposed interaction preserves every observation inside each of the four
groups, while allowing relationships between groups to involve a qubit.
The familiar fragment can therefore remain unchanged under the interaction,
even while the prediction of its complete isolated return can fail.

The useful human-readable distinction is between returning internal form,
returning purity and returning the complete state. These need not coincide.
This would expose a boundary of the present model, rather than supply a
theory of an irreversible arrow or a literal account of human memory.

The dynamics are a standard exactly solvable controlled-phase model.
Spin-environment Hamiltonians, conditional environment states and the
resulting coherence factors are established in
[Cucchietti, Paz and Zurek, equations (1) and (4)-(8)](https://arxiv.org/pdf/quant-ph/0508184).
The prospective contribution is the specific finite comparison tied to the
recorded return, with explicit controls. No new decoherence mechanism,
recurrence theorem or uniquely quantum appearance is claimed.

## Fixed model and normalization

Retain H_S=diag(E), E_(g,r)=r+b_g, b=(0,sqrt(2),sqrt(3),sqrt(5)),
g=0,...,3, r=0,...,7, and the initial uniform pure state psi_0. Set hbar=1.
Let Z have eigenvalues +1 and -1 on the environment states |0> and |1>.
Use

    A = diag(-3,-1,1,3) on the group index, repeated over each eight-mode group,
    chi = 1/10000 exactly,
    H = H_S tensor I_2 + chi*A tensor Z,    H_E = 0.

A is dimensionless; chi has inverse abstract-time units. Its population
mean is zero and its operator norm is 3. Centering avoids hiding an
environment-only Z Hamiltonian in an identity component of A. The odd
integer eigenvalues also give transparent exact controls. The interaction
norm is 0.0003 relative to the unit within-group energy gap, but the
accumulated action chi*t need not stay small at a distant recurrence.

The Hamiltonian is fixed, finite and unitary. It commutes with the clock's
energy. This is a phase-coupling model, without energy exchange, a thermal
bath or dissipative dynamics.

The primary preparation is psi_0 tensor |+>, with
|+>=(|0>+|1>)/sqrt(2). Define V_+=(exp[-it(H_S+chi*A)]) and
V_-=(exp[-it(H_S-chi*A)]). Then

    |Psi(t)> = [V_+ psi_0 tensor |0> + V_- psi_0 tensor |1>] / sqrt(2),
    rho_S(t) = [V_+ rho_0 V_+^dagger + V_- rho_0 V_-^dagger] / 2,
    (rho_S(t))_jk = (rho_iso(t))_jk cos[chi*t*(a_j-a_k)].

For j and k in the same group, a_j=a_k. Every block-diagonal clock
observable therefore follows exactly its isolated evolution, at all times.
In particular all such observations return at the integer cycles below.

The environment coherence is

    Gamma(t) = sum_j p_j exp(-2i*chi*t*a_j)
             = cos(4*chi*t) cos(2*chi*t),
    rho_E(t) = [[1,Gamma],[conjugate(Gamma),1]] / 2.

Its eigenvalues are lambda_+=(1+|Gamma|)/2 and
lambda_-=(1-|Gamma|)/2. For this pure joint preparation, the entanglement
entropy is h_2(lambda_+), in bits, and the reduced purity is
(1+|Gamma|^2)/2. The entropy of a mixed marginal by itself is not an
entanglement measure for a mixed joint preparation.

Use an independent partial-transpose check as well:

    N(rho_SE) = (||rho_SE^(T_E)||_1 - 1)/2.

For the pure preparation, the Schmidt coefficients give
N=sqrt(lambda_+*lambda_-). The definition and pure-state formula are
established by [Vidal and Werner, equation (4) and Proposition 8](https://arxiv.org/pdf/quant-ph/0102117).
Zero negativity will not be treated as a general separability criterion.

## Operational quantities and decisive controls

For each preparation compare the two known snapshots at 0 and t, with equal
priors and one copy, without an external cycle count or correlated time
record. Report density-matrix trace distances D_S, D_E and D_SE to the
respective initial states, and optimal success (1+D)/2 for access to the
clock, the environment or both. Each column describes a different allowed
register. For the initially mixed environment, no external purification is
supplied. Partial-trace contraction requires D_S,D_E<=D_SE. These facts
follow from [Watrous, Theorem 3.4 and Corollary 3.40](https://cs.uwaterloo.ca/~watrous/TQI/TQI.3.pdf).

Also report the disturbance at the same time,
D(rho_S(t),rho_iso(t)); this differs from the return distance to rho_S(0).
The coupled clock is generally mixed, so neither the old pure-overlap
formula nor the pure-phase graph certificate nor R_complete=D^2 may be
used for its return distance.

Use three environment preparations under the same H:

1. |+><+|: the primary pure joint state can become entangled.
2. I_2/2: exactly the same reduced clock state, but the joint state is the
   explicit separable mixture
   [V_+ rho_0 V_+^dagger tensor |0><0| +
   V_- rho_0 V_-^dagger tensor |1><1|]/2.
   This control prevents an inference of entanglement or uniquely quantum
   noise from the clock marginal alone.
3. |0><0|: a product state at all times, with a known coherent detuning
   H_S+chi*A. This tests the rival explanation that accumulated phase
   shifts can change a return even without entanglement.

The primary preparation with chi=0 supplies the isolated reference. No
threshold or coupling will be tuned after seeing these cases.

## Six times, chosen before calculation

Use t=2*pi*n for n in {0,1,1250,2500,4109,5000}.

- n=0 checks preparation and normalization.
- n=1 checks that the interaction is initially a small perturbation.
- n=1250 gives chi*t=pi/4 and Gamma=0: exactly one bit of entanglement
  for the primary preparation, with reduced purity 1/2 and negativity 1/2.
- n=2500 gives chi*t=pi/2. The interaction factorizes as
  -i*sin(pi*A/2) tensor Z. The primary state is unentangled again, but
  the environment is |->, orthogonal to its initial |+>. Thus D_E=D_SE=1.
  Returning purity does not restore the environment's initial state.
- n=4109 is the previously certified isolated-clock near return.
- n=5000 gives chi*t=pi. Every interaction eigenphase is -1, so its
  unitary is exactly -I_64. The primary joint state is the isolated clock
  state tensor the initial environment, up to a common phase. This is an
  exact interaction return; it is not a claim that the clock or joint state
  has returned to its initial configuration.

The six times are analytic controls and one existing witness, not a
recurrence search. No joint near-return construction is needed to establish
the proposed distinction. The qubit can hold at most one bit of Schmidt
entanglement here; it does not resolve all four group labels independently.

## Minimal admission gates and independent routes

Construct the full 64-dimensional density matrices, keeping subsystem order
explicit. Check both partial traces through tensor-index contraction and
independently through block/operator traces. An eight-dimensional group-by-
qubit model provides an exact stroboscopic compression, verified against the
full 32-by-2 calculation. Evaluate the original diagonal phases and the
closed formulas at 80 decimal digits. Independently propagate a dense
Hamiltonian with matrix exponentials. Repeat in a local Fourier/Hadamard
basis W_S tensor W_E; a global entangling basis change must not silently
redefine the subsystem split.

1. Normalization, Hermiticity, positivity, the two partial traces, analytic
   marginal formulas and compressed/full agreement pass within 2e-12.
   Dense long-time propagation agrees in trace distance within 2e-9; its
   looser bound explicitly allows large-argument binary64 propagation.
2. Every clock block matches the isolated block within 2e-12. At cycle
   4109 the uncoupled reference agrees with the prior D value within
   2e-12. No previous state array or study record is modified.
3. At cycle 1, the primary joint state differs from the isolated product
   state at that same instant by less than 0.002 in trace distance. At
   cycle 4109, the proposed isolation-failure narrative advances only if
   D_S to its initial state exceeds 0.5 and the primary entanglement
   entropy exceeds 0.5 bits. Otherwise retain and report the negative result.
4. At every time, D_S,D_E<=D_SE with slack no worse than -2e-12. Explicit
   binary Helstrom projectors achieve the reported optimal probabilities
   within 2e-12, with positivity/completeness checked. Local basis changes
   preserve these quantities and the entanglement metrics within 2e-9.
5. For the pure joint preparation, marginal eigenvalues, purity and
   negativity agree with the Gamma formulas within 2e-12; entropy agrees
   within 2e-10 bits. The exact n=1250,2500,5000 controls pass those
   tolerances, including the changed environment at the earlier
   disentanglement and its restoration at the interaction return.
6. The mixed-environment control has the identical clock marginal within
   2e-12, matches the explicit separable decomposition and has negativity
   below 2e-12. The eigenstate-environment control stays a product state.
   Report their return distances even when they weaken a preferred reading.
7. Preserve every gate, all three preparations, small state/marginal arrays,
   exact control identities, dependency/source/protocol hashes and resource
   costs. A failed gate is retained without expanding this experiment.

## Conclusions the study would not support

This finite, specially chosen interaction cannot establish robustness to
generic environments, irreversible decoherence, thermalization, an objective
arrow, macroscopic recording or collapse. A small coupling coefficient is
not evidence of a small perturbation after arbitrarily long time. Reduced
clock data alone cannot distinguish the two matched environment mechanisms.
Entanglement entropy returning to zero is not a global-state return. An
exact global recurrence would also restore every included environment and
correlation; no register included in an exact joint return could retain a
distinguishing record of the intervening evolution. The artwork may invite a reading about context
and recognition, while the scientific claim remains this finite isolation
test and its specified access restrictions.
