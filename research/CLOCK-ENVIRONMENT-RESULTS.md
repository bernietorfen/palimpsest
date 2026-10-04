# How much isolation does a return require?

The recorded near return belongs to an isolated clock. In the declared
32-by-2 comparison, adding a weak, finite phase interaction changes that
return substantially. Entanglement is one possible part of the changed
relationship, but it is not necessary: an environment that remains in a
product state also disrupts the isolated return.

The first admission record passed all 1,172 numerical gates. Ten focused
tests passed before execution. The calculation used exactly the six
preregistered times and three preparations; no parameter search, time scan
or enlarged experiment was performed. The source and pre-execution protocol
are captured with the record.

## The previously returned clock

At cycle n=4109, t=2*pi*n, the results are:

| Environment preparation | Clock return distance D_S | Environment distance D_E | Joint distance D_SE | Joint entanglement |
| --- | ---: | ---: | ---: | --- |
| Uncoupled reference, chi=0 | 0.017388885 | 0 | 0.017388885 | Product |
| Pure coherent state, \|+> | 0.891417417 | 0.635119184 | 0.929294391 | Entropy 0.946660194 bits; negativity 0.481396724 |
| Maximally mixed state, I_2/2 | 0.891417417 | 0 | 0.929294261 | Separable by explicit decomposition |
| Eigenstate, \|0> | 0.929475066 | 0 | 0.929475066 | Product throughout |

The isolated reference reproduces the earlier distance within 9e-18. The
coupled pure-environment preparation passes both declared narrative gates:
D_S>0.5 and entanglement entropy>0.5 bits. Its same-time distance from the
isolated clock is 0.891359782; this is a disturbance measure, distinct from
the return distance to the initial clock.

Every within-group block still agrees with the isolated clock. The added
interaction acts only through relationships between groups. The clock can
therefore retain exactly the same fragment observations while its full
state behaves differently.

The two controls are essential to that interpretation. The coherent and
maximally mixed environment preparations produce identical reduced clock
states at every time, although the latter joint state is an explicit
separable mixture. The eigenstate preparation remains a product state and
produces an even larger clock return distance at this witness. Accumulated
coherent detuning alone is sufficient to change the return. Reduced-clock
observations cannot establish which of these mechanisms produced them.

Each distance compares two known snapshot preparations, at 0 and t, with
equal priors and one copy. Optimal success using only the named register is
(1+D)/2. No external cycle count, retained history, correlated time label or
purification of the mixed environment is supplied. Thus clock-only optimal
success at n4109 changes from about 50.869% for the isolated reference to
94.571% for either of the matched reduced-clock preparations, or 96.474%
for the product detuning control. This is a discrimination task, separate
from the earlier ensemble expectation-value readouts.

## Returning purity is not returning the joint state

The primary pure-environment preparation gives the following six rows.
Numbers rounded to zero or one below have residuals retained in the record.

| Cycle n | D_S | D_E | D_SE | Entanglement entropy, bits | Negativity |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 | 0 | 0 |
| 1 | 0.991221558 | 0.000001974 | 0.991221721 | 0.000040255 | 0.001404961 |
| 1250 | 0.863081361 | 0.500000000 | 0.969269236 | 1.000000000 | 0.500000000 |
| 2500 | 0.836148863 | 1.000000000 | 1.000000000 | 0 | 0 |
| 4109 | 0.891417417 | 0.635119184 | 0.929294391 | 0.946660194 | 0.481396724 |
| 5000 | 0.753341268 | 0 | 0.753341268 | 0 | 0 |

At n=1 the joint state is only 0.001404962 from the isolated product state
at the same instant, below the preregistered 0.002 gate. The coefficient is
weak compared with the within-group energy gap; its accumulated phase need
not remain small at a distant return.

At n=1250 the interaction produces exactly one bit of entanglement in the
primary preparation. At n=2500 it factorizes again. The clock is pure, but
the environment is now |->, orthogonal to its initial |+>. Access to that
environment perfectly distinguishes the two snapshots. Disentanglement
does not imply that the environment has returned.

