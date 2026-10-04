# A clock can be sharp nearby and ambiguous far away

Pre-execution protocol, 4 October 2026. This is a focused continuation of
`RELATIONAL-CLOCK-PROTOCOL.md`, using the same four- and 32-level unitary
models and observation graphs. No new physical model or principal exhibit is
proposed. The question is whether local sensitivity and identification of a
widely separated instant are different properties of the same clock.

## Local change

Put `omega_jk=E_j-E_k` and let the observer's readout be the complex vector
`y_G(t)=(sqrt(a_jk)*rho_jk(t))` over observed edges. For the fixed-population
phase family,

    ||y_G(t+delta)-y_G(t)||^2
       = R_G(delta)
       = 4 sum_edges a_jk p_j p_k sin^2(omega_jk*delta/2).

The distance depends on elapsed separation delta, not on the starting
instant t. Define exact coefficients

    C_G = sum_edges a_jk p_j p_k omega_jk^2,
    K_G = sum_edges a_jk p_j p_k omega_jk^4.

The cosine Taylor remainder and `|sin x|<=|x|` give

    C_G*delta^2 - K_G*delta^4/12 <= R_G(delta) <= C_G*delta^2.  (1)

Thus `R_G(delta)=C_G*delta^2+O(delta^4)`. C_G is a squared readout speed,
with units of inverse abstract time squared. It is not automatically the
classical Fisher information of a specified measurement protocol. For a
nonstationary observer, R is strictly increasing for
`0<delta<pi/max_edges|omega_jk|`, because every nonzero term in its derivative
has positive sign there. This interval gives an admitted bracket for a local
resolution threshold when that threshold is reached inside it.

For complete unit-emphasis observations,

    C_complete = sum_(j<k) p_j p_k(E_j-E_k)^2 = Var_p(E).

