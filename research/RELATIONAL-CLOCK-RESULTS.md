# A visible return with a hidden difference

The declared finite experiment passes all 61 admission checks. At the first
return of the four-level instrument's two observed pairs, the complete state
has trace distance **0.963902532850** from its beginning. Adding the missing
relationship exposes that difference. In the 32-level extension, every observed
within-group relationship returns while the full distance is **0.991221653246**.

This is an exact distinction in the specified mathematical model, checked
numerically against independently formed density matrices and measurement
operators. It does not say that information has been destroyed or that a
physical quantum system has been measured. The observation graph selects
relationships to read; its edges are not couplings in the Hamiltonian.

## What was calculated

The state is `psi_j(t)=sqrt(p_j) exp(-i E_j t)` with known positive populations,
unit total probability and hbar=1. Energies are angular frequencies per abstract
time unit. The state evolution is unitary. D is half the trace norm of the
density-matrix difference, hence lies between zero and one. R is the declared
weighted sum of squared complex coherence changes. It has no units and is not
normalized by the number of observed edges.

The four-level spectrum is `(0,1,sqrt(2),1+sqrt(2))`, with equal populations.
Its limited observer reads pairs `(0,1)` and `(2,3)`. At `t=2*pi`, both pair
coherences return analytically. The recorded residual is numerical roundoff:

| Case at `t=2*pi` | Observation discrepancy R | Full trace distance D |
| --- | ---: | ---: |
| Two disconnected observed pairs | 7.4429430e-33 | 0.963902532850 |
| Same pairs, total emphasis raised to match three edges | 1.1164415e-32 | 0.963902532850 |
| Add pair `(1,2)` with unit emphasis | 0.232277023209 | 0.963902532850 |
| All six pairs observed | D squared, by the complete-graph identity | 0.963902532850 |

The matched-emphasis control shows that increasing weights on the same
relationships does not recover the missing relative phase. This is an
algebraic control; weights were not identified with a physical measurement-shot
budget. Every observer consumed the same immutable state array.

For a true positive control, the commensurate spectrum `(0,1,2,3)` returns
globally at `2*pi`; its independently computed D is 2.7384e-16. For the
irrational spectrum, the declared later point `t=2*pi*169` has
D=0.00657229348734. This is a near return, not an exact one.

