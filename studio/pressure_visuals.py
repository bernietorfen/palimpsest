"""An original print and compact interactive record of imperfect writing."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
import numpy as np
from PIL import Image

from studio.preserve import sha256


PAPER, INK, MUTED, AMBER = '#f1eddf', '#293e42', '#69716b', '#ac7137'


def load_cases(folder):
    pitches, factors = [], []
    for path in sorted(folder.glob('batch-*.npz')):
        with np.load(path) as data:
            pitches.append(data['pitch_hz'])
            factors.append(data['pressure_factors'])
    return np.concatenate(pitches), np.concatenate(factors)


def main(args):
    study, atlas, out = Path(args.study), Path(args.atlas), Path(args.output)
    report = json.loads((study / 'report.json').read_text())
    data = np.load(atlas / 'rate-96' / 'atlas.npz')
    canonical = data['pitch_hz'].astype(float)
    labels = data['labels'].tolist()
    features = canonical.reshape(120, -1)
    center = features.mean(axis=0)
    components = data['projection_components']
    divisor = math.sqrt(features.shape[1])
    positions = (features - center) @ components.T / divisor
    fractions = data['singular_values'] ** 2
    fractions /= fractions.sum()
    out.mkdir(parents=True, exist_ok=False)
    public = out / 'public'
    public.mkdir()
    sample_indexes = np.array([0, 96, 192, 288])
    glyphs = [canonical[:, sample_indexes]]
    levels = []
    truth = np.repeat(np.arange(120), 8)
    for index, severity in enumerate((.01, .03, .10)):
        folder = study / 'rate-96' / f'pressure-{round(severity * 100):02d}'
        pitches, factors = load_cases(folder)
        result = np.load(folder / 'identification.npz')
        if pitches.shape != (960, 336, 12) or not np.array_equal(result['truth'], truth):
            raise ValueError('The display requires all eight new-seed cases for all 120 histories')
        points = (pitches.reshape(960, -1).astype(float) - center) @ components.T / divisor
        summaries = report['summaries']['96']['pressures'][str(severity)]
        levels.append({'percent': round(severity * 100), 'position': points, 'factors': factors,
                       'nearest': result['baseline_predicted'], 'corrected': result['corrected_predicted'],
                       'raw_distance': result['baseline_correct_distance_hz'],
                       'residual': result['correct_residual_hz'],
                       'nearest_correct': summaries['nearest_canonical']['correct'],
                       'corrected_correct': summaries['pressure_corrected']['correct'],
                       'glyph_offset': 120 + index * 960})
        glyphs.append(pitches[:, sample_indexes].astype(float))
    all_positions = np.concatenate([positions] + [level['position'] for level in levels])
    lower, upper = all_positions.min(axis=0), all_positions.max(axis=0)
    padding = (upper - lower) * .09
    extent = [float(lower[0] - padding[0]), float(upper[0] + padding[0]),
              float(lower[1] - padding[1]), float(upper[1] + padding[1])]
    mean = canonical[:, sample_indexes].mean(axis=0)
    deviations = np.concatenate(glyphs) - mean
    limit = float(np.abs(deviations).max())
    encoded = np.rint(deviations / limit * 32767).astype('<i2')
    glyph_file = public / 'pressure-glyphs-v1.bin'
    glyph_file.write_bytes(encoded.tobytes())
    reconstructed = np.frombuffer(glyph_file.read_bytes(), dtype='<i2').reshape(deviations.shape) * limit / 32767
    error = float(np.abs(reconstructed - deviations).max())
    if error > limit / 32767 / 2 + 1e-12:
        raise ValueError('Display glyph quantization exceeded its recorded error bound')
    resolved = np.flatnonzero((levels[2]['nearest'] != truth) & (levels[2]['corrected'] == truth))
    example = int(resolved[0]) if len(resolved) else 0
    payload = {'version': 1, 'title': 'The imperfect hand', 'seed': report['seed'],
               'histories': labels, 'canonical_positions': positions.round(6).tolist(),
               'extent': extent, 'projection_variance': fractions[:2].tolist(),
               'glyph_file': 'pressure-glyphs-v1.bin', 'glyph_shape': list(encoded.shape),
               'glyph_scale_hz': limit, 'glyph_maximum_display_error_hz': error,
               'glyph_times_seconds': [0, 4, 8, 12], 'glyph_encoding': 'little-endian signed int16; value/32767 is normalized deviation',
               'glyph_center': 'Mean pitch of the 120 canonical histories at the same time and voice',
               'example': {'level': 2, 'case': example, 'selection': 'First lexicographic case misread by nearest-reference and correctly read after pressure correction, if present'},
               'refinement': report['refinement'], 'source_report_sha256': sha256(study / 'report.json'), 'levels': []}
    for level in levels:
        points = [[round(float(x), 6), round(float(y), 6), int(level['nearest'][i]), int(level['corrected'][i]),
                   round(float(level['raw_distance'][i]), 7), round(float(level['residual'][i]), 7)]
                  for i, (x, y) in enumerate(level['position'])]
        payload['levels'].append({'percent': level['percent'], 'tested': 960,
                                  'nearest_correct': level['nearest_correct'], 'corrected_correct': level['corrected_correct'],
                                  'glyph_offset': level['glyph_offset'], 'points': points,
                                  'pressure_factors': level['factors'].astype(float).round(6).tolist()})
    (public / 'pressure-study-v1.json').write_text(json.dumps(payload, separators=(',', ':'), allow_nan=False) + '\n')
    web_bytes = sum(path.stat().st_size for path in public.iterdir())
    if web_bytes > 650_000:
        raise ValueError(f'The interactive record exceeds its 650 KB data budget: {web_bytes}')

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'text.color': INK,
                         'axes.labelcolor': INK, 'pdf.fonttype': 42, 'savefig.facecolor': PAPER})
    fig = plt.figure(figsize=(20, 26 + 2 / 3), facecolor=PAPER)
    fig.text(.052, .953, 'PALIMPSEST / STUDY III', fontsize=12, color=INK)
    fig.text(.948, .953, 'CODEX / 2026', fontsize=12, color=INK, ha='right')
    fig.add_artist(Line2D([.052, .948], [.942, .942], transform=fig.transFigure, color='#aaa994', lw=.6))
    fig.text(.049, .899, 'An imperfect hand', fontsize=65, fontfamily='DejaVu Serif', color=INK)
    fig.text(.052, .867, '120 histories. Pressure varies. Two ways of reading what remains.', fontsize=17, color=MUTED)
    for row, (method, title) in enumerate([('nearest', 'I.  The nearest ideal answer'), ('corrected', 'II.  Allow for pressure')]):
        top = .825 - row * .291
        bottom = .604 - row * .291
        fig.text(.052, top, title, fontsize=22, fontfamily='DejaVu Serif', color=INK)
        for column, level in enumerate(levels):
            left = .055 + column * .308
            ax = fig.add_axes([left, bottom, .268, .179])
            ax.set_facecolor(PAPER)
            segments = np.stack([positions[truth], level['position']], axis=1)
            ax.add_collection(LineCollection(segments, colors='#bfbeb0', linewidths=.3, alpha=.5, zorder=1))
            correct = level[method] == truth
            ax.scatter(level['position'][correct, 0], level['position'][correct, 1], s=7, color=INK, alpha=.73, linewidths=0, zorder=3)
            ax.scatter(level['position'][~correct, 0], level['position'][~correct, 1], s=10, color=AMBER, alpha=.88, linewidths=0, zorder=4)
            ax.scatter(positions[:, 0], positions[:, 1], s=16, facecolors=PAPER, edgecolors=INK, linewidths=.55, zorder=5)
            ax.set_xlim(extent[:2]); ax.set_ylim(extent[2:]); ax.set_aspect('equal', adjustable='box')
            ax.spines[['top', 'right']].set_visible(False)
            ax.spines[['left', 'bottom']].set_color('#bab9a7')
            ax.tick_params(colors=MUTED, labelsize=9, length=3)
            ax.set_xlabel('First component / Hz RMS', fontsize=9, color=MUTED)
            if column == 0:
                ax.set_ylabel('Second component / Hz RMS', fontsize=9, color=MUTED)
            fig.text(left, top - .027, f"Up to {level['percent']}% pressure variation", fontsize=14, color=MUTED)
            count = level[f'{method}_correct']
            fig.text(left, bottom - .032, f'{count} / 960', fontsize=28, fontfamily='DejaVu Serif', color=INK)
            fig.text(left + .137, bottom - .028, 'histories identified', fontsize=11, color=MUTED)
    fig.add_artist(Line2D([.052, .948], [.249, .249], transform=fig.transFigure, color='#aaa994', lw=.6))
    fig.text(.052, .225, 'THE SAME MEASURED ANSWERS', fontsize=11, color=INK)
    fig.text(.052, .207,
             'Each dot is one response to the common probe. Eight independent pressure realizations were written\n'
             'for each of the 120 gesture orders. The two rows use exactly the same new-seed records.\n'
             'Dark dots receive their written history label. Ochre dots receive another label. Open circles\n'
             'mark the ideal histories. Fine lines connect a perturbed reply with its own ideal reference.',
             fontsize=12, color=INK, linespacing=1.8, va='top')
    fig.text(.052, .123, 'WHAT THE SECOND READER ALLOWS', fontsize=11, color=INK)
    fig.text(.052, .105,
             'Five controlled pressure derivatives define a local linear response space for each history.\n'
             'The second reader removes that pressure component before comparing residuals. Its directions\n'
             'were built independently of these evaluation cases; its rule receives no true label or pressure severity.',
             fontsize=11.5, color=INK, linespacing=1.8, va='top')
    fig.text(.707, .225, 'READING THIS MAP', fontsize=11, color=INK)
    fig.text(.707, .207,
             f'Two components retain {100 * fractions[:2].sum():.1f}%\nof ideal-trajectory variation.\n'
             'The plotted map loses other differences.\nBoth readers use all 4,032 pitch values.\n\n'
             'Writing pressure varies; timing stays fixed.\nThe material and later probe are unchanged.',
             fontsize=11.5, color=INK, linespacing=1.8, va='top')
    fig.text(.052, .038,
             '128 × 128 authored material / timestep 1/96 s / 24 s writing / reset transients / 14 s common probe / 12 voices × 336 samples',
             fontsize=9, color=MUTED)
    fig.text(.052, .020,
             'A finite numerical identification experiment. These counts do not establish human audibility, physical memory capacity or robustness to other perturbations.',
             fontsize=9, color=MUTED)
    for suffix in ('png', 'pdf'):
        fig.savefig(out / f'the-imperfect-hand.{suffix}', dpi=300, facecolor=PAPER)
    plt.close(fig)
    with Image.open(out / 'the-imperfect-hand.png') as source:
        source.convert('RGB').resize((1050, 1400), Image.Resampling.LANCZOS).save(out / 'the-imperfect-hand-review.jpg', quality=84)
    inventory = [{'name': path.name, 'bytes': path.stat().st_size, 'sha256': sha256(path)}
                 for path in sorted(public.iterdir()) if path.is_file()]
    (public / 'manifest.json').write_text(json.dumps({'files': inventory}, indent=2) + '\n')
    files = [{'path': str(path.relative_to(out)), 'bytes': path.stat().st_size, 'sha256': sha256(path)}
             for path in sorted(out.rglob('*')) if path.is_file()]
    record = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_report_sha256': sha256(study / 'report.json'),
              'atlas_sha256': sha256(atlas / 'rate-96' / 'atlas.npz'), 'web_data_bytes': web_bytes,
              'glyph_maximum_display_error_hz': error, 'glyph_quantization_half_step_hz': limit / 32767 / 2,
              'projection_variance_fraction': float(fractions[:2].sum()), 'files': files}
    (out / 'report.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--study', default='artifacts/studies/pressure-reading-001')
    parser.add_argument('--atlas', default='artifacts/studies/history-atlas-001')
    parser.add_argument('--output', default='artwork/analysis/pressure-reading-001')
    main(parser.parse_args())
