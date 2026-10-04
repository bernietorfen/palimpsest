# Six crossings of a shared origin

This is an interactive continuation of the already published observer diagnostic,
using the original near-receiver 96/192 trajectories. No writing histories or
material states were regenerated. The design and its verification boundary were
recorded in `OBSERVER-INTERACTION.md` before producing the compact coefficients.

For a fraction alpha of the measured common translation, each squared RMS
candidate distance is a quadratic in alpha. The quadratic term is identical for
all candidates, so differences between candidate distances are affine. Taking
the lower envelopes of these candidate lines gives six nearest-reader changes
on the interval from zero to complete alignment:

| History | Original choice | Own-history crossing alpha |
| --- | --- | ---: |
| DABC | BDAC | 0.07184506374634762 |
| DCBA | BCDA | 0.09670653824791368 |
| BACD | ABCD | 0.23704115699143416 |
| BDCA | DBCA | 0.3157843303410602 |
| BADC | ABDC | 0.3227221441800121 |
| BDAC | DBAC | 0.3557742942086933 |

Each listed point is a tied nearest pair within the declared 1e-15 Hz-squared
numerical tolerance. The displayed unique-own count is 18 through 23 at the
successive ties. Past the last crossing, all 24 histories select their own
reference through full alignment. The other 18 histories keep their original
correct choice throughout. In this coefficient representation, affine candidate
contrasts preserve a strict own-choice inequality between endpoints where it
already holds; the transition record enumerates the changes.

The independent verifier uses direct dot-product norms of all 3,468 coordinates
at 35 positions, including both sides of every crossing and each crossing itself.
All 20,160 candidate comparisons agree with the compact reader's nearest sets.
The largest squared-distance discrepancy is 8.743006318923108e-16 Hz-squared.
It also independently checks each drawn own/rival projection.

The six visible strips are projections, each with its own pair-distance unit.
All counts and the full table use all 24 candidates in the recorded space. The
24-second automatic passage has authored timing and short dwells at the measured
crossings. Exported SVGs preserve the chosen fraction, candidate sets, dataset
hash, original input identities and embedded font license.

The collection supplies its own alignment origin. This remains a post-result
diagnostic of a complete balanced set, not a reader of one unknown history, an
audibility test, a general theory of timestep bias or a new material simulation.
