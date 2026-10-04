# A sharp clock can still confuse its returns

The admitted experiment distinguishes two questions: how small a change in
time an observer can resolve nearby, and whether a distant instant can look
like the beginning. These properties do not rank the tested observers in the
same order. In the four-level model, increasing emphasis on the disconnected
relationships improves local resolution, yet leaves every exact observed
return unchanged. Reading the connecting relationship is locally less
sensitive than that matched-emphasis control, but distinguishes its first
return. Later, finite readout uncertainty makes some near returns ambiguous
again.

All 658 declared checks and 12 focused tests pass. These are calculated
ensemble expectation values of known pure-state families, not measurements
on a physical quantum clock. The experiment adds no dissipative dynamics,
erasure, or claim that observation creates time.

## What ambiguity means here

The state, spectra and observation graphs are those in
`RELATIONAL-CLOCK-PROTOCOL.md`. For an observer G, collect weighted complex
coherences in `y_G(t)=(sqrt(a_jk)*rho_jk(t))`. Both quadratures are retained.
The squared distance between readings at times separated by delta is

    R_G(delta) = ||y_G(t+delta)-y_G(t)||^2
               = 4 sum_edges a_jk p_j p_k sin^2((E_j-E_k)*delta/2).

It is independent of the starting time t. Suppose a reported readout can
differ from its true expectation vector by norm at most eta. Two candidate
times admit the same possible report precisely when

    sqrt(R_G(delta)) <= 2*eta.

Their error balls then overlap; the midpoint of the true readings is an
explicit common report. This is possible ambiguity under a deterministic
error bound, not an error probability. Eta is a chosen weighted-observation
norm. Equal eta or equal total emphasis across graphs does not represent
equal measurement shots, experimental cost, or physical noise.

The primary radius is eta=0.01. The local threshold below is the separation
at which the two balls just touch, computed within a proved monotone
interval. Smaller thresholds mean finer local separation in this norm.
The distant search uses only the declared **stroboscopic candidate grid**
`delta=2*pi*n`, `n=1,...,4096`. Its horizon is `8192*pi`, approximately
25,735.927 abstract time units. An earliest candidate is not a globally first
ambiguity in continuous time.

| Model and observer | Local threshold at eta=0.01 | First overlapping candidate n | Overlapping candidates out of 4096 |
| --- | ---: | ---: | ---: |
| Four levels, disconnected | 0.05657609 | 1 | 4096 |
| Four levels, disconnected with matched total emphasis | 0.04619213 | 1 | 4096 |
| Four levels, bridge emphasis 0.000001 | 0.05657609 | 1 | 4096 |
| Four levels, connected | 0.05429410 | 29 | 104 |
| Four levels, complete | 0.02309589 | 70 | 51 |
| 32 levels, disconnected | 0.12102247 | 1 | 4096 |
| 32 levels, connected | 0.05316201 | 623 | 14 |
| 32 levels, complete | 0.00820720 | None on this grid | 0 |

The ordinary disconnected observers distinguish separation 0.2 at this
radius: their readout distances are 0.07059289 and 0.03301680, both greater
than 0.02. Nevertheless, they have exact analytic aliases at every `2*pi*n`.
The connected observers reject the first such alias, with distances
0.48195127 and 0.10146719 respectively. A positive but extremely weak bridge
does not suffice under the selected error bound: all 4096 four-level
weak-bridge candidates remain ambiguous for all three declared radii.

## Local speed is not a global guarantee

With `omega_jk=E_j-E_k`, the exact coefficients are

    C_G = sum_edges a_jk p_j p_k omega_jk^2,
    K_G = sum_edges a_jk p_j p_k omega_jk^4.

The elementary cosine remainder gives the proved sandwich

    C_G*delta^2 - K_G*delta^4/12 <= R_G(delta) <= C_G*delta^2.

Consequently C_G is the squared local readout speed. In units with hbar=1,
energies are angular frequencies and C_G has units of inverse abstract time
squared. For the four-level matched-emphasis observer, `C=3/16=0.1875`;
for the connected observer, `C=(5-2*sqrt(2))/16=0.135723304703`. The former
is sharper locally and still misses the latter's distinguishing relationship.
This is an algebraic comparison under the declared norm, not an experimental
resource advantage.

