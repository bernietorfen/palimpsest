# Received histories: locked follow-up

Fixed on 4 October 2026, before executing this follow-up. The existing transfer
experiment establishes retained differences after indirect writing; it does
not establish that an untouched receiver distinguishes the order of equal
writing ingredients. This follow-up asks that narrower question. It was chosen
after the earlier explorations and transfer results, not independently of them.

## Construction

Use the admitted three-body chain from `choir_transfer_study.chain`, unchanged:
source 0, receiver 1, receiver 2; 64 x 64 body grids; feedback 0.08; two sixteen-
bead bridges at tension 1.6, mass 0.65, damping 0.24; reciprocal width-0.16 ports.
Use all 24 permutations of these four source-only contacts:

| Token | x | y | Amplitude | Polarity |
|---|---:|---:|---:|---:|
| A | 0.165 | 0.345 | 0.85 | +1 |
| B | 0.215 | 0.395 | 0.78 | +1 |
| C | 0.190 | 0.370 | 0.92 | -1 |
| D | 0.215 | 0.345 | 0.71 | +1 |

Each contact has attack 0.7 s, hold 0.8 s and release 3.0 s. The order fills
fixed onsets 2, 8, 15 and 22 seconds. Source footprints have width 0.16 and RMS
one, as in the earlier study. Write until 30 seconds. Reordering preserves the
four prescribed contact envelopes, locations and signed amplitudes; it does
not prescribe equal realized mechanical work.

Cut all links and clear transient state: u=p, velocity, delay and phase zero.
Give each receiver the earlier quiet question: mode 0 at 1 second, mode 4 at
4 seconds, mode 8 at 7 seconds; amplitude 0.025, attack 0.5, hold 0.4, release
1.6 seconds. Record all twelve pitch readouts at 24 Hz for twelve seconds,
including the endpoint (289 times). Do not probe or mix the source. Repeat the
complete procedure at 96 and 192 steps per second on the same spatial grid.

Compute connected, inscription-erased, wear-erased and both-erased probes from
the same written retained fields. A fresh isolated receiver gets the identical
question at each rate. Preserve every initial field intervention and readout.
The already completed broken-link study remains separate; it is not silently
recounted as a control in this follow-up.

## Admission and evaluation

Batch at most eight independent chains (24 bodies). Before the full evaluation,
compare one packed connected chain against the same chain simulated alone for
six seconds. Require maximum field disagreement <= 2e-6 and pitch disagreement
<= 1e-4 Hz, and finite values. Failure stops evaluation; changing this numerical
admission needs a separately recorded protocol revision, not an unlabeled retry.
No bridge or force may connect different histories in the batch.

For each receiver and timestep compute all 276 pairwise RMS pitch distances
across the twelve modes and 289 times. Report the minimum, median, maximum,
closest pair and every matrix entry. Also report same-ending and same-last-two
subsets, without separate advancement gates. Partial erasure results are full
alternative observations, not additive contributions.

For each fine-timestep trajectory identify its nearest coarse-timestep
trajectory under the same RMS metric; report every label and distance, including
mistakes. No fitted classifier, adaptive weighting or rematching of time is used.

Advance the claim that *this selected distant receiver resolves all tested
orders across this timestep check* only if receiver 2 meets all of:

1. Every connected pair differs by more than 0.001 Hz RMS at both rates.
2. All 24 finer responses have their own history as the unique nearest coarse
   response.
3. Every both-erased response equals the fresh isolated control to within
   1e-6 Hz maximum absolute difference, and all arrays are finite.

The threshold is a numerical admission margin, not a hearing threshold. A
failure will be retained and reported without tuning the contacts, reader,
bridge, threshold or timestep to rescue this claim. Receiver 1, partial erasure
and shared-ending results are reported regardless of the primary outcome.

These deterministic permutations are the complete selected four-token universe,
not a sample from human gestures or a capacity estimate. The study does not
establish audibility, pressure robustness, continuum convergence, biological
memory or infinite-time arithmetic rank. It investigates one original finite
material and one explicitly chosen observation.
