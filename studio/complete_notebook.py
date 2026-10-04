"""Extend the frozen first notebook with the playable and scientific continuations."""
import argparse
import json
from pathlib import Path

from studio.notebook import Book, MUTED, opening_pages, evidence_pages, atlas_pages, closing_pages
from studio.preserve import sha256


def continuation_pages(book, figures):
    record = json.loads((figures / 'report.json').read_text())
    for item in record['files']:
        if sha256(figures / item['path']) != item['sha256']:
            raise ValueError('A continuation figure changed after its record was written')

    book.page('The playable instrument', dark=True)
    book.heading('Your hand enters the loop.')
    book.image('site/assets/generated/live-material.jpg', 48, 211, 768, 340)
    book.paragraph('Play the twelve voices. Each held gesture writes into the shared material. Keep a phrase, then ask it again: the timing and pressure repeat, while the material carries the accumulated consequence.', 48, 186, 363, 11, 17)
    book.paragraph('Save the material to continue later. Take a measured vector drawing of two replies, or export the current surface as a closed sculpture. A portable edition includes the instrument, fonts and example files.', 453, 186, 363, 11, 17)
    book.text_line(48, 68, 'Original browser solver / WebGL surface / twelve synthesized voices', 9, 'Sans')

    book.page('A kept phrase')
    book.heading('Keep the question. Let the answer change.')
    book.image(figures / 'live-repeated-question.png', 48, 181, 501, 363)
    y = book.paragraph('These curves come from the actual paired drawing exported by the browser instrument. A 6.25-second phrase returns to material that has already received it.', 579, 515, 237, 10.5, 16)
    y = book.paragraph(f"The comparison contains {record['live_reply_samples']} samples of twelve voices. The two replies differ by <b>{record['live_reply_rms_hz']:.6f} Hz RMS</b>. Both panels share the same vertical scale.", 579, y - 19, 237, 10.5, 16)
    book.paragraph('Blue and ochre identify the two played voices. The other ten also respond through their shared inscription, fatigue and feedback.', 579, y - 19, 237, 10.5, 16)
    book.paragraph('The live solver uses a 64 x 64 grid at 96 steps per second. Its operation order is checked against the reference material. An exact replay on a fresh saved state reproduces the reply; this comparison intentionally retains the earlier writing.', 48, 153, 363, 10, 15)
    book.paragraph('Full state files preserve displacement, velocity, inscription, fatigue, delay and phase. Bounded recovery restores a tab after reload; a paused picture survives a tested graphics-context restoration. The first exported dialogue remains a separate, inspectable example.', 453, 153, 363, 10, 15)

    book.page('An imperfect hand')
    book.heading('What survives uneven pressure?')
    book.image('artwork/analysis/pressure-reading-003/the-imperfect-hand.png', 48, 87, 330, 440)
    y = book.paragraph('The ideal atlas writes every gesture at its nominal strength. Here each complete gesture receives its own pressure multiplier. All 120 histories are written eight times at each of three variation limits.', 417, 521, 399, 11, 17)
    y = book.paragraph('A second reader allows each candidate history to vary locally along five pressure directions. Its derivatives and rule were fixed before a fresh evaluation seed generated the 2,880 cases.', 417, y - 20, 399, 11, 17)
    top = y - 33
    for x, text in ((417, 'LIMIT'), (490, 'NEAREST'), (647, 'ALLOW PRESSURE')):
        book.text_line(x, top, text, 8.5, 'Sans', MUTED)
    for i, (limit, nearest, adjusted) in enumerate((('1%', 960, 960), ('3%', 904, 960), ('10%', 374, 881))):
        baseline = top - 25 - i * 28
        for x, text in ((417, limit), (490, f'{nearest} / 960'), (647, f'{adjusted} / 960')):
            book.text_line(x, baseline, text, 12, 'Mono')
    book.paragraph('At 10% variation, the pressure rule recovers 516 cases and loses nine. This is a finite identification experiment on simulated pitch records. It does not establish what a listener could hear.', 417, top - 116, 399, 10.5, 16)


