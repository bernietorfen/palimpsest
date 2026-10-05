"""Join accepted original and revised film sections without re-encoding.

The revision replaces 132-180 film seconds on the same absolute model timeline.
This program admits only complete twelve-second sections with matching sources
for the phase geometry, materials and original light/camera definitions.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess

from studio.river_delivery import identity, probe, stream


def require(condition, message):
    if not condition:
        raise ValueError(message)


def packet_timeline(path, count, *, zero_start=False):
    """Check integer packet timing without assuming that each chunk starts at zero."""
    result = subprocess.run([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_streams',
        '-show_packets', '-show_data_hash', 'sha256', '-show_entries',
        'stream=codec_name,width,height,pix_fmt,avg_frame_rate,time_base,start_pts,duration_ts,nb_frames,color_range,color_space,color_transfer,color_primaries,extradata_hash:'
        'packet=pts,dts,duration,flags', '-of', 'json', str(path)],
        check=True, capture_output=True, text=True)
    require(not result.stderr.strip(), 'Section packet reader reported an error')
    return check_packet_timeline(json.loads(result.stdout), count, zero_start=zero_start)


def check_packet_timeline(record, count, *, zero_start=False):
    require(len(record['streams']) == 1, 'Expected one selected picture stream')
    video = record['streams'][0]
    for key, expected in {'codec_name': 'hevc', 'width': 3840, 'height': 2160,
                          'pix_fmt': 'yuv420p10le', 'color_range': 'tv',
                          'color_space': 'bt709', 'color_transfer': 'bt709',
                          'color_primaries': 'bt709'}.items():
        require(video.get(key) == expected, f'A section has the wrong {key}')
    require(Fraction(video['avg_frame_rate']) == 24, 'A section has the wrong frame rate')
    step = Fraction(1, 24) / Fraction(video['time_base'])
    require(step.denominator == 1 and step > 0, 'Time base cannot represent exact 24-fps frames')
    step = int(step)
    require(int(video['nb_frames']) == count and int(video['duration_ts']) == count * step,
            'A section has the wrong count or duration')
    require(video.get('extradata_hash', '').startswith('SHA256:'), 'Missing codec header identity')
    packets = record['packets']
    require(len(packets) == count, 'Missing or extra picture packets')
    require('K' in packets[0]['flags'], 'A section does not start on a key frame')
    pts = sorted(int(packet['pts']) for packet in packets)
    dts = [int(packet['dts']) for packet in packets]
    first = int(video['start_pts'])
    require(pts == [first + index * step for index in range(count)],
            'Picture packet presentation cadence changed')
    require(all(right - left == step for left, right in zip(dts, dts[1:])),
            'Picture packet decode cadence changed')
    require(all(int(packet['duration']) == step for packet in packets),
            'Picture packet duration changed')
    require(not zero_start or first == 0, 'Assembled picture does not begin at zero')
    header = {key: video[key] for key in ('codec_name', 'width', 'height', 'pix_fmt',
              'time_base', 'color_range', 'color_space', 'color_transfer',
              'color_primaries', 'extradata_hash')}
    return {'header': header, 'packets': count, 'ticks_per_frame': step,
            'first_pts': first, 'last_pts': pts[-1], 'first_dts': dts[0],
            'exact_relative_cadence': True, 'first_packet_is_keyframe': True}


def compare_frame_updates(original, revised):
    """Permit only the declared camera selector inside the per-frame update."""
    trees = [ast.parse(Path(path).read_text()) for path in (original, revised)]
    digests = {}
    for name in ('update_curve', 'frame_state'):
        functions = []
        for index, tree in enumerate(trees):
            matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
            require(len(matches) == 1, f'Missing or duplicate {name} definition')
            node = matches[0]
            if name == 'frame_state':
                assignments = [item for item in ast.walk(node) if isinstance(item, ast.Assign)
                               and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name)
                               and item.targets[0].id == 'camera_state']
                require(len(assignments) == 1, 'Unexpected camera selector assignment')
                expression = ('camera_at(seconds)' if index == 0 else
                              "pickup_camera_at(seconds) if getattr(args, 'camera_revision', False) else camera_at(seconds)")
                require(ast.dump(assignments[0].value) == ast.dump(ast.parse(expression, mode='eval').body),
                        'The camera selector differs from the accepted revision')
                assignments[0].value = ast.Constant(value='accepted camera selector')
            functions.append(ast.dump(node))
        require(functions[0] == functions[1], 'A per-frame geometry or light update changed')
        digests[name] = hashlib.sha256(functions[0].encode()).hexdigest()
    return {'normalized_ast_sha256': digests,
            'scope': 'The curve and frame update functions match after the declared camera selector substitution; camera-dependent sample limits may differ.'}


def load_record(folder, start, duration):
    path = folder / 'render.json'
    report = json.loads(path.read_text())
    require(report['start'] == start and report['duration'] == duration,
            'The rendered interval differs from the assembly plan')
    require(report['fps'] == 24 and report['frames'] == duration * 24
            and report['resolution'] == [3840, 2160], 'Expected the completed 4K24 production')
    require(report['single_temporary_frame_removed'], 'The production is not settled')
    require('open-gop=0' in ' '.join(report['encoder_command']),
            'The source does not declare independently closed picture groups')
    for name, digest in report['source_sha256'].items():
        require(PurePosixPath(name).name == name, 'Unsafe captured source filename')
        require(identity(folder / 'source' / name)['sha256'] == digest, 'Captured source changed')
    chunks = report['chunks']
    require(len(chunks) == duration // 12, 'Wrong number of completed sections')
    clocks = []
    for index, chunk in enumerate(chunks):
        expected_name = f'chunks/part-{index:03d}.mp4'
        require(chunk['file'] == expected_name, 'Unexpected section order or filename')
        actual = identity(folder / expected_name)
        require(actual['bytes'] == chunk['bytes'] and actual['sha256'] == chunk['sha256'],
                'Completed section bytes changed')
        clocks.append(packet_timeline(folder / expected_name, 288))
        require(clocks[-1]['header'] == clocks[0]['header'], 'Section codec headers or time bases differ')
    rows = [json.loads(line) for line in (folder / 'frames.jsonl').read_text().splitlines()]
    require(len(rows) == duration * 24, 'Rendered frame log has missing or extra entries')
    require(all(row['frame'] == index and abs(row['film_time'] - (start + index / 24)) < 1e-10
                for index, row in enumerate(rows)), 'Rendered frame order or time changed')
    return report, rows, clocks


def main(args):
    output, base, revised = Path(args.output), Path(args.base), Path(args.revised)
    require(not output.exists(), 'Choose a new assembly directory')
    original, original_rows, original_clocks = load_record(base, 0, 240)
    replacement, revised_rows, revised_clocks = load_record(revised, 132, 48)
    require(original_clocks[0]['header'] == revised_clocks[0]['header'],
            'Replacement codec headers or time base differ from the original')
    require(original.get('camera_revision') is None, 'The base must be the original camera score')
    require((replacement.get('camera_revision') or {}).get('edition') == 'connecting-fibres-v1',
            'The replacement must use the declared fibre camera revision')
    preserved = ('river_geometry.py', 'river_blender.py', 'river_cinematography.py', 'river_typography.py')
    for name in preserved:
        require(original['source_sha256'][name] == replacement['source_sha256'][name],
                'A source outside the camera revision changed')
    frame_updates = compare_frame_updates(base / 'source/river_sequence.py',
                                         revised / 'source/river_sequence.py')
    for index, row in enumerate(revised_rows):
        prior = original_rows[132 * 24 + index]
        require(all(abs(row[key] - prior[key]) < 1e-12
                    for key in ('film_time', 'model_time', 'light', 'reference_focus')),
                'The revision changed model time or composed observation light')
        if 132 <= row['film_time'] < 136 or 148 <= row['film_time'] < 160:
            require(row['shot'] == prior['shot'] and abs(row['camera_lens'] - prior['camera_lens']) < 1e-9,
                    'An unrevised camera interval changed')
            for key in ('camera_location', 'camera_rotation'):
                require(len(row[key]) == len(prior[key]) == 3
                        and max(abs(a - b) for a, b in zip(row[key], prior[key])) < 2e-6,
                        'An unrevised camera pose changed')
    output.mkdir(parents=True)
    (output / 'source').mkdir()
    shutil.copyfile(__file__, output / 'source' / Path(__file__).name)
    shutil.copyfile(base / 'render.json', output / 'source/original-render.json')
    shutil.copyfile(revised / 'render.json', output / 'source/revised-render.json')
    selected, lines = [], []
    for index in range(20):
        use_revised = 11 <= index < 15
        source_index = index - 11 if use_revised else index
        folder = revised if use_revised else base
        source_report = replacement if use_revised else original
        chunk = source_report['chunks'][source_index]
        path = (folder / chunk['file']).resolve()
        require("'" not in str(path) and '\n' not in str(path), 'Unsafe concat path')
        lines.append(f"file '{path.as_posix()}'\nduration 12\n")
        selected.append({'first_frame': index * 288, 'frames': 288, 'film_start': index * 12,
                         'source': folder.name, 'source_section': chunk['file'],
                         'source_film_start': (132 if use_revised else 0) + source_index * 12,
                         'bytes': chunk['bytes'], 'sha256': chunk['sha256'],
                         'packet_timeline': (revised_clocks if use_revised else original_clocks)[source_index]})
    concat = output / 'sections.concat.txt'
    concat.write_text(''.join(lines))
    video = output / 'river-silent-10bit.mp4'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-xerror', '-nostdin', '-n',
                    '-f', 'concat', '-safe', '0', '-i', str(concat), '-map', '0:v:0',
                    '-c:v', 'copy', '-tag:v', 'hvc1', '-movflags', '+faststart', str(video)], check=True)
    encoded = probe(video)
    picture = stream(encoded, 'video')
    require(int(picture['nb_frames']) == 5760 and abs(float(picture['duration']) - 240) < 1e-4
            and abs(float(picture['start_time'])) < 1e-6, 'Assembled picture timeline is incomplete')
    require(abs(float(encoded['format']['duration']) - 240) < .002, 'Assembled container duration changed')
    assembled_clock = packet_timeline(video, 5760, zero_start=True)
    with (output / 'frames.jsonl').open('w') as destination:
        for index in range(5760):
            replaced = 132 * 24 <= index < 180 * 24
            source_index = index - 132 * 24 if replaced else index
            row = dict((revised_rows if replaced else original_rows)[source_index])
            row.update(frame=index, source_frame=source_index,
                       source_render=revised.name if replaced else base.name)
            destination.write(json.dumps(row) + '\n')
    report = {'format': 'palimpsest-river-picture-assembly-v1', 'version': 1,
              'title': 'A River Twice', 'created_utc': datetime.now(timezone.utc).isoformat(),
              'start': 0, 'duration': 240, 'duration_seconds': 240, 'fps': 24, 'frames': 5760,
              'resolution': [3840, 2160], 'video': video.name, 'picture': identity(video),
              'original_render_receipt': identity(base / 'render.json'),
              'revised_render_receipt': identity(revised / 'render.json'),
              'original_frame_log': identity(base / 'frames.jsonl'),
              'revised_frame_log': identity(revised / 'frames.jsonl'),
              'assembled_frame_log': identity(output / 'frames.jsonl'),
              'sections': selected, 'preserved_source_sha256': {name: original['source_sha256'][name]
                                                              for name in preserved},
              'revised_camera': replacement['camera_revision'],
              'sequence_sources': {'original': identity(base / 'source/river_sequence.py'),
                                   'revised': identity(revised / 'source/river_sequence.py')},
              'frame_update_check': frame_updates, 'packet_timeline': assembled_clock,
              'source': identity(__file__), 'model_and_light_log_comparisons': len(revised_rows),
              'encoded_without_reencoding': True, 'all_passed': True,
              'scope': 'Picture assembly and same-time source checks. Sound is added separately; final delivery independently decodes all presentation timestamps.'}
    (output / 'render.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'picture': report['picture'], 'frames': 5760,
                      'all_passed': True}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True)
    parser.add_argument('--revised', required=True)
    parser.add_argument('--output', required=True)
    main(parser.parse_args())