For complete unit-emphasis observations, `C_complete=Var_p(E)`. The pure
unitary family's quantum Fisher information for the time parameter is
`F_Q=4 Var_p(E)`: 3 for the four-level model and 23.7576246254 for the
32-level model. This established quantity describes optimized local
statistical sensitivity over quantum measurements. It is neither the
classical Fisher information of the selected graph nor a guarantee of unique
time identification. The local-generator identity is given by
[Pang and Brun, equations (9)-(10)](https://arxiv.org/html/1407.6091); the
optimized statistical-distance interpretation is due to
[Braunstein and Caves](https://doi.org/10.1103/PhysRevLett.72.3439).

The commensurate control makes that limit exact. Its spectrum `(0,1,2,3)`
has `F_Q=5`, larger than the irrational four-level model's value of 3, and a
complete-observer local threshold of 0.01788993. Yet the entire state returns
at `2*pi`, so no observation can identify which exact cycle has elapsed
without additional information. All 4096 commensurate candidates return
numerically within 4.52e-12 in readout distance. The stationary control has
zero C and QFI and resolves no separation.

## Actual ambiguous readings and finite negative results

For the four-level connected observer at the first cycle, the separation is
0.481951266425. Its excess over `2*eta` is 0.461951266425. The triangle
inequality therefore rules out any common report inside both radius-0.01
balls.

At cycle 29, the connected readings are separated by 0.0191485208744.
Their stored midpoint is 0.00957426043721 from each endpoint, below eta.
At cycle 70, the complete readings are separated by 0.0158663685242 and
each midpoint error is 0.00793318426209. These are explicit nonzero
near-alias witnesses. They do not rely on roundoff turning a difference into
zero.

The other declared error radii change the finite search as follows. Each
entry gives the earliest overlapping candidate n and the total overlap count.

| Observer | eta=0.001 | eta=0.01 | eta=0.05 |
| --- | ---: | ---: | ---: |
| Four levels, connected | 408 / 10 | 29 / 104 | 12 / 525 |
| Four levels, complete | 985 / 4 | 70 / 51 | 12 / 260 |
| 32 levels, connected | None / 0 | 623 / 14 | 2 / 3909 |
| 32 levels, complete | None / 0 | None / 0 | None / 0 |

The smallest complete-observer distance on the 32-level grid is
0.135827446781, above even the largest tested overlap threshold of 0.1.
The absence of a qualifying candidate is retained as a negative result.
It says nothing about unsampled times or a longer horizon and does not
contradict approximate recurrence. The stored floating-point spectra also
do not establish the infinite-time arithmetic of the ideal irrational model.

## Independent verification and record

Dense matrix exponentials and explicit Hermitian X/Y operators check 450
local cases across the declared deltas and arbitrary starting times. The
four-level calculations also transform the Hamiltonian, state and operators
together into a Fourier basis. Direct dense derivatives independently check
C. The symmetric-logarithmic-derivative equation is checked using
`rho_dot=-i[H,rho]`, `L=2*rho_dot`, and `F_Q=Tr(rho*L^2)`.

| Independent check | Maximum recorded error |
| --- | ---: |
| Dense-operator R against gap formula | 8.88e-16 |
| Readout-distance invariance under starting time | 1.84e-15 |
| Taylor sandwich after division by delta squared | 1.37e-11, within the declared 2e-10 slack |
| Symmetric-logarithmic-derivative equation | 1.12e-16 |
| QFI against four times the energy variance | 1.78e-14 |

The record retains every grid discrepancy, signed error-ball margin and
classification, plus vectors for the declared stroboscopic midpoint
witnesses. All 420 candidate/radius midpoint cases and the local midpoint
checks pass. No case fell in the declared 1e-10 numerical borderline band;
that band is a floating-point convention, not an interval-arithmetic proof.
State-array and configuration hashes remain unchanged. Review found no
correction needed to the admitted equations or implementation.

The study ran remotely on CPU at 18:10 UTC on 4 October 2026, with NumPy
2.5.3, SciPy 1.18.1 and two BLAS threads. The measured calculation took
0.415 seconds; the complete captured record is 3,069,035 bytes. The duration
excludes environment installation, preparation and the separate test run.
No GPU or peak-memory benchmark was used.

`artifacts/studies/time-ambiguity-001/` contains numerical arrays, the full
report, manifest and exact producing source/test/protocol copies. SHA-256:

- Protocol: `d92be654d9e360ee83ca8d5050925ba1c18abd707c4b17bc459a05847f5bf0cc`
- Numerical arrays: `0cd9a1734ade731df89783e358404c12f4c043953201e30399f84f8782da7b4e`
- Report: `37a81824c77cb0c48edae39e37c40cb58593563ff92348f11f5b49c16e520062`

The contribution is the explicit finite comparison, its reproducible controls
and an authored artistic interpretation. The inequalities, quantum Fisher
identity and overlap geometry are established mathematics. Parameters and
pure fixed populations are assumed known; mixed-state inference, measurement
backaction, physical memory and irreversible loss are outside this model.
The human reading is that recognizing change and recognizing where one is
in time are different acts. That reading belongs to the artwork, not to a
new physical law or a result about human perception.