At n=5000 the interaction unitary is exactly -I_64. Each preparation then
matches its isolated clock state tensored with its original environment at
the same time. However, the isolated clock itself has distance 0.753341268
from its initial state. This is an exact interaction return, not a full
clock or joint recurrence. Neither n=4109 nor any other sampled time is
claimed to be the earliest return.

## Model and exact controls

Units and normalization follow the
[preregistered protocol](CLOCK-ENVIRONMENT-PROPOSAL.md): hbar=1,
E_(g,r)=r+b_g with b=(0,sqrt(2),sqrt(3),sqrt(5)), four groups of eight modes,
and uniform initial population 1/32. The environment has two levels and no
free Hamiltonian. With A=(-3,-1,1,3), repeated across each group,

    H = H_S tensor I_2 + chi*A tensor Z,   chi=1/10000 exactly.

The interaction norm is 0.0003 in units where the within-group gap is one.
A has zero population mean. The interaction commutes with H_S and causes
no energy exchange. All dynamics are finite and jointly unitary.

For the coherent environment preparation, write phi=chi*t. The independently
checked formulas are

    (rho_S)_jk = (rho_iso)_jk cos[phi*(a_j-a_k)],
    Gamma = cos(4*phi) cos(2*phi),
    rho_E = [[1,Gamma],[Gamma,1]] / 2,
    lambda_+/- = (1 +/- |Gamma|)/2,
    entropy = h_2(lambda_+),
    purity = (1+|Gamma|^2)/2,
    negativity = sqrt(lambda_+*lambda_-).

Only the pure joint preparation permits identifying marginal entropy with
entanglement entropy. For the mixed-environment control, separability is
established by the actual product-state decomposition, not inferred from
zero negativity. Zero negativity is not a general separability criterion
in the 32-by-2 setting.

The exact interaction identities are

    n=1250: phi=pi/4, Gamma=0;
    n=2500: phi=pi/2, U_int=-i*sin(pi*A/2) tensor Z;
    n=5000: phi=pi, U_int=-I_64.

The mixed preparation is the equal mixture of the two product evolutions
V_+ rho_0 V_+^dagger tensor |0><0| and
V_- rho_0 V_-^dagger tensor |1><1|. The eigenstate preparation uses only
the first branch. These exact controls explain why identical clock
marginals do not establish entanglement and why detuning remains a rival
explanation.

## Independent checks and retained evidence

Original large-argument phases were evaluated at 80 decimal digits. Full
64-dimensional density matrices were compared with an independently
constructed eight-dimensional group-by-environment model. Both partial
traces were checked by tensor contraction and by explicit subsystem
operators. Dense matrix exponentials supplied an independent propagation
route, including a local Fourier/Hadamard basis change with transformed
Hamiltonian, states and measurement operators.

The maximum dense-propagation trace-distance discrepancy was 3.727e-11,
below its declared 2e-9 tolerance. The largest partial-trace comparison
error was 1.671e-15. The largest local-basis covariance discrepancy was
1.509e-13. Analytic marginal and entanglement checks passed their declared
2e-12 numerical and 2e-10-bit entropy tolerances. Partial-trace contraction
and explicit achieved Helstrom probabilities passed for all 18 cases.
Numerical probabilities are not interpreted as physically exceeding one
when roundoff is a few parts in 10^15.

The old pure-overlap distance and graph certificate were not applied to
mixed marginals. All reported distances use density-matrix trace norms.
The earlier three studies' 26 retained files were hashed before and after
this calculation and were unchanged.

The complete admission record is
[run-001/report.json](../artifacts/studies/clock-environment-001/run-001/report.json),
with full state and marginal arrays, compressed measurement projectors,
spectra, exact-control residuals, all gates, source copies and a file
manifest. There were no failed admission gates in this run. The focused
tests include an intentional calculation failure that verifies retention
of its exception, failed gate, source copies and manifest.

