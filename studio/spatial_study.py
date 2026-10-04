"""Predeclared three-grid check with the original echo geometry registered."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import time

import numpy as np
from scipy.spatial.distance import cdist, pdist, squareform
import torch

from studio.assay import relax
from studio.batched_material import BatchedMaterial
from studio.material import MaterialConfig, PalimpsestMaterial
from studio.preserve import sha256
from studio.pressure_study import LABELS, ORDERS, SOURCE_FILES, probe_drives, state_difference, writing_drives


GRIDS = (128, 256, 512)
RATES = (96, 192)
FIELD_LABELS = ('ABCDE', 'DEABC')


def register_echo(material):
    size = material.cfg.size
    if size not in GRIDS:
        raise ValueError('This declared lift supports grids 128, 256 and 512')
    target = (18 * size // 128, 11 * size // 128)
    native = (size // 7, size // 11)
    delta = tuple(a - b for a, b in zip(target, native))
    if delta != (0, 0):
        for name in ('echo_modes', 'echo_quadratures'):
            setattr(material, name, torch.roll(getattr(material, name), delta, (-2, -1)))
    return material


def admit(config, directory):
    orders = [ORDERS[LABELS.index(label)] for label in FIELD_LABELS]
    batch = register_echo(BatchedMaterial(config, 2))
    scalar = [register_echo(PalimpsestMaterial(config)) for _ in range(2)]
    drive = writing_drives(orders, np.ones((2, 5), np.float32), config)
    for step in range(len(drive)):
        batch.step(drive[step])
        for index, material in enumerate(scalar):
            material.step(drive[step, index], feedback=.08)
    written = state_difference(batch, scalar)
    batch.reset_transients()
    for material in scalar:
        relax(material)
    drive = probe_drives(config)
    stride = round(1 / (24 * config.dt))
    differences = []
    for step in range(len(drive)):
        if step % stride == 0:
            expected = np.stack([material.readout()['pitch_hz'].cpu().numpy() for material in scalar])
            differences.append(batch.tuning()[2].cpu().numpy().astype(float) - expected.astype(float))
        batch.step(drive[step].expand(2, -1))
        for material in scalar:
            material.step(drive[step], feedback=.08)
    probed = state_difference(batch, scalar)
    delta = np.asarray(differences)
    admitted = batch.finite() and all(value <= .0002 for state in (written, probed)
                                     for key, value in state.items() if key != 'echo_phase_raw')
    result = {'grid': config.size, 'rate': round(1 / config.dt), 'labels': list(FIELD_LABELS),
              'written_state_max_absolute': written, 'probed_state_max_absolute': probed,
              'state_tolerance': .0002, 'probe_pitch_rms_hz': float(np.sqrt(np.mean(delta * delta))),
              'probe_pitch_max_absolute_hz': float(np.abs(delta).max()), 'admitted': admitted}
    (directory / 'scalar-admission.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'scalar_admission': result}), flush=True)
    if not admitted:
        raise ValueError('The registered batched equations failed scalar admission')
    return result


def run_cases(config, begin, stop, directory):
    count = stop - begin
    material = register_echo(BatchedMaterial(config, count))
    drive = writing_drives(ORDERS[begin:stop], np.ones((count, 5), np.float32), config)
    for step in range(len(drive)):
        material.step(drive[step])
    if not material.finite():
        raise FloatingPointError('Non-finite written material')
    retained = {'memory_rms': material.p.square().mean(dim=(-2, -1)).sqrt().cpu().numpy(),
                'fatigue_mean': material.z.mean(dim=(-2, -1)).cpu().numpy()}
    for label in FIELD_LABELS:
        index = LABELS.index(label)
        if begin <= index < stop:
            np.savez_compressed(directory / f'writing-{label}.npz', label=label,
                                inscription=material.p[index - begin].cpu().numpy(),
                                fatigue=material.z[index - begin].cpu().numpy())
    material.reset_transients()
    drive = probe_drives(config)
    stride = round(1 / (24 * config.dt))
    pitches = torch.empty((count, 336, 12), device=material.device, dtype=material.dtype)
    for step in range(len(drive)):
        if step % stride == 0:
            pitches[:, step // stride] = material.tuning()[2]
        material.step(drive[step].expand(count, -1))
    if not material.finite() or not bool(torch.isfinite(pitches).all()):
        raise FloatingPointError('Non-finite probed material')
    return pitches.cpu().numpy(), retained


def compare(directory, key, coarse, fine):
    reference, query = coarse.reshape(120, -1).astype(float), fine.reshape(120, -1).astype(float)
    distances = cdist(query, reference) / math.sqrt(reference.shape[1])
    predicted = distances.argmin(axis=1)
    own = np.diag(distances).copy()
    other = distances.copy()
    np.fill_diagonal(other, np.inf)
    margin = other.min(axis=1) - own
    np.savez_compressed(directory / f'{key}.npz', distances_hz=distances, predicted=predicted,
                        own_distance_hz=own, margin_hz=margin, labels=np.array(LABELS))
    return {'correct_nearest_history': int(np.count_nonzero(predicted == np.arange(120))), 'tested': 120,
            'minimum_margin_hz': float(margin.min()), 'median_own_distance_hz': float(np.median(own)),
            'maximum_own_distance_hz': float(own.max()), 'rms_all_histories_hz': float(np.sqrt(np.mean(own * own)))}


def field_comparison(coarse_folder, fine_folder, stride):
    values = {}
    for label in FIELD_LABELS:
        with np.load(coarse_folder / f'writing-{label}.npz') as coarse, np.load(fine_folder / f'writing-{label}.npz') as fine:
            values[label] = {}
            for field in ('inscription', 'fatigue'):
                delta = fine[field][::stride, ::stride].astype(float) - coarse[field].astype(float)
                values[label][field] = {'rms': float(np.sqrt(np.mean(delta * delta))),
                                        'max_absolute': float(np.abs(delta).max())}
    return values


def main(args):
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision('highest')
    out, atlas = Path(args.output), Path(args.atlas)
    out.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for relative in SOURCE_FILES + ['studio/spatial_study.py', 'research/SPATIAL-STUDY.md']:
        path = Path(relative)
        target = out / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        hashes[relative] = sha256(path)
    began = time.monotonic()
    reports, records = {}, {}
    for size in GRIDS:
        for rate in RATES:
            config = MaterialConfig(size=size, dt=1 / rate, feedback=.08)
            directory = out / f'grid-{size}' / f'rate-{rate}'
            directory.mkdir(parents=True)
            summary = {'config': asdict(config), 'registered_echo_shift_yx': [18 * size // 128, 11 * size // 128]}
            if size > 128:
                summary['scalar_admission'] = admit(config, directory)
            batches, memory, fatigue = [], [], []
            batch_size = 32 if size == 512 else 64
            for begin in range(0, 120, batch_size):
                stop = min(120, begin + batch_size)
                pitches, retained = run_cases(config, begin, stop, directory)
                np.savez_compressed(directory / f'batch-{begin:04d}.npz', labels=np.array(LABELS[begin:stop]),
                                    pitch_hz=pitches, **retained)
                batches.append(pitches); memory.append(retained['memory_rms']); fatigue.append(retained['fatigue_mean'])
                print(json.dumps({'grid': size, 'rate': rate, 'completed': stop, 'seconds': time.monotonic() - began}), flush=True)
            pitches = np.concatenate(batches)
            records[(size, rate)] = pitches
            np.savez_compressed(directory / 'atlas.npz', labels=np.array(LABELS), pitch_hz=pitches,
                                memory_rms=np.concatenate(memory), fatigue_mean=np.concatenate(fatigue))
            pairwise = pdist(pitches.reshape(120, -1).astype(float)) / math.sqrt(4032)
            np.save(directory / 'pairwise-rms-hz.npy', squareform(pairwise))
            pairs = np.column_stack(np.triu_indices(120, 1))
            summary['pairwise'] = {'pairs': len(pairwise), 'above_1e_minus_6_hz': int(np.count_nonzero(pairwise > 1e-6)),
                                   'minimum_hz': float(pairwise.min()), 'median_hz': float(np.median(pairwise)),
                                   'maximum_hz': float(pairwise.max()),
                                   'closest': [LABELS[index] for index in pairs[pairwise.argmin()]]}
            if size == 128:
                with np.load(atlas / f'rate-{rate}' / 'atlas.npz') as reference:
                    if reference['labels'].tolist() != LABELS:
                        raise ValueError('The original atlas history order changed')
                    summary['original_atlas_admission'] = compare(directory, 'original-atlas', reference['pitch_hz'], pitches)
                original = summary['original_atlas_admission']
                if original['correct_nearest_history'] != 120 or original['maximum_own_distance_hz'] > .001:
                    raise ValueError('The registered 128-grid recorder differs from the original atlas')
            reports[f'{size}/{rate}'] = summary
            (directory / 'report.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
            print(json.dumps({'grid': size, 'rate': rate, 'pairwise': summary['pairwise']}), flush=True)
    comparisons = out / 'comparisons'
    comparisons.mkdir()
    cross = {}
    for rate in RATES:
        for coarse, fine in ((128, 256), (256, 512), (128, 512)):
            key = f'grid-{coarse}-{fine}-rate-{rate}'
            result = compare(comparisons, key, records[(coarse, rate)], records[(fine, rate)])
            result['coincident_retained_fields'] = field_comparison(out / f'grid-{coarse}/rate-{rate}', out / f'grid-{fine}/rate-{rate}', fine // coarse)
            cross[key] = result
    for size in GRIDS:
        key = f'timestep-grid-{size}'
        result = compare(comparisons, key, records[(size, 96)], records[(size, 192)])
        result['coincident_retained_fields'] = field_comparison(out / f'grid-{size}/rate-96', out / f'grid-{size}/rate-192', 1)
        cross[key] = result
    files = [{'path': str(path.relative_to(out)), 'bytes': path.stat().st_size, 'sha256': sha256(path)}
             for path in sorted(out.rglob('*')) if path.is_file()]
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': hashes,
              'original_atlas_sha256': {str(rate): sha256(atlas / f'rate-{rate}/atlas.npz') for rate in RATES},
              'grids': list(GRIDS), 'rates': list(RATES), 'echo_translation_yx_fraction': [18 / 128, 11 / 128],
              'summaries': reports, 'comparisons': cross, 'files': files, 'seconds': time.monotonic() - began,
              'scope': 'Finite registered spatial lift of the original 128-grid instrument. No continuum, physical-material or auditory proof.'}
    (out / 'report.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'finished': str(out), 'seconds': result['seconds'],
                      'comparisons': {key: {k: v for k, v in value.items() if k != 'coincident_retained_fields'} for key, value in cross.items()}}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='artifacts/studies/spatial-study-001')
    parser.add_argument('--atlas', default='artifacts/studies/history-atlas-001')
    main(parser.parse_args())
