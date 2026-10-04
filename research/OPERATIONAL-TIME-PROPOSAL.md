# Two moments, one specimen

Proposal recorded 4 October 2026 at 19:06 UTC, before implementation or execution.

## Finite scope and budget

Construct one certified near return of the existing 32-level state and compare
two kinds of time discrimination. The search has at most 2,097,153 integer
candidates, an approximately 8 MiB integer table, a 120-second search limit,
a 256 MiB target for peak process memory, and a five-minute total calculation
limit. Use one CPU process, at most two BLAS threads and no GPU. Retain less
than 1 MiB of source, protocol, witness, small matrices, checks and hashes.
These are pre-execution limits and estimates; report actual costs afterward.
Stop and retain the failed gate if a limit is exceeded. Do not enlarge the
search or tune the target after seeing the result.

## The question

A fragment may return because the allowed observations omit relationships.
A whole state may instead come so close to returning that even the best
single-copy quantum measurement has little power to identify its time.
These are different operational limits. The proposed addition would make
that distinction explicit in a short companion section or expandable note.
It does not require another main exhibit or a jump in the film's timeline.

## Two known snapshot preparations

Retain the existing Hamiltonian and preparation, in units with hbar=1:

    E_(g,r) = r + b_g,  b=(0,sqrt(2),sqrt(3),sqrt(5)),
    g=0,...,3,  r=0,...,7,  p_(g,r)=1/32.

One register is prepared in either rho(0) or rho(t), with equal prior
probabilities. The observer knows both candidate preparations and receives
one copy, without a trusted external cycle count or a correlated time label.
A retained history or external reference can supply information outside this
model. This is a binary snapshot-discrimination task, not continuous tracking
of one system or estimation of an unrestricted unknown time.

Let P_g project onto group g and define E(rho)=sum_g P_g rho P_g. The
restricted observer's effective POVM effects commute with every P_g; this
includes any preprocessing and ancillas used to produce the final guess.
Arbitrary intergroup mixing would remove the restriction. At t=2*pi*n,

    U(t) = sum_g exp(-2*pi*i*n*b_g) P_g,
    E(U(t) rho U(t)^dagger) = E(rho).

The identity holds for any density matrix. Since
Tr(M rho)=Tr(M E(rho)) for a block-diagonal effect M, all permitted outcome
distributions coincide. The optimal restricted success probability is
exactly 1/2. E represents available information here; no physical dephasing
operation is applied to the evolving state.

For unrestricted quantum measurements, the established Holevo–Helstrom
bound gives

    D = ||rho(0)-rho(t)||_1/2,
    P_success = (1+D)/2,  P_error = (1-D)/2.

The positive-eigenspace projector of rho(0)-rho(t) attains the bound.
For the specified pure preparation, D=sqrt(1-|<psi(0)|psi(t)>|^2).
The previous record gives D(2*pi)=0.9912216532462548, implying about
99.561% unrestricted success despite the restricted observer's 50%.
The selected 31-edge expectation readings are not asserted to implement
this optimal single-copy measurement. The measurement theorem and exact
assumptions are set out in [Watrous, Scenario 3.2 and Theorem 3.4](https://cs.uwaterloo.ca/~watrous/TQI/TQI.3.pdf).

## A constructive near return

The admission target is D<=0.05, so unrestricted single-copy success is at
most 52.5%. Choose Q=128, the first power of two for which
pi*sqrt(3)/Q<0.05. Divide the unit cube into Q^3 equal boxes and consider
the fractional triples k*(sqrt(2),sqrt(3),sqrt(5)) for k=0,...,Q^3.
Stop at the first repeated box, with indices k>l, and set n=k-l.
Pigeonhole guarantees a collision and integers m_s satisfying

    1 <= n <= Q^3,
    |n*sqrt(s)-m_s| < 1/Q,  s in {2,3,5}.

Use exact integer square roots to obtain each coordinate of the box:

    f_s(k) = isqrt(s*k*k),
    h_s(k) = isqrt(s*(Q*k)^2),
    B_s(k) = h_s(k) - Q*f_s(k),
    m_s = f_s(k)-f_s(l).

Retain k, l, n, all integer roots and their squared enclosing inequalities,
the equal box coordinates and m_s. These integer facts certify the phase
bounds independently of floating-point argument reduction.

At t=2*pi*n, the eight phases in each group coincide. With
z_0=1 and z_s=exp(-2*pi*i*(n*sqrt(s)-m_s)), the equal group masses give

    D^2 = (1/4) sum_g |z_g - mean(z)|^2
        <= (1/4) sum_g |z_g - 1|^2
        <= 3*pi^2/Q^2 < (1/20)^2.

The final strict inequality can be certified using pi<22/7 and integer
arithmetic. High-precision D supplies an independent value alongside this
exact inequality; numerical closeness is not the certificate. Simultaneous
Diophantine approximation is an established recurrence method, discussed
in [Gupta and Short, Section III](https://arxiv.org/html/2604.14995).
This application claims no new recurrence theorem or optimal recurrence time.

## Declared verification gates

1. The exact integer collision certificate passes, with 4096<n<=128^3.
   A smaller n is retained as a discrepancy with the earlier finite record,
   not silently replaced. This is one constructed return, not the first
   return in continuous time or even the first qualifying grid point.
2. Independently evaluate the original 32 energies and amplitudes at
   t=2*pi*n with 80 decimal digits, and the reduced four-group phases.
   Their state entries agree within 1e-60. D<=0.05 and D>0; the ideal
   irrational model cannot have an exact positive global return.
3. Form dense density matrices from the independently evaluated amplitudes.
   Trace-norm D and the pure-state formula agree within 2e-12. An explicit
   Helstrom projector is positive, complete with its complement and
   idempotent within 2e-12, and its achieved success agrees within 2e-12.
4. Check the restricted block-state identity at n=1 and the new n, within
   2e-12. At n=1, D>0.9. A fixed Fourier basis change transforms states,
   projectors and effects together and preserves all distances and success
   probabilities within 2e-12.
5. Identical-state and the existing commensurate (0,1,2,3) full-return
   controls have unrestricted success 1/2 within 2e-12. The non-stroboscopic
   separation t=0.2 has restricted success greater than 0.501, checking that
   the restricted algebra is not blind to all change.
6. Preserve all pass/fail outcomes, exact witness integers, small reference
   matrices, source/protocol copies and hashes. No existing state, study
   record, browser fixture or graph assumption is modified.

## What this would and would not add

The worthwhile contrast is: a hidden relation can make two times legible,
but a sufficiently close full return leaves little information in one
specimen. The mathematics supports that contrast under an explicit resource
restriction. It does not establish a universal unknowability of time.
For M independent copies of the specified pure states, with squared overlap
F, the tensor-product formula gives D_M=sqrt(1-F^M); unequal states become
more distinguishable with more copies. We will state this boundary, without
another copy-count study.

The previous eta-ball experiment concerned uncertainty in ensemble
expectation vectors. Its deterministic error norm is not used as quantum
measurement noise here. Neither probability claim bounds exact classical
computer readouts, the rendered image, human perception, or arbitrary mixed
state reconstruction. Nearness of states alone does not certify perceptual
similarity of authored geometry, materials, camera or music. No state is
erased, and no new physical law or mechanism of human memory is proposed.