def pressure_and_spatial_pages(book, figures):
    """Pages following the opening pressure-study spread."""
    record = json.loads((figures / 'report.json').read_text())
    case = record['lost_case']
    book.page('A failed correction')
    book.heading('A correction can misread, too.')
    book.image(figures / 'a-lost-reading.png', 48, 258, 768, 256)
    book.paragraph(f"The first loss in the study's ordered case list is <b>{case['history']}, realization {case['realization']}</b>. The nearest ideal answer identifies it correctly. Allowing pressure instead selects <b>{case['pressure_corrected']}</b>. The glyphs show four probe times on the same display scale; the decisions use all 4,032 pitch values.", 48, 231, 363, 10.5, 16)
    book.paragraph('The adjustment is an unconstrained local linear fit. It can explain away a meaningful difference between histories. At 10% variation, 209 of 960 winning adjustments exceed the actual pressure bound. The rule leaves 79 errors, including nine cases that the simpler reader got right.', 453, 231, 363, 10.5, 16)
    factors = ' / '.join(f'{value:.6f}' for value in case['pressure_factors'])
    book.text_line(48, 95, 'ACTUAL GESTURE MULTIPLIERS / IN WRITING ORDER', 8.5, 'Sans', MUTED)
    book.text_line(48, 73, factors, 11, 'Mono')

    book.page('Registered spatial refinement')
    book.heading('A mark, at three scales.')
    book.image(figures / 'registered-fields.png', 48, 267, 768, 256)
    book.paragraph('The retained inscription after D E A B C, at 1/192 second. The same analytic force patterns are sampled on three grids. All three fields use the original inscription scale, -0.8 to +0.8; no panel is independently normalized.', 48, 240, 363, 11, 17)
    book.paragraph('The echo stays at the original fractional location: 18/128 of the domain vertically and 11/128 horizontally. Finer-grid shifts are exact multiples. This registered construction prevents integer rounding from moving the feedback pattern as the grid changes.', 453, 240, 363, 11, 17)
    book.paragraph('The protocol was recorded before generation. All 120 nominal histories were rerun at 128, 256 and 512 samples per side, at both 96 and 192 steps per second: 720 canonical trajectories. The film and earlier studies remain frozen in their original grids.', 48, 105, 768, 9.5, 14)

    book.page('Reading across grids')
    book.heading('What survives refinement.')
    book.image(figures / 'spatial-reading-differences.png', 48, 209, 446, 321)
    book.paragraph('Every finer-grid response is nearest to its own history in the comparison atlas: 120 of 120, in all six spatial comparisons. The same is true of all three timestep comparisons.', 524, 517, 292, 11, 17)
    book.text_line(524, 405, 'AT 192 STEPS / SECOND', 9, 'Sans', MUTED)
    for row, (grids, rms, maximum) in enumerate((('128 > 256', '.003356', '.005464'), ('256 > 512', '.000795', '.001290'), ('128 > 512', '.004135', '.006749'))):
        y = 359 - row * 30
        book.text_line(524, y, grids, 10, 'Mono')
        book.text_line(640, y, rms, 10, 'Mono')
        book.text_line(735, y, maximum, 10, 'Mono')
    book.text_line(524, 382, 'GRIDS', 8, 'Sans', MUTED)
    book.text_line(640, 382, 'RMS / HZ', 8, 'Sans', MUTED)
    book.text_line(735, 382, 'MAX / HZ', 8, 'Sans', MUTED)
    book.paragraph('RMS combines all histories, voices and probe times. Max is the largest single-history RMS. Each line at left follows one of the 120 histories.', 524, 266, 292, 9.5, 14)
    book.paragraph('The aggregate adjacent-grid difference falls by about 4.2 times at both timesteps. The smallest pairwise history separation remains above 0.170 Hz. These observations support the tested identification result under this registered refinement.', 48, 169, 363, 10.5, 16)
    book.paragraph('Three finite grids do not prove continuum convergence, global stability or physical realism. Independent reconstruction checks all 71 study files and every distance, label and count; the largest distance discrepancy is below 4.45 x 10^-16 Hz.', 453, 169, 363, 10.5, 16)


def main(args):
    book = Book(args.output, 'Complete notebook / 4 October 2026')
    plates = Path('artwork/masters/plates-001')
    opening_pages(book, plates, Path('artwork/masters/diptych-002'), Path('artwork/notebook/figures-002'))
    evidence_pages(book, Path('artwork/notebook/figures-002'))
    atlas_pages(book, Path('artifacts/studies/history-atlas-001'), Path('artwork/analysis/history-refinement-001'))
    figures = Path(args.figures)
    continuation_pages(book, figures)
    pressure_and_spatial_pages(book, figures)
    closing_pages(book, plates)
    if book.page_number != 24:
        raise ValueError('The complete notebook must contain 24 pages')
    book.finish()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='artwork/masters/palimpsest-complete-notebook.pdf')
    parser.add_argument('--figures', default='artwork/notebook/continuation-001')
    main(parser.parse_args())
