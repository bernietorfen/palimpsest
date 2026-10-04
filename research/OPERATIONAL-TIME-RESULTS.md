# A hidden change and a nearly returned whole

The fixed integer construction found a full-state near return at cycle
**n=4109**, beyond the earlier candidate grid ending at 4096. This is a
constructed witness, not the first recurrence. The result gives a concrete
contrast between two kinds of time ambiguity: missing relationships and
states that are close even when all quantum measurements are permitted.

All 169 recorded admission checks and 11 focused tests pass. The model,
Q=128, target D<=0.05 and resource limits were declared before execution.

## Two snapshots, one copy

The task supplies one quantum register in one of two known states, rho(0)
or rho(2*pi*n), with equal prior probabilities. There is no trusted external
cycle count, correlated time label or retained history. Such information
would be outside this task and can change what is inferable. The preparation
is the existing uniform pure 32-level state with energies
E_(g,r)=r+b_g, b=(0,sqrt(2),sqrt(3),sqrt(5)), r=0,...,7 and hbar=1.

| Candidate cycle n | Pure-state trace distance D | Best success with observations confined within groups | Best success with unrestricted quantum measurement |
| --- | ---: | ---: | ---: |
| 1 | 0.991221653246254708 | 50% | 99.5610826623% |
| 4109 | 0.017388884873856538 | 50% | 50.8694442437% |

These are calculated optimal probabilities, not observed success frequencies
or claims about a viewer. The selected 31-edge ensemble readout used in the
earlier experiment is not asserted to implement the unrestricted optimum.

For equal priors, the Holevo–Helstrom theorem gives

    P_success = (1+D)/2,  P_error = (1-D)/2,
    D = ||rho(0)-rho(t)||_1/2.