| Quantity | Recorded value |
| --- | ---: |
| Scientific calculation wall time | 0.259870386 seconds |
| Scientific calculation CPU time | 0.714010796 seconds |
| Peak process memory | 67,772,416 bytes |
| BLAS thread ceiling | 2 |
| GPU use | None |
| Full retained admission package | 458,890 bytes |
| Admission gates | 1,172 passed |
| Focused tests, before execution | 10 passed in 0.35 seconds |

SHA-256 receipts:

    record.npz
    9a32552b5c453e986f27ee421b9cacef418bb8ed2f35f60734d3bfe2087803f9
    report.json
    b6235865c516fbd4e9f10ef5fd6608f767299b6c1df7e2218ee849a3c8c570e3
    manifest.json
    4f0503de9dd3c893787c65c2a930b584fb2c30cb8cd67488cae9872f4603c0c3
    studio/clock_environment.py
    ccbca46c82f2ee2edbd8d46227ab3d7e6148420e9e6b6f5dbfd9f5adb7bd2308
    studio/tests/test_clock_environment.py
    246d499f2832182eee41810d6f71c6c3169180f1f32c7cc3bf779d76bd4c7c1c
    research/CLOCK-ENVIRONMENT-PROPOSAL.md
    7ed7ebb6b6703ee375aabf0f96aeaff8baa9a40aa3110f166c579f7e990ff32b

Reproduction uses the captured sources and declared dependencies. First
restore or generate the three prerequisite records at the canonical paths
`artifacts/studies/relational-clock-001`, `artifacts/studies/time-ambiguity-001`
and `artifacts/studies/operational-time-001`; the environment study's
admission checks require these records and verify that they remain unchanged.
Follow `RIVER-REPRODUCTION.md` for the exact sequence. Use a new output
directory for this study so the recorded evidence cannot be overwritten:

```sh
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python -m pytest -q studio/tests/test_clock_environment.py
OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python -m studio.clock_environment --output artifacts/studies/clock-environment-reproduction
```

## Scope and primary sources

This is an authored finite comparison of an existing return witness under
a standard controlled-phase interaction. It supplies neither a new
decoherence mechanism nor a theorem about generic environments. One qubit
is not a thermal bath or a macroscopic history. The experiment establishes
no irreversible arrow, information destruction, collapse or literal model
of human memory. The new coupled model was not used to generate the film.

Any register included in an exact joint return would itself return; no
register included in such a return could retain a distinguishing record
of the intervening evolution. External records or trusted cycle counts
would change the stated discrimination task.

The finite spin-environment construction and conditional coherence factors
are established in [Cucchietti, Paz and Zurek, equations (1) and (4)-(8)](https://arxiv.org/pdf/quant-ph/0508184).
Their large-environment claims are not imported into this one-qubit study.
Negativity and its pure-state Schmidt formula follow
[Vidal and Werner, equation (4) and Proposition 8](https://arxiv.org/pdf/quant-ph/0102117).
The operational success formula and trace-norm contraction follow
[Watrous, Theorem 3.4 and Corollary 3.40](https://cs.uwaterloo.ca/~watrous/TQI/TQI.3.pdf).

## Independent high-precision review

A separately authored verifier imports no project generating module. It
reconstructed all 18 cases using 80-digit eight-dimensional Hermitian
operators, explicit partial traces and high-precision eigensolvers. All
comparisons passed; the largest difference from the admitted binary64
record was 2.463e-14. The review took 0.415598986 seconds.

The saved receipt is
[clock-environment-001.json](../artifacts/reviews/clock-environment-001.json),
14,356 bytes, SHA-256
`ba645c85b6bba5438b697ce461a7c88fc270b09432bd53cf4b9e0b535656f285`.
Its independent source, `studio/verify_clock_environment.py`, has SHA-256
`d12c852ef6ca97e047f4aa2d6b0f852bd11dd73e52cf85a3d4b867958338f77c`.
The receipt binds the same admitted report hash shown above. These 18
independent comparisons supplement the 1,172 protocol gates; they are not
counted again as gates or focused tests.
