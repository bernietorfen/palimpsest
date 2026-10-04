"""Original figures from the live, pressure and registered-refinement records."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.path import Path as VectorPath
from matplotlib.patches import PathPatch
import numpy as np
from PIL import Image

from studio.preserve import sha256


PAPER, INK, AMBER, MUTED = '#f1eddf', '#293e42', '#ac7137', '#69716b'


def ring(values, radius, amplitude, color):
    angles = np.arange(12) * np.pi / 6
    points = np.column_stack(((radius + amplitude * values) * np.sin(angles),
                              (radius + amplitude * values) * np.cos(angles)))
    vertices, codes = [points[0]], [VectorPath.MOVETO]
    for index in range(12):
        a, b, c, d = (points[(index + offset) % 12] for offset in (-1, 0, 1, 2))
        vertices.extend([b + (c - a) / 6, c - (d - b) / 6, c])
        codes.extend([VectorPath.CURVE4] * 3)
    vertices.append(points[0]); codes.append(VectorPath.CLOSEPOLY)
    return PathPatch(VectorPath(vertices, codes), fill=False, color=color, lw=1.1)


def main(args):
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'text.color': INK,
                         'axes.labelcolor': INK, 'pdf.fonttype': 42, 'savefig.facecolor': PAPER})
    sources = {}
    spatial = Path('artifacts/studies/spatial-study-001')
    report = json.loads((spatial / 'report.json').read_text())
    verified = json.loads(Path('research/spatial-verification-001.json').read_text())
    if sha256(spatial / 'report.json') != verified['study_report_sha256']:
        raise ValueError('The verified spatial record changed')
    fields = {}
    for size in (128, 256, 512):
        path = spatial / f'grid-{size}/rate-192/writing-DEABC.npz'
        with np.load(path) as data:
            fields[size] = data['inscription'].astype(float)
        sources[str(path)] = sha256(path)
    differences = [fields[256][::2, ::2] - fields[128], fields[512][::2, ::2] - fields[256]]
    error_scale = max(float(np.abs(value).max()) for value in differences)
    palette = LinearSegmentedColormap.from_list('palimpsest-inscription', ['#294e59', PAPER, '#a56b31'])

    fig = plt.figure(figsize=(20, 15), facecolor=PAPER)
    fig.text(.048, .957, 'PALIMPSEST / STUDY IV', fontsize=12)
    fig.text(.952, .957, 'CODEX / 2026', fontsize=12, ha='right')
    fig.add_artist(Line2D([.048, .952], [.940, .940], transform=fig.transFigure, color='#aaa994', lw=.6))
    fig.text(.046, .877, 'A mark, at three scales', fontsize=47, fontfamily='DejaVu Serif')
    fig.text(.048, .843, 'D · E · A · B · C / after 24 seconds of writing / timestep 1/192 s / fixed echo placement', fontsize=13, color=MUTED)
    for index, size in enumerate((128, 256, 512)):
        left = .048 + index * .307
        ax = fig.add_axes([left, .465, .288, .345])
        artist = ax.imshow(fields[size], cmap=palette, vmin=-.8, vmax=.8, origin='lower', interpolation='nearest')
        ax.set_axis_off()
        fig.text(left + .014, .451, f'{size} × {size}', fontsize=17, fontfamily='DejaVu Serif')
    cb = fig.colorbar(artist, cax=fig.add_axes([.066, .416, .868, .012]), orientation='horizontal', ticks=[-.8, 0, .8])
    cb.outline.set_visible(False); cb.ax.tick_params(labelsize=10, colors=MUTED, length=2)
    fig.text(.5, .380, 'Rest-shape inscription p / one scale across all three fields', fontsize=12, color=MUTED, ha='center')
    fig.add_artist(Line2D([.048, .952], [.355, .355], transform=fig.transFigure, color='#aaa994', lw=.6))
    for index, difference in enumerate(differences):
        left = .054 + index * .303
        ax = fig.add_axes([left, .066, .256, .277])
        artist = ax.imshow(difference, cmap=palette, vmin=-error_scale, vmax=error_scale,
                           origin='lower', interpolation='nearest')
        ax.set_axis_off()
        fig.text(left + .023, .051, ['256 − 128', '512 − 256'][index], fontsize=15, fontfamily='DejaVu Serif')
    fig.text(.675, .315, 'WHAT CHANGES BETWEEN GRIDS', fontsize=12)
    fig.text(.675, .279,
             'Below: differences at coincident sample sites.\n'
             'Both maps use the same enlarged color scale.\n'
             f'Its limits are ±{error_scale:.6f} in inscription units.\n\n'
             'Above: the complete retained fields,\n'
             'shown in their common original scale.\n\n'
             'All 120 histories retain their nearest own label\n'
             'through every tested spatial comparison.\n'
             'This is a finite check of registered geometry,\n'
             'not a continuum or physical-material proof.',
             fontsize=12, linespacing=1.55, va='top')
    for suffix in ('png', 'pdf'):
        fig.savefig(out / f'a-mark-at-three-scales.{suffix}', dpi=300)
    plt.close(fig)
    with Image.open(out / 'a-mark-at-three-scales.png') as image:
        image.convert('RGB').resize((1200, 900), Image.Resampling.LANCZOS).save(out / 'spatial-review.jpg', quality=84)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), facecolor=PAPER)
    for ax, size in zip(axes, (128, 256, 512)):
        ax.imshow(fields[size], cmap=palette, vmin=-.8, vmax=.8, origin='lower', interpolation='nearest')
        ax.set_axis_off(); ax.set_title(f'{size} × {size}', fontsize=14, color=INK, pad=12)
    fig.subplots_adjust(left=.015, right=.985, bottom=.045, top=.88, wspace=.07)
    fig.savefig(out / 'registered-fields.png', dpi=300); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 5.4), facecolor=PAPER)
    ax.set_facecolor(PAPER)
    errors = []
    for key in ('grid-128-256-rate-192', 'grid-256-512-rate-192'):
        path = spatial / 'comparisons' / (key + '.npz')
        with np.load(path) as data:
            errors.append(data['own_distance_hz'].copy())
        sources[str(path)] = sha256(path)
    for index in range(120):
        ax.plot([0, 1], [errors[0][index], errors[1][index]], color=INK, alpha=.16, lw=.65)
    for position, values in enumerate(errors):
        ax.scatter(np.full(120, position), values, color=[INK, AMBER][position], s=10, zorder=3)
        rms = np.sqrt(np.mean(values * values))
        ax.text(position + .05, rms, f'{rms:.6f} Hz\nRMS over all histories', fontsize=10, va='center', color=INK)
    ax.set_yscale('log'); ax.set_xlim(-.2, 1.85); ax.set_ylim(.0002, .008)
    ax.set_xticks([0, 1], ['128 → 256', '256 → 512'])
    ax.set_ylabel('Same-history pitch difference / Hz RMS', fontsize=11)
    ax.spines[['top', 'right']].set_visible(False)
    ax.spines[['bottom', 'left']].set_color('#aaa994')
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.set_title('120 histories / fixed timestep 1/192 s', fontsize=14, loc='left', pad=17)
    fig.tight_layout(pad=1.5); fig.savefig(out / 'spatial-reading-differences.png', dpi=260); plt.close(fig)

    live_path = Path('artwork/live-edition-002/first-dialogue.svg')
    svg = ET.parse(live_path).getroot()
    live = json.loads(svg.find('{http://www.w3.org/2000/svg}metadata').text)['comparison']
    baseline = np.array([110, 137.5, 146.6666667, 165, 183.3333333, 220, 247.5, 275, 293.3333333, 330, 366.6666667, 440])
    pitches = [np.array([frame['pitch'] for frame in live[key]]) for key in ('previous', 'current')]
    if len(pitches[0]) != live['samples'] or len(pitches[1]) != live['samples']:
        raise ValueError('The live drawing contains incomplete compared replies')
    rms = float(np.sqrt(np.mean((pitches[0] - pitches[1]) ** 2)))
    if abs(rms - live['rms_hz']) > 1e-12:
        raise ValueError('The live drawing metric does not match its actual record')
    cents = [1200 * np.log2(values / baseline) for values in pitches]
    limit = max(float(np.abs(values).max()) for values in cents) * 1.06
    fig, axes = plt.subplots(2, 1, figsize=(8, 5.8), sharex=True, facecolor=PAPER)
    for ax, values, key, title in zip(axes, cents, ('previous', 'current'), ('First question', 'Asked again')):
        ax.set_facecolor(PAPER)
        seconds = np.array([frame['step'] for frame in live[key]]) / 96
        for voice in range(12):
            ax.plot(seconds, values[:, voice], color=AMBER if voice == 2 else ('#365f6c' if voice == 0 else '#8b948b'),
                    alpha=1 if voice in (0, 2) else .6, lw=1.7 if voice in (0, 2) else .7)
        ax.axhline(0, color='#a6a895', lw=.5)
        ax.set_ylim(-limit, limit); ax.set_ylabel('Cents from initial tuning', fontsize=10)
        ax.set_title(title, loc='left', fontsize=14, color=INK)
        ax.spines[['top', 'right']].set_visible(False)
        ax.spines[['left', 'bottom']].set_color('#aaa994'); ax.tick_params(colors=MUTED, labelsize=9)
    axes[-1].set_xlabel('Time within the kept phrase / seconds', fontsize=10)
    fig.tight_layout(pad=1.5); fig.savefig(out / 'live-repeated-question.png', dpi=260); plt.close(fig)
    sources[str(live_path)] = sha256(live_path)

    public = Path('artwork/analysis/pressure-reading-003/public')
    pressure = json.loads((public / 'pressure-study-v1.json').read_text())
    glyphs = np.fromfile(public / pressure['glyph_file'], dtype='<i2').reshape(pressure['glyph_shape']) / 32767
    level = pressure['levels'][2]
    lost = next(index for index, point in enumerate(level['points']) if point[2] == index // 8 and point[3] != index // 8)
    point = level['points'][lost]
    indexes = [level['glyph_offset'] + lost, point[2], point[3]]
    labels = [pressure['histories'][lost // 8], pressure['histories'][point[2]], pressure['histories'][point[3]]]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), facecolor=PAPER)
    for ax, index, label, title in zip(axes, indexes, labels, ('Written answer', 'Nearest reader', 'Allow pressure')):
        ax.set_facecolor(PAPER)
        for voice in range(12):
            angle = voice * np.pi / 6
            ax.plot([.14 * np.sin(angle), .96 * np.sin(angle)], [.14 * np.cos(angle), .96 * np.cos(angle)], color='#c7c2b4', lw=.4)
        for number, values in enumerate(glyphs[index]):
            ax.add_patch(ring(values, .28 + number * .17, .128, ['#69776b', '#436b75', AMBER, INK][number]))
        ax.set_xlim(-1, 1); ax.set_ylim(-1, 1); ax.set_aspect('equal'); ax.set_axis_off()
        ax.set_title(title, fontsize=13, pad=8, color=INK)
        ax.text(0, -1.05, ' · '.join(label), ha='center', fontsize=16, color=INK)
    fig.subplots_adjust(left=.035, right=.965, bottom=.1, top=.9, wspace=.15)
    fig.savefig(out / 'a-lost-reading.png', dpi=300); plt.close(fig)
    for path in public.iterdir():
        sources[str(path)] = sha256(path)
    inventory = [{'path': path.name, 'bytes': path.stat().st_size, 'sha256': sha256(path)}
                 for path in sorted(out.iterdir()) if path.is_file()]
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': sources,
              'spatial_report_sha256': sha256(spatial / 'report.json'), 'spatial_field_history': 'DEABC',
              'spatial_field_rate': 192, 'difference_map_shared_limit': error_scale,
              'live_reply_rms_hz': rms, 'live_reply_samples': live['samples'],
              'lost_case': {'history': labels[0], 'realization': lost % 8 + 1, 'nearest': labels[1],
                            'pressure_corrected': labels[2], 'pressure_factors': level['pressure_factors'][lost]},
              'files': inventory}
    (out / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='artwork/notebook/continuation-001')
    main(parser.parse_args())