For the pure state under `exp(-i H t)` with hbar=1, the quantum Fisher
information for the time parameter is `F_Q=4 Var_p(E)`. It describes the
optimized local statistical sensitivity over quantum measurements. It does
not imply global identification of an unknown time, remove aliases, or turn
the present edge-weighted Euclidean norm into a measurement-shot budget.
This is established quantum estimation mathematics; see the local-generator
definition and pure-state identity in equations (9)-(10) of
[Pang and Brun, Quantum metrology for a general Hamiltonian parameter](https://arxiv.org/html/1407.6091).
The optimal-statistical-distance interpretation originates in
[Braunstein and Caves](https://doi.org/10.1103/PhysRevLett.72.3439).

As an independent matrix check, form `rho_dot=-i[H,rho]`. For a pure state,
`L=2*rho_dot` solves the symmetric-logarithmic-derivative equation
`rho_dot=(L*rho+rho*L)/2`. Evaluate `Tr(rho*L^2)` and compare it with
`4 Var_p(E)`. This is a check of the established identity in the selected
models, not a new quantum Fisher information theorem.

## Bounded uncertainty and possible ambiguity

Assume a single estimated ensemble readout can differ from y_G(t) by a vector
of norm at most eta. The allowed readouts form a closed Euclidean ball. Two
candidate times can share an allowed readout exactly when

    sqrt(R_G(delta)) <= 2*eta.                              (2)

The sufficiency witness is the actual midpoint
`m=(y_G(t)+y_G(t+delta))/2`, whose distance from each candidate is half their
separation. Necessity is the triangle inequality: if both errors were at most
eta, the two centers could not be farther than 2*eta.

Equation (2) describes possible ambiguity under bounded deterministic error.
It is not the probability of a mistake, a claim that every error confuses the
times, or a quantum noise model. Eta is a chosen norm in the specified
weighted readout space. Holding eta fixed across graphs does not hold a
physical shot count, experimental cost or measurement resource fixed.
Parameters and the initial-state family are assumed known.

## Exact reference contrasts

The ordinary four-level disconnected observer has

    C_disconnected = 1/8,
    R_disconnected(delta) = (1/2)*sin^2(delta/2).

Its local sensitivity is positive, but it has exact aliases at `delta=2*pi*n`.
With total emphasis matched to three, the two edge weights are 1.5 each and
`C_matched=3/16`. The connected three-edge observer has

    C_connected = (5-2*sqrt(2))/16 < 3/16.

It is less sensitive locally than that matched-weight observer, yet resolves
the latter's first exact alias. This shows that local sharpness and removal
of a distant alias need not rank observers in the same order. Matched total
emphasis remains an algebraic comparison, not an equal-resource measurement
experiment. The complete observer has `C_complete=3/4`, hence `F_Q=3`.

At the stroboscopic lags `delta=2*pi*n`,

    sqrt(R_connected) = |sin(pi*n*sqrt(2))|/2,
    sqrt(R_complete) = |sin(pi*n*sqrt(2))|.

The connected observer removes the exact 2*pi ambiguity but still admits
later near-aliases under nonzero eta. Declared midpoint demonstrations include
n=29 for the connected observer and n=70 for the complete observer, at
eta=0.01. These are nonzero readout differences, not just repeated identical
points. Earlier and later candidate outcomes must all remain in the record.

The 32-level disconnected observer has

    C_disconnected = 7/256,
    R_disconnected(delta) = (7/64)*sin^2(delta/2).

The connected coefficient is
`[28+sum_(g=0)^2 (7+b_g-b_(g+1))^2]/1024`, with
`b=(0,sqrt(2),sqrt(3),sqrt(5))`. The complete coefficient is
`31/4-(sqrt(2)+sqrt(3)+sqrt(5))^2/16`.
Both disconnected observers must distinguish delta=0.2 under eta=0.01,
while confusing delta=2*pi exactly. The connected and complete observers
must reject the first 2*pi ambiguity at that eta.

The commensurate four-level control uses `(0,1,2,3)`, for which complete
`C=5/4` and `F_Q=5`, yet all states return at 2*pi. A zero-energy control is
stationary, has C=F_Q=0 and cannot distinguish any two instants.

## Finite scope and declared samples

Use the explicitly named **stroboscopic candidate grid**
`delta_n=2*pi*n`, `n=1,...,4096`. Its horizon is `8192*pi` abstract time
units. Report the earliest qualifying candidate on this grid only. Do not
call it the first ambiguity in continuous time or infer an absence of
between-sample aliases.

The primary error radius is eta=0.01; sensitivity cases are eta=0.001 and
eta=0.05. For every model, observer, radius and candidate retain the raw R,
distance, signed margin `sqrt(R)-2*eta`, and classification. Use an explicit
numerical borderline band of 1e-10 in distance: margins below -1e-10 indicate
overlap, above 1e-10 indicate disjoint balls, and all others are retained as
borderline. This band is a declared numerical convention, not a formal
interval-arithmetic proof.

For local checks use deltas `(1e-4,1e-3,1e-2,0.1,0.2,0.5)` and starting
times `(0,0.37,9.1)`. Include all four existing observation presets
(disconnected, connected, weak bridge and complete), the matched-weight
four-level control, and the three existing 32-level presets. Add the
commensurate and stationary four-level controls. No favorable spectrum,
threshold or candidate subset may be selected after observing results.

If a local threshold `sqrt(R)=2*eta` lies in the proven monotone interval,
locate it with a bracketed scalar root solver and retain its residual and
bracket. Otherwise report that the bracket does not resolve a threshold;
do not extend a local monotonicity assertion without proof. This local
threshold is independent of the finite stroboscopic search.

## Independent checks and gates

1. Compute C and K directly from declared energy gaps and weights. Match the
   exact coefficient expressions above within 2e-12. Independently obtain C
   from dense `rho_dot` and explicit X/Y operators; use both the energy and
   Fourier bases for four levels, transforming operators with the state.
2. Evaluate the Taylor sandwich (1) using dense-exponential, explicit-operator
   readout differences at every declared local delta and starting time.
   After dividing by delta squared, allow 2e-10 numerical slack. Check the
   unscaled readout distance's starting-time invariance within 2e-12.
3. Confirm `C_complete=Var_p(E)` and the SLD matrix identity `F_Q=4Var_p(E)`
   within 2e-12, including the commensurate and stationary controls. Preserve
   the distinction between this QFI and the chosen graph norm.
4. At eta=0.01, both ordinary disconnected observers must have
   `sqrt(R(0.2))>0.02` and `sqrt(R(2*pi))<1e-12`. Connected and complete
   observers must have `sqrt(R(2*pi))>0.02`. The matched-weight four-level
   observer must have larger C than the connected one and retain its exact
   first alias.
5. Construct midpoint readout vectors for every local check and for declared
   candidates n=(1,2,5,12,29,70,169,985,2378,4096). Verify each endpoint's
   distance equals half the center separation within 2e-12. Explicitly retain
   the n=29 connected and n=70 complete overlap witnesses at eta=0.01, with
   both endpoint errors below eta. For disjoint cases record the strictly
   positive triangle-inequality gap rather than claiming a midpoint alone
   proves disjointness.
6. The commensurate control must return on every stroboscopic grid point to
   within 2e-11 in distance; the stationary control stays identical. Every
   grid classification and borderline margin is saved, including any cases
   with no hit inside the declared horizon.
7. Observation selection, local derivative calculations and synthetic error
   construction must not modify the clock configurations or reference states.
   Retain input/source/protocol hashes and numerical arrays. Do not change
   admission thresholds to hide a failed check.

All execution is a small remote CPU calculation, with no GPU required. The
expected record is below 10 MiB and the run below a minute; measured cost
must replace those estimates in the results. Any implementation defect or
failed declared contrast is retained and reported.

## Interpretation boundary

All earlier pure-state, fixed-population, ensemble-observation and measurement
backaction boundaries remain. The readout vectors are computed expectations,
not ideal monitoring of one unknown quantum object. The model has no physical
erasure or dissipative arrow. The intended contribution is an explicit example
of why a locally responsive clock need not identify a distant instant uniquely.
Its relevance to remembered time, loss and recurrence is an artistic reading,
not a derivation of the nature of time or a new theorem of universal priority.