The absence of a positive exact global period follows from the ideal algebraic
parameters: the gap 1 requires `t=2*pi*n`, while the gap sqrt(2) would then
require `n*sqrt(2)` to be an integer. No positive integer n can satisfy that.
This is an analytic statement, not an inference of irrationality from numerical
samples. The executable stores finite floating-point approximations and does
not establish infinite-time arithmetic by computation. Approximate recurrence
is consistent with the established quantum recurrence framework.
[Bocchieri and Loinger](https://doi.org/10.1103/PhysRev.107.337).

## A bound that knows when the observer is weak

For a connected observation graph, the proof in
`RELATIONAL-CLOCK-PROTOCOL.md` gives `D^2 <= R/lambda`, where lambda is the
weighted graph spectral gap in the population metric. The complete graph
gives the exact identity `R=D^2`. A disconnected graph gives no such global
certificate: each component can carry a different unseen common phase.

| Emphasis of the connecting pair | Spectral gap lambda | R at `2*pi` |
| ---: | ---: | ---: |
| 0 | 0; disconnected | 7.4429430e-33 |
| 0.000001 | 2.49999874973e-7 | 2.32277023209e-7 |
| 0.0001 | 2.49987500000e-5 | 2.32277023209e-5 |
| 0.01 | 0.00248750031248 | 0.00232277023209 |
| 1 | 0.146446609407 | 0.232277023209 |

A raw acceptance threshold `R<=1e-6` admits the weak-bridge case even though
the complete state is still far from its beginning. The gap-aware certificate
does not make that error. At bridge emphasis 1e-6 with no observation error,
it bounds D by 0.963902773878. With weighted observation-error norm 0.001,
the tested certificate becomes the uninformative bound D<=1.

The noise calculation assumes a declared deterministic bound on complex
coherence error. It is not a simulation of quantum measurement shots. An
adversarial error was also set equal to the negative true change, making the
reported observation discrepancy zero. Accounting for that error still
prevented a false certificate of a close global return.

The generic spectral-gap bound is conservative. Adding observations cannot
remove information, but `R/lambda` need not monotonically improve at every
particular state; it uses a worst-direction constant for the whole phase
family. Some connected cases give only D<=1, and those outcomes remain in the
record. The work does not present every valid bound as an informative one.

## Thirty-two levels

The extension uses four groups of eight modes, with energies
`E_(g,r)=r+b_g`, `b=(0,sqrt(2),sqrt(3),sqrt(5))`, and populations 1/32.
Four within-group paths give 28 observed edges. Three bridges join them into
a connected path; the complete observer reads all 496 pairs.

| Observer at `t=2*pi` | R | Spectral gap |
| --- | ---: | ---: |
| Four separate paths | 6.6835374e-32 | 0 |
| Paths joined by three observed relationships | 0.0102955904907 | 0.000300954582988 |
| Every pair | 0.982520365864 | 1, to numerical precision |

The full-state distance is 0.991221653246 in all three cases. The connected
path reveals a change, while its general bound is loose at this point. The
complete observation discrepancy equals the squared full distance. Revealing
relationships changes access to the state, not the state itself.

## Verification and adversarial review

The record contains 4,103 times for each model. Explicit density-matrix
eigenvalues independently check trace distances throughout both time grids.
At eight declared special times, SciPy's dense matrix exponential supplies an
independent propagation route. For four levels, it is evaluated in both the
energy basis and a fixed Fourier basis, with states, Hamiltonians and
measurement operators transformed together.

| Check | Largest recorded absolute error |
| --- | ---: |
| State normalization, either model | 4.44e-16 |
| Dense propagation against direct phases | 2.30e-13 |
| Explicit Hermitian-operator coherences | 6.16e-14 |
| Four-level full-grid density-distance identity | 2.00e-15 |
| 32-level full-grid density-distance identity | 3.22e-15 |
| 32-level complete observation/variance identity | 6.00e-15 |

All connected-graph and bounded-error inequalities pass their declared
2e-11 numerical slack. The most negative observed bound slack is -1.67e-15.
Stationary, common-energy-shift and vertex-relabeling controls pass. Hashes
confirm that neither observer selection nor noise evaluation modified the
state arrays. Sixteen focused tests additionally cover nonuniform populations,
the imaginary-coherence sign, invalid graphs, absent support and mutation.

The implementation/proof review found no correction required to the admitted
equations or numerical results. The following boundaries are essential:

- The complete-graph identity counts unordered pairs exactly once. Summing
  both edge directions would introduce a factor of two.
- Basis invariance means transforming the Hamiltonian, state and observation
  operators together. Changing the meaning of the observed pairs is a
  different observer, not a harmless relabeling of the same experiment.
- Both quadratures of complex coherences matter. Every raw magnitude
  `|rho_jk|` is constant here; magnitude-only displays would conceal all the
  phase dynamics. The metric uses changes in the complex value.
- The graph theorem assumes the declared pure state family with known fixed
  positive populations. It is not general mixed-state tomography.
- The readouts are calculated ensemble expectation values, not simultaneous
  disturbance-free observations of a single unknown quantum object.
- Hidden phase has not been erased. There is no dissipation, entropy
  production or permanent memory in this unitary calculation. If a closed
  total system includes a record, an exact return of that total system also
  returns the record, by contraction under partial trace.
  [Watrous, Chapter 1](https://cs.uwaterloo.ca/~watrous/TQI/TQI.1.pdf).

Phase synchronization and graph spectral geometry are established subjects.
This project's contribution is their explicit finite application, reproducible
contrasts, and authored audiovisual interpretation. It does not claim a new
general recurrence theorem, a physical arrow of time, a hearing result or
universal artistic priority.
[Singer](https://arxiv.org/abs/0905.3174).

## Record

The study completed on 4 October 2026 at 17:42 UTC, using remote CPU only,
NumPy 2.5.3, SciPy 1.18.1 and two BLAS threads. The computation took 0.821
seconds; the complete captured record is 3,373,652 bytes. That duration excludes
environment installation, source preparation and the separate test invocation.
No peak-memory benchmark is claimed.

`artifacts/studies/relational-clock-001/` contains `record.npz`, `report.json`,
`manifest.json`, and exact copies of the producing source, tests and protocol.
The protocol hash is
`f7a12f52c823aa8c6468d4dcc0767b8b6f608abf0341d8b21f5eb8a4ee74d43d`.
The numerical-array file hash is
`8eab3ae818ec72572b4ecc2aab984795ace2f06023dfa8b6c29a42c0334ab524`.
The source/test hashes and every individual gate are retained in the report.

The scientific result supports a specific artistic tension: familiarity can
return within the part one can see while its relationships remain changed.
That human interpretation is an authored reading of the experiment, not a
deduction about human memory or the metaphysical nature of time.

## Browser arithmetic cross-check

A dependency-free browser core implements the same finite states, complex
coherences, distances and fixed observation graphs. Its compact 27,420-byte
fixture is generated from the admitted scientific record, including its
source hashes and independently evaluated graph gaps. No browser eigensolver
or trained model is involved.

Remote Node 18.19.1 verification compared 24 saved states and 84 observer
readings with the Python record. Maximum absolute errors were 2.78e-17 in
state amplitudes, 2.11e-15 in squared distance, 2.22e-16 in observation
discrepancy and 1.74e-18 in the checked complex coherence. Noise-certificate
bounds agreed exactly at the retained reference values. Frozen-array,
model-ownership and input-validation checks passed. These are arithmetic
checks, not a claim about a completed browser interface or its appearance.

The client work per state is linear in the number of modes and observed
edges: 32 phase evaluations and 31 selected edge contributions for the
connected larger instrument. The complete observer uses 496 edge
contributions. Changing the observer reuses the same immutable state; a
missing certificate is represented as unavailable, never as a zero bound.