The positive-eigenspace projector of rho(0)-rho(t) attains this probability.
The known-state, single-register task and measurement proof appear in
[Watrous, Scenario 3.2 and Theorem 3.4](https://cs.uwaterloo.ca/~watrous/TQI/TQI.3.pdf).
For the pure preparation, D=sqrt(1-|<psi(0)|psi(t)>|^2).

## Why the restricted result is exact

Let P_g project onto an eight-mode group. Every allowed effective POVM
effect commutes with all P_g, including any preprocessing used to make the
final decision. An arbitrary unitary mixing groups would violate that
restriction. At every integer cycle,

    U(2*pi*n) = sum_g exp(-2*pi*i*n*b_g) P_g.

Writing E(rho)=sum_g P_g rho P_g therefore gives E(U rho U^dagger)=E(rho)
for any density matrix. A permitted effect M satisfies
Tr(M rho)=Tr(M E(rho)), so every permitted outcome distribution is identical
for the two snapshots. With equal priors the best success is exactly 1/2.
This extends the selected-pair example to the whole restricted algebra.
E represents an information restriction; no dephasing or erasure operation
is applied to the evolving state.

The restriction is not blindness to all change. At the declared nearby
separation t=0.2, its optimal success is 71.9802352796%, while the
unrestricted optimum is 73.1970775799%. The identical-state and
commensurate full-return controls have success 1/2.

## The exact integer certificate

The search assigns the fractional triples k*(sqrt(2),sqrt(3),sqrt(5)) to
128^3 boxes. The first repeated box in its prescribed order occurred at
k=4110 and l=1. Their common box was (53,93,30), giving n=k-l=4109.
Only 4111 candidates were examined, below the fixed 2,097,153 endpoint.
The resulting integer vector is m=(5811,7117,9188).

For s in {2,3,5}, the certificate stores

    f_s(k) = floor(k*sqrt(s)),
    h_s(k) = floor(128*k*sqrt(s)),
    B_s(k) = h_s(k)-128*f_s(k).

| Index | s | f | h | B |
| --- | ---: | ---: | ---: | ---: |
| 4110 | 2 | 5812 | 743989 | 53 |
| 4110 | 3 | 7118 | 911197 | 93 |
| 4110 | 5 | 9190 | 1176350 | 30 |
| 1 | 2 | 1 | 181 | 53 |
| 1 | 3 | 1 | 221 | 93 |
| 1 | 5 | 2 | 286 | 30 |

The independent certificate checker uses only integer arithmetic:
f^2<=s*k^2<(f+1)^2, h^2<=s*(128*k)^2<(h+1)^2, equal B values in [0,128),
and the differences m_s=f_s(4110)-f_s(1). These facts imply
|4109*sqrt(s)-m_s|<1/128. The certificate does not depend on numerically
reducing a large floating-point phase.

At an integer cycle the eight phases in each group agree. Set z_0=1 and
z_s=exp(-2*pi*i*(n*sqrt(s)-m_s)). For equal group masses, the weighted
variance identity and comparison to reference phase 1 give

    D^2 = (1/4) sum_g |z_g-mean(z)|^2
        <= (1/4) sum_g |z_g-1|^2
        <= 3*pi^2/128^2.

Thus D<=pi*sqrt(3)/128, approximately 0.042510923. Using pi<22/7, the
stronger-than-target comparison with (1/20)^2 is the integer inequality
580800<802816. This proves D<0.05 for the certified witness independently
of the numerical D value. The ideal irrational spectrum has no exact
positive global return: the unit energy gap requires t=2*pi*n, while
n*sqrt(2) cannot then be an integer for positive n.

Pigeonhole supplies the finite search guarantee, not an optimal return-time
estimate. Simultaneous Diophantine approximation is an established approach
to recurrence; see [Gupta and Short, Section III](https://arxiv.org/html/2604.14995).
Neither that general method nor this inequality is claimed as a new theorem.

## Independent values and implementation checks

An 80-decimal-digit calculation evaluates all 32 original energies at the
unreduced time 25817.608427200920833686. A separate route evaluates the
four residual phases from the integer witness. Their maximum amplitude
difference is 4.34e-77. The independently obtained value is

    D = 0.01738888487385653785640082896549865497154124374699...

The three residuals n*sqrt(s)-m_s are approximately
0.003527791048, -0.003231699483 and 0.003319546636. Their smallness is a
numerical illustration of the exact certificate, not its justification.

Dense density matrices constructed from the original amplitudes give the
trace norm independently of the pure-overlap formula. Actual Helstrom
projectors are checked for positivity, completeness, idempotence and
achieved discrimination probability. A Fourier basis change transforms
states, effects and group projectors together; the probabilities and
distances remain unchanged within the declared 2e-12 tolerance. The
focused tests also show why intergroup preprocessing invalidates a
restriction imposed only on the final detector.

The first execution failed in a reporting helper because a keyword collided
with its positional argument. That source and exception are retained in
`artifacts/studies/operational-time-001/failed-run-001/`; no admission result
is asserted for that attempt. The helper was corrected and a failure-path
preservation test added. The same protocol, target and search limits then
produced the passing `run-002/` record. No scientific gate was relaxed.

The passing calculation used 0.0902 seconds wall time, 0.1443 seconds CPU
time and a measured peak process size of 44,900,352 bytes. Its integer table
used 8,388,608 bytes. The captured passing record is 303,112 bytes; including
the retained failed attempt, the study is 360,003 bytes. It used two bounded
BLAS threads and no GPU. Durations exclude installation and separate tests.

The saved `run-002/` manifest verifies source/protocol copies, matrices,
high-precision values, all checks and hashes. SHA-256:

- Protocol: `eed319fa322d61b2c2661d0471733fa89ab6ae626ef053cfa26ecf9a67306c60`
- Numerical arrays: `5038c3c748e72766efb4e078d4874eec88d4ea3567f004dcb9b8ce47ddc505fd`
- Report: `df9c3ce82d6bdfc4dd61b35f3de6638cf18b495541bbfd035f6932831157f903`

## Meaning and limits

The previous no-hit result applied only to its declared 4096-cycle grid.
The constructed 4109-cycle witness makes that finite boundary tangible.
It does not identify the earliest qualifying recurrence on a longer grid
or over continuous time, and no broader search was performed.

The one-copy task is distinct from deterministic eta-balls around ensemble
coherence readings. There is no conversion here from eta to a quantum shot
budget. With M independent copies of the specified pure preparations and
squared overlap F, the tensor-product formula gives D_M=sqrt(1-F^M).
More copies can distinguish nonidentical states more reliably; the result
does not establish permanent unknowability or a limit on noiseless classical
computation. Nor does it certify similarity of a nonlinear rendering,
measure a human response, or describe irreversible loss. The contribution
is the authored finite comparison, its exact witness and its reproducible
operational interpretation.
