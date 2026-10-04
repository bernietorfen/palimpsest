"""Vector companion figures derived from the retained clock experiments.

Run on the computation host. No dynamics or new experimental sweep is run.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch
import numpy as np


PAPER = '#F3EEE4'
INK = '#203B3D'
TEAL = '#3D777A'
AMBER = '#B26843'
MUTED = '#727B76'
LINE = '#C9CEC4'


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def checked_study(path):
    path = Path(path)
    manifest = json.loads((path / 'manifest.json').read_text())
    entries = manifest['files']
    if isinstance(entries, dict):
        entries = [{'path': name, **entry} for name, entry in entries.items()]
    for entry in entries:
        source = path / entry['path']
        if digest(source) != entry['sha256']:
            raise ValueError(f'Study integrity failure: {source.name}')
    report = json.loads((path / 'report.json').read_text())
    if not report['all_passed'] or not all(row['passed'] for row in report['checks']):
        raise ValueError('An unadmitted scientific record cannot supply these figures')
    arrays = np.load(path / 'record.npz', allow_pickle=False)
    return report, arrays


def write_csv(path, header, rows):
    with Path(path).open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def save_figure(fig, output, name):
    fig.savefig(output / f'{name}.svg', facecolor=PAPER, metadata={'Date': None})
    fig.savefig(output / f'{name}.pdf', facecolor=PAPER,
                metadata={'Title': name, 'Author': 'Codex', 'CreationDate': None})
    plt.close(fig)


def style():
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 12,
        'figure.facecolor': PAPER, 'axes.facecolor': PAPER,
        'text.color': INK, 'axes.labelcolor': INK,
        'xtick.color': MUTED, 'ytick.color': MUTED,
        'axes.edgecolor': LINE, 'axes.spines.top': False,
        'axes.spines.right': False, 'svg.fonttype': 'none',
        'pdf.fonttype': 42, 'axes.titleweight': 'normal',
        'legend.frameon': False,
    })


def phase_figure(output, arrays, report):
    times = arrays['time']
    ids = [int(np.argmin(abs(times - value))) for value in (0., 2 * np.pi)]
    if max(abs(times[ids] - [0., 2 * np.pi])) > 1e-12:
        raise ValueError('The declared reference times are missing from the study')
    states = arrays['four_states'][ids]
    phases = states / states[:, :1]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.55))
    nodes = np.array([[0., 1.], [1.55, 1.], [3.25, 1.], [4.8, 1.]])
    rows = []
    for panel, ax in enumerate(axes):
        ax.set_xlim(-.65, 5.45)
        ax.set_ylim(-.3, 2.2)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.text(-.55, 2.02, ('BEGINNING', 'APPARENT RETURN')[panel],
                fontsize=11, color=MUTED)
        ax.text(-.55, 1.65, ('t = 0', 't = 2π')[panel], fontsize=16)
        for first, second in ((0, 1), (2, 3)):
            ax.plot(nodes[[first, second], 0], nodes[[first, second], 1],
                    color=TEAL, lw=2.5, zorder=1)
        ax.plot(nodes[[1, 2], 0], nodes[[1, 2], 1], color=AMBER,
                ls='--' if panel == 0 else '-', lw=1.4, zorder=1)
        for j, (x, y) in enumerate(nodes):
            ax.add_patch(Circle((x, y), .34, edgecolor=LINE, facecolor=PAPER, lw=1.1, zorder=2))
            direction = phases[panel, j]
            ax.add_patch(FancyArrowPatch((x, y), (x + .28 * direction.real, y + .28 * direction.imag),
                                        arrowstyle='-|>', mutation_scale=11,
                                        lw=1.3, color=TEAL if j < 2 else AMBER, zorder=3))
            ax.text(x, .46, str(j), ha='center', fontsize=12, color=MUTED)
            rows.append([float(times[ids[panel]]), j, float(direction.real), float(direction.imag)])
        ax.text(2.4, -.03, 'two observed pairs' if panel == 0 else 'the bridge reveals a changed relation',
                fontsize=10.5, ha='center', color=TEAL if panel == 0 else AMBER)
    fig.subplots_adjust(left=.03, right=.985, top=.97, bottom=.08, wspace=.18)
    save_figure(fig, output, '01-return-and-relation')
    write_csv(output / '01-return-and-relation.csv', ['time', 'mode', 'phase_relative_to_mode_0_real',
                                                    'phase_relative_to_mode_0_imaginary'], rows)
    return {'reference_time': float(times[ids[1]]),
            'full_distance': report['four_level']['false_return_distance'],
            'restricted_R': report['four_level']['graphs'][0]['observation_discrepancy_at_2pi']}


def local_figure(output, report):
    fig, ax = plt.subplots(figsize=(9.5, 3.55))
    rows = []
    samples = report['dense_matrix_cases']
    observers = report['models']['four']['observers']
    for name, label, color in [('matched', 'Separate pairs / stronger local response', TEAL),
                               ('connected', 'Connected pairs / missing relation added', AMBER)]:
        chosen = [r for r in samples if r['clock'] == 'four' and r['observer'] == name
                  and r['basis'] == 'energy' and r['start'] == 0 and r['delta'] <= .2]
        x = np.array([r['delta'] for r in chosen])
        y = np.sqrt([r['R_dense'] for r in chosen])
        ax.plot(x, y, marker='o', markersize=4, color=color, lw=1.5, label=label)
        for item, distance in zip(chosen, y):
            rows.append([name, item['delta'], item['R_dense'], float(distance), item['C']])
    ax.axhline(.02, lw=1.1, ls=(0, (3, 3)), color=INK)
    ax.text(.199, .023, '2η = 0.02', ha='right', fontsize=11, color=INK)
    ax.set_xlim(0, .2)
    ax.set_ylim(0, .1)
    ax.set_xlabel('Time separation δ / abstract units', labelpad=9)
    ax.set_ylabel('Readout distance √R', labelpad=9)
    ax.set_xticks([0, .05, .1, .15, .2])
    ax.set_yticks([0, .02, .04, .06, .08, .1])
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(axis='y', color=LINE, alpha=.55, lw=.6)
    fig.subplots_adjust(left=.10, bottom=.23, right=.955, top=.97)
    save_figure(fig, output, '02-local-separation')
    write_csv(output / '02-local-separation.csv', ['observer', 'delta', 'R_dense', 'distance', 'C'], rows)
    return {name: next(r['separation'] for r in observers[name]['local_thresholds'] if r['eta'] == .01)
            for name in ('matched', 'connected')}


def alias_figure(output, arrays, report):
    cycles = arrays['stroboscopic_cycles']
    series = [('four_connected', '4 modes / connected', AMBER),
              ('thirty_two_connected', '32 modes / connected', TEAL),
              ('thirty_two_complete', '32 modes / every relation', INK)]
    fig, ax = plt.subplots(figsize=(9.5, 3.65))
    columns = [cycles]
    header = ['cycle_n']
    for key, label, color in series:
        values = arrays[key + '_distance']
        running_minimum = np.minimum.accumulate(values)
        ax.step(cycles, running_minimum, where='post', color=color, lw=1.6, label=label)
        columns.extend([values, running_minimum])
        header.extend([key + '_distance', key + '_closest_so_far'])
    ax.axhline(.02, color=MUTED, ls=(0, (3, 3)), lw=1)
    ax.text(3600, .0245, 'overlap threshold 2η = 0.02', ha='right', fontsize=10.5, color=MUTED)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(1, 4096)
    ax.set_ylim(8e-5, 1)
    ax.set_xticks([1, 10, 100, 1000, 4096], ['1', '10', '100', '1000', '4096'])
    ax.set_yticks([.0001, .001, .01, .1, 1], ['0.0001', '0.001', '0.01', '0.1', '1'])
    ax.minorticks_off()
    ax.set_xlabel('Searched candidate cycles n / time separation = 2πn', labelpad=9)
    ax.set_ylabel('Closest readout distance so far', labelpad=8)
    ax.grid(axis='y', color=LINE, alpha=.55, lw=.6)
    ax.legend(loc='lower left', fontsize=10.5)
    fig.subplots_adjust(left=.12, bottom=.23, right=.955, top=.97)
    save_figure(fig, output, '03-distant-ambiguity')
    write_csv(output / '03-distant-ambiguity.csv', header, zip(*columns))
    witness = next(row for row in report['midpoint_cases'] if row['clock'] == 'four'
                   and row['observer'] == 'connected' and row['cycle'] == 29 and row['eta'] == .01)
    return {'cycle_29_midpoint': witness,
            'complete_32_minimum': float(arrays['thirty_two_complete_distance'].min())}


def discrimination_figure(output, report):
    fig, ax = plt.subplots(figsize=(9.5, 3.55))
    rows, summary = [], {}
    for key, n, top in [('first_return', 1, 3.3),
                        ('constructed_return', report['witness']['n'], 1.35)]:
        value = report['cases'][key]['energy']
        ax.text(0, top, f'CYCLE {n:,}', fontsize=12, color=INK, weight='bold')
        summary[key] = {'n': n, 'distance': value['full']['distance'],
                        'restricted_success': value['restricted']['optimal_success'],
                        'unrestricted_success': value['full']['optimal_success']}
        for kind, label, color, y in [('restricted', 'Within groups', TEAL, top - .48),
                                       ('full', 'Unrestricted', AMBER, top - .98)]:
            success = value[kind]['optimal_success']
            ax.barh(y, 100 * success, height=.20, color=color)
            ax.text(100 * success + 1.7, y, f'{100 * success:.3f}%',
                    fontsize=13, va='center', color=color)
            ax.text(-2, y, label, fontsize=12, ha='right', va='center', color=MUTED)
            rows.append([n, kind, success, value[kind]['distance']])
    ax.axvline(50, color=MUTED, lw=.9, ls=(0, (3, 3)))
    ax.set_xlim(0, 120)
    ax.set_ylim(-.3, 3.6)
    ax.set_yticks([])
    ax.set_xticks([0, 50, 100], ['0%', '50% / chance', '100%'])
    ax.set_xlabel('Best single-copy success / equal prior probabilities', labelpad=10, fontsize=12)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(axis='x', length=0, labelsize=11)
    fig.subplots_adjust(left=.175, right=.985, top=.99, bottom=.20)
    save_figure(fig, output, '04-snapshot-discrimination')
    write_csv(output / '04-snapshot-discrimination.csv',
              ['cycle_n', 'allowed_measurements', 'optimal_single_copy_success', 'trace_distance'], rows)
    return {'rows': summary, 'certificate': report['witness'],
            'high_precision_D': report['high_precision']['constructed_return']['distance'],
            'scope': 'One known quantum snapshot preparation, equal priors, no external cycle count or retained history.'}


def environment_figure(output, report):
    """Four saved clock marginals; color never substitutes for the controls."""
    fig, ax = plt.subplots(figsize=(9.5, 4.25))
    rows = []
    entries = [
        ('isolated', 'Isolated', 'No interaction', INK, 'Product', 'Reference'),
        ('plus', 'Coherent', '|+⟩⟨+|', AMBER, 'Entangled', '0.947 bits'),
        ('mixed', 'Mixed', 'I₂ / 2', TEAL, 'Separable', 'Same clock state'),
        ('eigenstate', 'Eigenstate', '|0⟩⟨0|', INK, 'Product', 'Detuning only'),
    ]
    ax.axhspan(.56, 2.44, color='#E5E9DF', zorder=0)
    for index, (key, label, preparation, color, status, detail) in enumerate(entries):
        y = 3 - index
        if key == 'isolated':
            distance = report['isolated']['4109']['distance']
            environment_distance, joint_distance, negative = 0., distance, 0.
        else:
            case = report['cases']['n4109_' + key]
            distance = case['return']['S']['distance']
            environment_distance = case['return']['E']['distance']
            joint_distance = case['return']['SE']['distance']
            negative = case['negativity']
        ax.hlines(y, 0, 1, color=LINE, lw=.8, zorder=1)
        ax.plot([0, distance], [y, y], color=color, lw=3.4, solid_capstyle='round', zorder=2)
        ax.scatter([distance], [y], s=50, color=color, edgecolor=PAPER, linewidth=.8, zorder=3)
        position = .19 + .71 * (y + .5) / 4
        fig.text(.025, position + .026, label, fontsize=13, color=INK)
        fig.text(.025, position - .025, preparation, fontsize=11.5, color=MUTED)
        fig.text(.685, position, f'{distance:.6f}', fontsize=12.2, color=color, va='center')
        fig.text(.818, position + .026, status, fontsize=12.5, color=INK)
        fig.text(.818, position - .025, detail, fontsize=10.5, color=MUTED)
        rows.append([4109, key, distance, environment_distance, joint_distance, negative, status])
    ax.set_xlim(0, 1)
    ax.set_ylim(-.5, 3.5)
    ax.set_xticks([0, .5, 1], ['0', '0.5', '1'])
    ax.set_yticks([])
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(axis='x', length=0, labelsize=11)
    ax.set_xlabel('Full-clock return distance Dₛ', fontsize=12, labelpad=8)
    ax.set_position([.24, .19, .415, .71])
    fig.text(.025, .955, 'ENVIRONMENT', fontsize=10, color=MUTED)
    fig.text(.685, .955, 'DISTANCE', fontsize=10, color=MUTED)
    fig.text(.818, .955, 'JOINT STATE', fontsize=10, color=MUTED)
    save_figure(fig, output, '05-isolation-and-return')
    write_csv(output / '05-isolation-and-return.csv',
              ['cycle_n', 'preparation', 'clock_distance', 'environment_distance',
               'joint_distance', 'negativity', 'joint_status'], rows)
    return {'cycle': 4109, 'rows': rows,
            'same_clock_state': ['plus', 'mixed'],
            'scope': 'Separate changed-Hamiltonian extension; no film reinterpretation; known snapshots, one copy, equal priors, no external time record.'}


def make_figures(output, clock_study, time_study, operational_study, environment_study):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    style()
    clock_report, clock_arrays = checked_study(clock_study)
    time_report, time_arrays = checked_study(time_study)
    operational_report, operational_arrays = checked_study(operational_study)
    environment_report, environment_arrays = checked_study(environment_study)
    try:
        summary = {'return': phase_figure(output, clock_arrays, clock_report),
                   'local_thresholds': local_figure(output, time_report),
                   'ambiguity': alias_figure(output, time_arrays, time_report),
                   'discrimination': discrimination_figure(output, operational_report),
                   'environment': environment_figure(output, environment_report),
                   'source_studies': {
                       'relational-clock-001': digest(Path(clock_study) / 'record.npz'),
                       'time-ambiguity-001': digest(Path(time_study) / 'record.npz'),
                       'operational-time-001/run-002': digest(Path(operational_study) / 'record.npz'),
                       'clock-environment-001/run-001': digest(Path(environment_study) / 'record.npz')},
                   'scope': 'Original diagrams and exact plot reductions of admitted saved data; no new dynamics.'}
    finally:
        clock_arrays.close()
        time_arrays.close()
        operational_arrays.close()
        environment_arrays.close()
    (output / 'figure-data.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    return summary, clock_report, time_report, operational_report, environment_report
