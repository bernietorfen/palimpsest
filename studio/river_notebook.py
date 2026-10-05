"""Build and render the nine-page A River Twice companion on the computation host.

Artwork and production receipts are explicit inputs. A missing receipt never
becomes a claim that a film was rendered, heard or perceptually validated.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time

import pymupdf as fitz
from PIL import Image, ImageDraw
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from threadpoolctl import threadpool_limits

from studio.river_science_figures import make_figures, digest, PAPER, INK, TEAL, AMBER, MUTED, LINE


WIDTH, HEIGHT = 595.276, 841.89
MARGIN, CONTENT = 46., 503.276
PAGE_COUNT = 9
SOURCES = (
    'studio/river_notebook.py', 'studio/river_science_figures.py',
    'research/RIVER-COMPANION.md', 'research/RIVER-SCORE.md',
    'research/RIVER-EDITION.md', 'research/RIVER-REPRODUCTION.md',
    'research/RELATIONAL-CLOCK-PROTOCOL.md', 'research/RELATIONAL-CLOCK-RESULTS.md',
    'research/TIME-AMBIGUITY-PROPOSAL.md', 'research/TIME-AMBIGUITY-RESULTS.md',
    'research/OPERATIONAL-TIME-PROPOSAL.md', 'research/OPERATIONAL-TIME-RESULTS.md',
    'research/CLOCK-ENVIRONMENT-PROPOSAL.md', 'research/CLOCK-ENVIRONMENT-RESULTS.md',
    'studio/clock_environment.py', 'studio/tests/test_clock_environment.py',
    'studio/verify_clock_environment.py',
)


def fonts():
    paths = {
        'Sans': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        'SansBold': '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        'Serif': '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
        'SerifItalic': '/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf',
        'Mono': '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
    }
    for name, path in paths.items():
        pdfmetrics.registerFont(TTFont(name, path))
    pdfmetrics.registerFontFamily('Sans', normal='Sans', bold='SansBold', italic='Sans', boldItalic='SansBold')
    pdfmetrics.registerFontFamily('Serif', normal='Serif', bold='Serif', italic='SerifItalic', boldItalic='SerifItalic')
    return {name: {'filename': Path(path).name, 'sha256': digest(path)} for name, path in paths.items()}


def copy_font_licenses(output):
    """Retain installed font notices in the package, separately from the PDF."""
    folder = output / 'licenses'
    folder.mkdir()
    receipt = {}
    for family, source in (
        ('dejavu', Path('/usr/share/doc/fonts-dejavu-core/copyright')),
        ('liberation', Path('/usr/share/doc/fonts-liberation/copyright')),
    ):
        target = folder / f'{family}-fonts-copyright.txt'
        shutil.copy2(source, target)
        receipt[family] = {'file': str(target.relative_to(output)),
                           'bytes': target.stat().st_size, 'sha256': digest(target),
                           'scope': 'Installed font license text copied into the source package; not a PDF attachment.'}
    return receipt


class Book:
    def __init__(self, output, art_status):
        self.output = output
        self.raw_path = output / 'layout.pdf'
        self.c = canvas.Canvas(str(self.raw_path), pagesize=(WIDTH, HEIGHT), pageCompression=1, invariant=1)
        self.c.setTitle('A River Twice / An illustrated scientific companion')
        self.c.setAuthor('Codex')
        self.c.setSubject('Return, incomplete observation, local precision and distant ambiguity')
        self.c.setCreator('PALIMPSEST / original companion builder')
        self.page_number = 0
        self.layout = []
        self.overlays = []
        self.status = art_status

    def page(self, label):
        if self.page_number:
            self.c.showPage()
        self.page_number += 1
        self.c.setFillColor(HexColor(PAPER))
        self.c.rect(0, 0, WIDTH, HEIGHT, fill=1, stroke=0)
        self.c.setStrokeColor(HexColor(LINE))
        self.c.setLineWidth(.55)
        self.c.line(MARGIN, 47, WIDTH - MARGIN, 47)
        self.line('A RIVER TWICE', MARGIN, 32, 8, color=MUTED, track=False)
        right = f'{self.page_number:02d} / {PAGE_COUNT:02d}'
        self.c.setFont('Sans', 8)
        self.c.drawRightString(WIDTH - MARGIN, 32, right)
        self.line(label.upper(), MARGIN, 799, 8.5, color=MUTED)
        if self.status == 'draft':
            self.c.setFillColor(HexColor(MUTED))
            self.c.setFont('Sans', 7.5)
            self.c.drawRightString(WIDTH - MARGIN, 799, 'ILLUSTRATED DRAFT')

    def record(self, kind, x, top, width, height, text=''):
        if x < MARGIN - 1 or x + width > WIDTH - MARGIN + 1 or top > HEIGHT - 25 or top - height < 54:
            raise ValueError(f'Page {self.page_number}: content outside the readable area: {text[:60]}')
        self.layout.append({'page': self.page_number, 'kind': kind, 'rect': [x, top - height, width, height], 'text': text})

    def line(self, text, x, baseline, size=11, font='Sans', color=INK, track=True):
        width = pdfmetrics.stringWidth(text, font, size)
        self.c.setFillColor(HexColor(color))
        self.c.setFont(font, size)
        self.c.drawString(x, baseline, text)
        if track:
            self.record('line', x, baseline + size * .86, width, size * 1.12, text)

    def paragraph(self, text, x, top, width, size=11.1, leading=16.1, font='Sans', color=INK):
        style = ParagraphStyle('body', fontName=font, fontSize=size, leading=leading,
                               textColor=HexColor(color), spaceAfter=0, allowWidows=0, allowOrphans=0)
        block = Paragraph(text, style)
        _, height = block.wrap(width, HEIGHT)
        block.drawOn(self.c, x, top - height)
        self.record('paragraph', x, top, width, height, text)
        return top - height

    def heading(self, text, top=758, size=30):
        self.line(text, MARGIN, top, size, 'Serif')

    def rule(self, y):
        self.c.setStrokeColor(HexColor(LINE))
        self.c.setLineWidth(.6)
        self.c.line(MARGIN, y, WIDTH - MARGIN, y)

    def image(self, path, x, top, width, height):
        with Image.open(path) as source:
            aspect = source.width / source.height
        desired = width / height
        self.c.saveState()
        clip = self.c.beginPath()
        clip.rect(x, top - height, width, height)
        self.c.clipPath(clip, stroke=0, fill=0)
        if aspect > desired:
            image_height, image_width = height, height * aspect
        else:
            image_width, image_height = width, width / aspect
        self.c.drawImage(str(path), x + (width - image_width) / 2,
                         top - height + (height - image_height) / 2,
                         width=image_width, height=image_height)
        self.c.restoreState()
        self.record('artwork', x, top, width, height)

    def figure(self, filename, x, top, width, height):
        self.overlays.append({'page': self.page_number - 1, 'path': self.output / 'figures' / filename,
                              'rect': [x, HEIGHT - top, x + width, HEIGHT - top + height]})
        self.record('scientific figure', x, top, width, height)

    def finish(self):
        if self.page_number != PAGE_COUNT:
            raise ValueError(f'The companion must contain {PAGE_COUNT} pages')
        self.c.save()
        pdf = fitz.open(self.raw_path)
        for overlay in self.overlays:
            with fitz.open(overlay['path']) as figure:
                pdf[overlay['page']].show_pdf_page(fitz.Rect(overlay['rect']), figure, 0, overlay=True)
        final = self.output / 'a-river-twice-companion.pdf'
        pdf.save(final, garbage=4, deflate=True)
        pdf.close()
        self.raw_path.unlink()
        return final


def prepare_plate(source, output, name):
    source = Path(source)
    target = output / 'assets' / f'{name}.jpg'
    target.parent.mkdir(exist_ok=True)
    with Image.open(source) as image:
        original_size = image.size
        image = image.convert('RGB')
        image.thumbnail((2100, 2100), Image.Resampling.LANCZOS)
        image.save(target, quality=92, subsampling=0, optimize=True)
    return target, {'name': source.name, 'source_sha256': digest(source), 'source_pixels': original_size,
                    'embedded_file': str(target.relative_to(output)), 'embedded_sha256': digest(target)}


def receipt_summary(path):
    if path is None:
        return None
    source = Path(path)
    data = json.loads(source.read_text())
    if not isinstance(data, dict):
        raise ValueError('A production receipt must be a JSON object')
    # A supplied receipt is identified, not interpreted as a listening verdict.
    # Arbitrary input paths, environment strings and private metadata are not copied.
    allowed = ('format', 'version', 'all_passed', 'duration_seconds', 'fps', 'frames',
               'frame_count', 'width', 'height', 'sample_rate', 'channels')
    fields = {key: data[key] for key in allowed if key in data
              and isinstance(data[key], (int, float, bool)) and not isinstance(data[key], str)}
    return {'name': source.name, 'sha256': digest(source), 'selected_numeric_fields': fields,
            'claim': 'Receipt supplied; no perceptual conclusion inferred.'}


def opening(book, wide):
    book.page('PALIMPSEST / an illustrated companion')
    book.heading('A River Twice', top=735, size=50)
    book.paragraph('What does it mean to recognize something<br/>when its relationships have changed?',
                   MARGIN, 692, CONTENT, 16, 22, 'Serif')
    book.image(wide, MARGIN, 605, CONTENT, 283)
    caption = 'Visual development plate. Final film images are supplied separately.' if book.status == 'draft' else 'From the film’s authored, phase-driven geometry.'
    book.paragraph(caption, MARGIN, 308, CONTENT, 8.6, 12, color=MUTED)
    book.paragraph('A part can return.<br/>The whole can remain different.',
                   MARGIN, 264, CONTENT, 26, 31, 'Serif')
    book.rule(187)
    for question, pages, x, top, width in (
        ('Which relationships can we see?', 'Pages 2 and 5', MARGIN, 172, 231),
        ('How much difference can we resolve?', 'Pages 3–4', 310, 172, 239),
        ('What can one snapshot tell us?', 'Page 7', MARGIN, 128, 231),
        ('What changes when the clock is not alone?', 'Page 8', 310, 128, 239),
    ):
        book.paragraph(f'<b>{question}</b><br/><font size="8.8" color="{MUTED}">{pages}</font>',
                       x, top, width, 10, 14)
    book.paragraph('Original composition, code and visual interpretation by Codex.<br/>'
                   'An artwork and four finite studies of what a clock can reveal.',
                   MARGIN, 84, CONTENT, 8.7, 13, color=MUTED)


def returning_fragment(book, data):
    book.page('01 / The part and the whole')
    book.heading('The fragment looks familiar.')
    book.paragraph('The observer first sees two separate relationships. They return exactly. '
                   'A relationship between those pairs remains changed.', MARGIN, 718, CONTENT, 12, 17.5)
    book.figure('01-return-and-relation.pdf', MARGIN, 659, CONTENT, 204)
    book.paragraph('Arrows show phases relative to mode 0. Teal lines are the two initially observed pairs; '
                   'the amber bridge is the additional relationship. This is a mathematical diagram, not a photograph.',
                   MARGIN, 444, CONTENT, 8.8, 12.6, color=MUTED)
    book.line('0', MARGIN, 362, 33, 'Serif', TEAL)
    book.line(f"{data['return']['full_distance']:.3f}", 309, 362, 33, 'Serif', AMBER)
    book.paragraph('Returning observed difference<br/><b>R = 0 analytically</b>', MARGIN, 342, 222, 10.5, 15)
    book.paragraph('Distance of the complete state<br/><b>D = 0.963902532850</b>', 309, 342, 240, 10.5, 15)
    book.rule(292)
    book.paragraph('Four amplitudes evolve with energies 0, 1, √2, 1 + √2 and equal populations. '
                   'At t = 2π, the observer reading only pairs (0,1) and (2,3) cannot distinguish the beginning. '
                   'Reading pair (1,2) exposes a difference already present in the same state.',
                   MARGIN, 273, CONTENT, 11, 16.2)
    book.paragraph('D is the pure-state trace distance: zero means the same state; one means orthogonal. '
                   'For the 32-mode version, the corresponding full distance is 0.991222. '
                   'Nothing in either unitary calculation has been erased.', MARGIN, 179, CONTENT, 11, 16.2)
    book.paragraph('These readouts are computed ensemble expectations. They do not represent disturbance-free '
                   'monitoring of one unknown quantum object. The graph chooses what is read; it does not change '
                   'the Hamiltonian.', MARGIN, 101, CONTENT, 9.2, 13.5, color=MUTED)


def local_clock(book, data):
    book.page('02 / Distinguishing nearby moments')
    book.heading('Nearness has a speed.')
    book.paragraph('A useful clock changes as time passes. Here its reading is a vector of complex '
                   'relationships, with both real and imaginary parts. Their magnitudes alone would show no change.',
                   MARGIN, 718, CONTENT, 11.7, 17)
    book.figure('02-local-separation.pdf', MARGIN, 646, CONTENT, 202)
    book.paragraph('Saved dense-operator samples, joined for readability. Equal total edge emphasis is an '
                   'algebraic control, not equal measurement cost. Each candidate readout has chosen error radius η = 0.01.',
                   MARGIN, 431, CONTENT, 8.8, 12.6, color=MUTED)
    book.line(f"{data['local_thresholds']['matched']:.5f}", MARGIN, 352, 29, 'Serif', TEAL)
    book.line(f"{data['local_thresholds']['connected']:.5f}", 309, 352, 29, 'Serif', AMBER)
    book.paragraph('Separate pairs, more emphasis<br/>finer local separation', MARGIN, 332, 230, 10.4, 15)
    book.paragraph('Connected pairs<br/>coarser locally, a relation recovered', 309, 332, 240, 10.4, 15)
    book.rule(285)
    book.paragraph('The squared readout distance has an exact local coefficient:', MARGIN, 266, CONTENT, 11, 16)
    book.line('R(δ) = C δ² + O(δ⁴)', MARGIN, 226, 17, 'Sans')
    book.line('C = Σ aⱼₖ pⱼ pₖ (Eⱼ - Eₖ)²', MARGIN, 195, 14, 'Sans')
    book.paragraph('For every pair with unit emphasis, C = Var(E). For this known pure unitary family, '
                   'the quantum Fisher information for time is F<sub>Q</sub> = 4 Var(E), with ℏ = 1. [4,5]',
                   MARGIN, 167, CONTENT, 10.6, 15.7)
    book.paragraph('Quantum Fisher information describes optimized local statistical sensitivity. It is not '
                   'the selected graph’s classical measurement Fisher information and does not identify a distant cycle.',
                   MARGIN, 99, CONTENT, 9.2, 13.5, color=MUTED)


def distant_clock(book, data):
    book.page('03 / A distant moment can look the same')
    book.heading('Precision does not count cycles.')
    book.paragraph('The locally sharper disconnected observer still repeats every 2π. The connected '
                   'observer rejects that first alias, then admits later near returns under finite readout uncertainty.',
                   MARGIN, 718, CONTENT, 11.7, 17)
    book.figure('03-distant-ambiguity.pdf', MARGIN, 647, CONTENT, 218)
    book.paragraph('The closest candidate so far, from the declared grid δ = 2πn, n = 1 through 4096. '
                   'This is a finite stroboscopic search, not a claim about the first ambiguity in continuous time.',
                   MARGIN, 416, CONTENT, 8.8, 12.6, color=MUTED)
    book.line('A report that fits both times', MARGIN, 344, 14, 'Serif', AMBER)
    book.line('A finite negative result', 310, 344, 14, 'Serif', TEAL)
    witness = data['ambiguity']['cycle_29_midpoint']
    book.paragraph(f'At four-mode cycle 29, the connected readings differ by {witness["separation"]:.8f}. '
                   f'Their actual midpoint is {witness["endpoint_errors"][0]:.8f} from each. Both errors are below '
                   'η = 0.01, so that same report is compatible with either time.',
                   MARGIN, 324, 231, 10.6, 15.7)
    book.paragraph('The 32-mode connected observer first admits a candidate at cycle 623. The complete observer '
                   f'admits none on this grid even at η = 0.05. Its closest distance is '
                   f'{data["ambiguity"]["complete_32_minimum"]:.8f}. Later or unsampled aliases are not excluded.',
                   310, 324, 239, 10.6, 15.7)
    book.rule(171)
    book.paragraph('<b>Why the factor two?</b> Two radius-η error balls share a possible readout exactly when '
                   'their centers are at most 2η apart. A midpoint proves overlap; the triangle inequality '
                   'rules it out when the distance exceeds 2η.', MARGIN, 154, CONTENT, 10.1, 14.6)
    book.paragraph('Exact control: the periodic spectrum (0,1,2,3) has larger F<sub>Q</sub> = 5, yet the whole '
                   'state returns every 2π. Local sharpness alone cannot label the cycle. [1]',
                   MARGIN, 87, CONTENT, 9, 13, color=MUTED)


def certificate(book):
    book.page('04 / The mathematical guarantee')
    book.heading('A return needs enough relations.')
    book.paragraph('A connected observation graph supplies a bound. A disconnected one can hide a '
                   'different common phase in each component. Weak connections can make the bound loose.',
                   MARGIN, 718, CONTENT, 11.6, 17)
    book.c.setFillColor(HexColor('#E5E9DF'))
    book.c.rect(MARGIN, 363, CONTENT, 286, fill=1, stroke=0)
    x, w = MARGIN + 17, CONTENT - 34
    book.paragraph('<b>A compact proof for the declared pure-state family</b>', x, 632, w, 11.1, 16)
    book.paragraph('Let z<sub>j</sub> = exp(-iE<sub>j</sub>t), P = diag(p), and give the graph Laplacian L '
                   'weights a<sub>jk</sub>p<sub>j</sub>p<sub>k</sub>. Populations are positive, fixed and sum to one. '
                   'Let λ be the first positive eigenvalue of P<super>-1/2</super> L P<super>-1/2</super>.',
                   x, 602, w, 10.2, 15.2)
    book.paragraph('Set μ = Σ p<sub>j</sub>z<sub>j</sub>, u = z - μ1, and x = P<super>1/2</super>u. '
                   'Then x is orthogonal to √p, the null eigenvector.', x, 530, w, 10.2, 15.2)
    book.line('D² = Σ pⱼ |uⱼ|² = x†x', x, 472, 14, 'Sans')
    book.line('R = u†Lu = x†(P⁻¹/² L P⁻¹/²)x ≥ λD²', x, 441, 13, 'Sans')
    book.paragraph('The Rayleigh quotient gives <b>D² ≤ R/λ</b>. This is an application of established '
                   'weighted graph spectral geometry. The proof applies beyond the sampled times, under '
                   'the stated assumptions. [2,3]', x, 415, w, 10, 14.8)
    book.paragraph('With all unordered pairs counted once and unit emphasis, <b>R = D² exactly</b>. '
                   'The graph reads relationships; its edges are not dynamical couplings.',
                   MARGIN, 341, CONTENT, 10.8, 16)
    book.line('With readout error, name the bound.', MARGIN, 277, 18, 'Serif')
    book.paragraph('D ≤ min(1, (√R<sub>obs</sub> + ε) / √λ)', MARGIN, 254, CONTENT, 15, 22)
    book.paragraph('Here ε bounds error in the measured <b>change vector</b>. On the preceding page, η bounds '
                   'each candidate’s <b>absolute readout</b>. If two endpoint estimates each have error at most η, '
                   'their difference has error at most 2η. These conventions must not be interchanged.',
                   MARGIN, 214, CONTENT, 10.7, 15.7)
    book.paragraph('These are deterministic weighted-norm bounds, not shot-noise or equal-resource claims. '
                   'A small λ can make the certificate merely D ≤ 1. No mixed-state reconstruction or '
                   'measurement-backaction model is asserted.', MARGIN, 117, CONTENT, 9.5, 14, color=MUTED)


def interpretation(book, macro, receipt_count, comparison=None):
    book.page('05 / An authored interpretation')
    book.heading('The familiar, carried elsewhere.', size=29)
    book.paragraph('The equations supply a tension. Form, light, camera, harmony and silence make it an artwork.',
                   MARGIN, 718, CONTENT, 12, 17.5)
    if comparison:
        half = (CONTENT - 12) / 2
        book.line('INITIAL VIEW', MARGIN, 661, 8.5, color=MUTED)
        book.line('RETURNING VIEW', MARGIN + half + 12, 661, 8.5, color=MUTED)
        book.image(comparison[0], MARGIN, 646, half, half * 9 / 16)
        book.image(comparison[1], MARGIN + half + 12, 646, half, half * 9 / 16)
        book.paragraph('The reference fragment under matched camera and light. Controlled renders '
                       'of the film’s geometry, with the same framing in both views.',
                       MARGIN, 493, CONTENT, 8.6, 12, color=MUTED)
        book.paragraph('We can recognize what returns before we know what has changed around it.',
                       MARGIN, 449, CONTENT, 15, 21, 'Serif')
    else:
        book.image(macro, MARGIN, 665, CONTENT, 225)
        label = 'Visual development detail; not an image of physical quantum matter.' if book.status == 'draft' else 'Detail from the supplied authored artwork; not physical quantum matter.'
        book.paragraph(label, MARGIN, 427, CONTENT, 8.6, 12, color=MUTED)
    book.line('D   F   E   A   D', MARGIN, 369, 25, 'Serif', AMBER)
    book.line('One authored call, changing carriers.', 279, 375, 10.4, 'Sans', MUTED)
    book.rule(345)
    book.line('The geometric contract', MARGIN, 320, 15, 'Serif')
    book.line('The separate musical score', 310, 320, 15, 'Serif')
    book.paragraph('Both phase quadratures shape the woven form. A local reference family is isolated '
                   'at film times 0, 104 and 208 seconds; cross-family relations shape the surroundings. '
                   'The full phase state continues through the authored blackout at 119.6-122.2 seconds.',
                   MARGIN, 297, 231, 10.6, 15.7)
    book.paragraph('The 240-second score develops the call in new harmony, register and voices. The felt '
                   'source is withdrawn at 118 seconds. Its absence and the scored silence are compositional '
                   'choices. They do not erase the unitary scientific state.',
                   310, 297, 239, 10.6, 15.7)
    book.paragraph('These are authored mappings and score contracts. Recognition, time, absence and return '
                   'are interpretive invitations, not results about human memory or emotional response.',
                   MARGIN, 145, CONTENT, 10.4, 15.4)
    status = (f'{receipt_count} production records identify the supplied picture and score by hash. '
              'They document the making of the work.' if receipt_count else
              'Final production receipts have not been supplied to this draft. '
              'No finished-film or listening verdict is inferred.')
    book.paragraph(status,
                   MARGIN, 82, CONTENT, 8.7, 12.4, color=MUTED)


def operational_clock(book, data):
    book.page('06 / Two moments, one specimen')
    book.heading('Even the whole can almost return.', size=29)
    book.paragraph('At first, the missing relationships hold the clue. Much later, a near return '
                   'leaves little information even when every quantum measurement is allowed.',
                   MARGIN, 718, CONTENT, 11.7, 17)
    book.c.setFillColor(HexColor('#E5E9DF'))
    book.c.rect(MARGIN, 584, CONTENT, 72, fill=1, stroke=0)
    book.paragraph('<b>The task beside these numbers:</b> one quantum register is prepared at '
                   't = 0 or t = 2πn with equal probability. Both candidate states are known. '
                   'No external cycle count, correlated time label or retained history is supplied.',
                   MARGIN + 14, 642, CONTENT - 28, 10.3, 15)
    book.figure('04-snapshot-discrimination.pdf', MARGIN, 567, CONTENT, 193)
    book.paragraph('Observations inside the groups may use any block-diagonal measurement. '
                   'Preprocessing must respect the same restriction. The unrestricted optimum is (1 + D)/2. [2]',
                   MARGIN, 360, CONTENT, 9.2, 13.5, color=MUTED)
    book.line('A return certified with integers.', MARGIN, 306, 17, 'Serif')
    certificate = data['discrimination']['certificate']
    book.paragraph(f'Q = 128. Indices <b>{certificate["k"]}</b> and <b>{certificate["l"]}</b> share '
                   f'the exact box <b>({", ".join(str(x) for x in certificate["box_k"])})</b>. Their difference '
                   f'is the constructed cycle <b>{certificate["n"]}</b>. The integer phase witness is '
                   f'<b>({", ".join(str(x) for x in certificate["m"])})</b>.',
                   MARGIN, 285, CONTENT, 10.5, 15.3)
    book.line('D ≤ π√3 / 128 < 0.05', MARGIN, 220, 17, 'Sans', TEAL)
    book.paragraph('Integer square-root enclosures certify the shared box and the bound. '
                   f'The independent 80-digit value is <b>D = {float(data["discrimination"]["high_precision_D"]):.9f}</b>. '
                   'This witness is beyond the earlier 4096-cycle grid; no earliest return is established. [6]',
                   MARGIN, 196, CONTENT, 10.2, 15)
    book.paragraph('Saved record: operational-time-001/run-002; report and hashes included. Full proof: '
                   'OPERATIONAL-TIME-RESULTS.md. This single-copy task is separate from the ensemble '
                   'error balls on page 4. More independent copies or an external history can add information.',
                   MARGIN, 116, CONTENT, 9.2, 13.5, color=MUTED)


def environment_clock(book):
    book.page('07 / A separate isolation test')
    book.heading('A return depends on its context.', size=29)
    book.paragraph('The near return on the previous page assumed isolation. Give the clock one extra '
                   'degree of freedom and a weak phase interaction: its fragments still return, '
                   'but its full state need not.', MARGIN, 718, CONTENT, 11.5, 16.8)
    book.line('32 clock levels × 2 environment levels   /   χ = 1/10000   /   cycle 4109',
              MARGIN, 647, 9, color=MUTED)
    book.figure('05-isolation-and-return.pdf', MARGIN, 629, CONTENT, 225)
    book.paragraph('D<sub>S</sub> compares the complete clock with its initial state; 0 means a return. '
                   'The shaded rows have exactly the same clock density matrix, despite different joint states.',
                   MARGIN, 391, CONTENT, 9.2, 13.5, color=MUTED)
    book.rule(346)
    book.paragraph('<b>The same clock state is not the same relationship.</b> The coherent environment '
                   'is entangled with the clock. The maximally mixed environment gives an explicitly '
                   'separable joint state, yet the identical clock marginal. Clock observations alone '
                   'cannot tell those mechanisms apart. [7,8]', MARGIN, 328, CONTENT, 10.9, 16)
    book.paragraph('<b>Entanglement is not required.</b> The eigenstate environment remains a product '
                   'state and changes the return even more. A weak coefficient can accumulate a large '
                   'phase over a long interval. This is a changed-Hamiltonian comparison.',
                   MARGIN, 246, CONTENT, 10.9, 16)
    book.paragraph('Returning purity is also insufficient: at cycle 2500 the primary clock is pure '
                   'again, while its environment is orthogonal to its beginning. At cycle 5000 the '
                   'interaction is exactly undone, but the clock still has D<sub>S</sub> = 0.753341. '
                   'Neither event is a joint return.', MARGIN, 179, CONTENT, 9.6, 14)
    book.paragraph('This finite unitary extension was not used to generate the film. No irreversible '
                   'loss or thermal bath is inferred. All 18 cases also passed a separate 80-digit '
                   'operator calculation. Full record and scope: CLOCK-ENVIRONMENT-RESULTS.md.',
                   MARGIN, 104, CONTENT, 8.9, 13.2, color=MUTED)


def closing(book, clock_report, time_report, operational_report, environment_report):
    book.page('08 / Limits, evidence and sources')
    book.heading('What the work does establish.')
    book.paragraph('A finite comparison of returning observations, distinguishable snapshots and '
                   'the assumption of isolation. Independent operators and exact integer '
                   'certificates check the four declared studies.',
                   MARGIN, 716, CONTENT, 11.7, 17)
    check_count = sum(len(report['checks']) for report in (clock_report, time_report, operational_report, environment_report))
    for x, value, label in [(MARGIN, str(check_count), 'protocol checks passed'),
                            (224, '49', 'focused Python tests'), (406, '4', 'admitted studies')]:
        book.line(value, x, 628, 31, 'Serif', TEAL)
        book.line(label, x, 607, 8.2, 'Sans', MUTED)
    book.rule(588)
    book.paragraph('<b>Boundaries.</b> Snapshot probabilities assume known preparations, equal priors '
                   'and one copy without an external time record. Ensemble error norms are separate. '
                   'The original graph bound applies to its fixed pure family; the environment extension '
                   'uses density-matrix distances. No general mixed-state tomography, backaction-free '
                   'monitoring or irreversible arrow is claimed. Exact joint return also returns every '
                   'included record. [2] An earliest return is not established.',
                   MARGIN, 570, CONTENT, 10.2, 15)
    book.line('Reproduce the evidence', MARGIN, 461, 14, 'Serif')
    book.paragraph('Restore or generate prerequisite records at their canonical paths first. '
                   'Then give the new study a fresh output. Follow RIVER-REPRODUCTION.md.',
                   MARGIN, 448, CONTENT, 9.3, 13.8)
    book.line('python -m studio.<study> --output <new-record>', MARGIN, 407, 8.4, 'Mono')
    book.paragraph('Studies: relational_clock · time_ambiguity · operational_time · clock_environment',
                   MARGIN, 390, CONTENT, 8.3, 12)
    book.line('python -m studio.river_notebook --help', MARGIN, 366, 8.4, 'Mono')
    book.line('Primary sources', MARGIN, 334, 14, 'Serif')
    references = [
        ('1', 'Bocchieri &amp; Loinger (1957). <i>Quantum Recurrence Theorem.</i>', 'doi.org/10.1103/PhysRev.107.337', 'https://doi.org/10.1103/PhysRev.107.337'),
        ('2', 'Watrous (2018). <i>The Theory of Quantum Information.</i> Chapters 1, 3.', 'cs.uwaterloo.ca/~watrous/TQI/', 'https://cs.uwaterloo.ca/~watrous/TQI/'),
        ('3', 'Singer (2011). <i>Angular Synchronization by Eigenvectors and Semidefinite Programming.</i>', 'arxiv.org/abs/0905.3174', 'https://arxiv.org/abs/0905.3174'),
        ('4', 'Braunstein &amp; Caves (1994). <i>Statistical distance and the geometry of quantum states.</i>', 'doi.org/10.1103/PhysRevLett.72.3439', 'https://doi.org/10.1103/PhysRevLett.72.3439'),
        ('5', 'Pang &amp; Brun (2014). <i>Quantum metrology for a general Hamiltonian parameter.</i> Eqs. 9-10.', 'arxiv.org/html/1407.6091', 'https://arxiv.org/html/1407.6091'),
        ('6', 'Gupta &amp; Short (2026). <i>Recurrence Time for Finite Quantum Systems.</i> Section III.', 'arxiv.org/html/2604.14995', 'https://arxiv.org/html/2604.14995'),
        ('7', 'Cucchietti, Paz &amp; Zurek (2005). <i>Decoherence from Spin Environments.</i> Eqs. 1, 4-8.', 'arxiv.org/abs/quant-ph/0508184', 'https://arxiv.org/abs/quant-ph/0508184'),
        ('8', 'Vidal &amp; Werner (2002). <i>A computable measure of entanglement.</i> Eq. 4, Proposition 8.', 'arxiv.org/abs/quant-ph/0102117', 'https://arxiv.org/abs/quant-ph/0102117'),
    ]
    tops = [316, 316]
    for index, (number, title, label, url) in enumerate(references):
        column = index // 4
        x = MARGIN if column == 0 else 310
        text = f'[{number}] {title}<br/><a href="{url}" color="{TEAL}">{label}</a>'
        tops[column] = book.paragraph(text, x, tops[column], 239, 8.1, 10.8) - 8
    book.paragraph('The package retains source, input hashes, figure data, SVG/PDF figures and page proofs. '
                   'Four study records retain arrays, finite negative results and exact controls. '
                   'Independent review receipts accompany the environment extension; the first operational '
                   'reporting failure is retained separately. Test counts sum recorded focused runs.',
                   MARGIN, 116, CONTENT, 8.5, 12.3, color=MUTED)


def visual_proofs(path, output):
    folder = output / 'proof'
    folder.mkdir()
    document = fitz.open(path)
    inventory = []
    columns = 3
    rows = (len(document) + columns - 1) // columns
    contact = Image.new('RGB', (columns * 248 + 8, rows * 360 + 10), '#D9DDD3')
    for index, page in enumerate(document):
        raster = page.get_pixmap(matrix=fitz.Matrix(1.55, 1.55), alpha=False)
        image = Image.frombytes('RGB', (raster.width, raster.height), raster.samples)
        image.save(folder / f'page-{index + 1:02d}.jpg', quality=91, optimize=True)
        thumbnail = image.copy()
        thumbnail.thumbnail((235, 332), Image.Resampling.LANCZOS)
        x, y = 12 + (index % columns) * 248, 15 + (index // columns) * 360
        contact.paste(thumbnail, (x, y))
        ImageDraw.Draw(contact).text((x, y + 339), f'{index + 1:02d}', fill=INK)
        text = page.get_text()
        if not text.strip() or '\ufffd' in text or '\x00' in text:
            raise ValueError(f'Invalid text extraction on page {index + 1}')
        escaped = [b for b in page.get_text('blocks') if b[0] < -1 or b[1] < -1
                   or b[2] > WIDTH + 1 or b[3] > HEIGHT + 1]
        if escaped:
            raise ValueError(f'Text extends beyond page {index + 1}')
        inventory.append({'page': index + 1, 'extracted_characters': len(text),
                          'links': len(page.get_links()), 'text_inside_page': True})
    contact.save(folder / 'contact.jpg', quality=88, optimize=True)
    (folder / 'text.txt').write_text('\n\n'.join(page.get_text() for page in document))
    document.close()
    return inventory


def main(args):
    began = time.monotonic()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    if args.artwork_status == 'final' and args.visual_receipt is None:
        raise ValueError('Final artwork status needs its supplied visual receipt')
    if bool(args.return_before) != bool(args.return_after):
        raise ValueError('A return comparison needs both supplied images')
    font_receipt = fonts()
    font_license_receipt = copy_font_licenses(output)
    for name in SOURCES:
        source = Path(name)
        target = output / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    summary, clock_report, time_report, operational_report, environment_report = make_figures(
        output / 'figures', args.clock_study, args.time_study, args.operational_study, args.environment_study)
    review_path = Path(args.environment_review)
    environment_review = json.loads(review_path.read_text())
    if not (environment_review['all_passed'] and len(environment_review['comparisons']) == 18
            and all(row['passed'] for row in environment_review['comparisons'])
            and environment_review['study_report_sha256'] == digest(Path(args.environment_study) / 'report.json')
            and environment_review['review_source_sha256'] == digest('studio/verify_clock_environment.py')):
        raise ValueError('Environment review does not certify the supplied study and verifier source')
    receipts = {name: receipt_summary(getattr(args, name + '_receipt')) for name in ('visual', 'film', 'audio')}
    wide, wide_receipt = prepare_plate(args.wide, output, 'wide')
    macro, macro_receipt = prepare_plate(args.macro, output, 'detail')
    comparison, comparison_receipts = None, []
    if args.return_before:
        with Image.open(args.return_before) as before, Image.open(args.return_after) as after:
            if before.size != after.size or before.width * 9 != before.height * 16:
                raise ValueError('The controlled return pair needs equally sized 16:9 images; no comparison crop is applied')
        initial, initial_receipt = prepare_plate(args.return_before, output, 'return-before')
        returning, returning_receipt = prepare_plate(args.return_after, output, 'return-after')
        comparison = (initial, returning)
        comparison_receipts = [initial_receipt, returning_receipt]
    for name, path in [('clock', args.clock_study), ('time-ambiguity', args.time_study),
                       ('operational-time', args.operational_study), ('clock-environment', args.environment_study)]:
        target = output / 'evidence' / name
        target.mkdir(parents=True)
        for filename in ('manifest.json', 'report.json'):
            shutil.copy2(Path(path) / filename, target / filename)
    shutil.copy2(review_path, output / 'evidence' / 'clock-environment-independent-review.json')
    book = Book(output, args.artwork_status)
    opening(book, wide)
    returning_fragment(book, summary)
    local_clock(book, summary)
    distant_clock(book, summary)
    certificate(book)
    interpretation(book, macro, sum(value is not None for value in receipts.values()), comparison)
    operational_clock(book, summary)
    environment_clock(book)
    closing(book, clock_report, time_report, operational_report, environment_report)
    pdf = book.finish()
    inventory = visual_proofs(pdf, output)
    report = {'format': 'palimpsest-river-companion', 'version': 1,
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'artwork_status': args.artwork_status, 'pages': PAGE_COUNT,
              'pdf_sha256': digest(pdf), 'artwork_inputs': [wide_receipt, macro_receipt] + comparison_receipts,
              'production_receipts': receipts, 'fonts': font_receipt,
              'font_licenses': font_license_receipt,
              'source_sha256': {name: digest(output / 'source' / name) for name in SOURCES},
              'study_record_sha256': summary['source_studies'],
              'environment_review_sha256': digest(review_path),
              'scientific_evidence': {
                  'admission_checks': sum(len(r['checks']) for r in (clock_report, time_report, operational_report, environment_report)),
                  'focused_tests_previously_recorded': 49,
                  'environment_independent_comparisons': 18,
                  'environment_calculation_wall_seconds': environment_report['calculation_wall_seconds'],
                  'environment_calculation_cpu_seconds': environment_report['calculation_cpu_seconds'],
                  'environment_peak_process_bytes': environment_report['peak_process_bytes'],
                  'environment_independent_review_seconds': environment_review['wall_seconds'],
              },
              'page_inventory': inventory, 'layout': book.layout,
              'render_seconds': time.monotonic() - began,
              'scope': 'Nine-page authored companion. Scientific figures use four admitted saved records. '
                       'Artwork status is explicit; no listening or human-perception result inferred.',
              'visual_inspection': 'Rendered page proofs prepared; human or agent visual review recorded separately.'}
    (output / 'receipt.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    manifest = {'format': 'palimpsest-river-companion-files', 'version': 1,
                'files': [{'path': str(path.relative_to(output)), 'bytes': path.stat().st_size, 'sha256': digest(path)}
                          for path in sorted(output.rglob('*')) if path.is_file()]}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'pdf_bytes': pdf.stat().st_size, 'pages': PAGE_COUNT,
                      'record_bytes': sum(path.stat().st_size for path in output.rglob('*') if path.is_file()),
                      'render_seconds': report['render_seconds'], 'pdf_sha256': report['pdf_sha256']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='artwork/river-notebook-001/draft-005')
    parser.add_argument('--wide', required=True, help='Supplied artwork plate; never guessed from a render path')
    parser.add_argument('--macro', required=True, help='Supplied artwork detail')
    parser.add_argument('--return-before', help='Optional supplied initial comparison image; requires --return-after')
    parser.add_argument('--return-after', help='Optional supplied returning comparison image; requires --return-before')
    parser.add_argument('--artwork-status', choices=('draft', 'final'), default='draft')
    parser.add_argument('--visual-receipt')
    parser.add_argument('--film-receipt')
    parser.add_argument('--audio-receipt')
    parser.add_argument('--clock-study', default='artifacts/studies/relational-clock-001')
    parser.add_argument('--time-study', default='artifacts/studies/time-ambiguity-001')
    parser.add_argument('--operational-study', default='artifacts/studies/operational-time-001/run-002')
    parser.add_argument('--environment-study', default='artifacts/studies/clock-environment-001/run-001')
    parser.add_argument('--environment-review', default='artifacts/reviews/clock-environment-001.json')
    with threadpool_limits(limits=2):
        main(parser.parse_args())
