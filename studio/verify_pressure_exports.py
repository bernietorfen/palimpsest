"""Check actual browser SVG downloads against the saved display measurements."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import numpy as np
from studio.preserve import sha256


def main(args):
    public = Path(args.public)
    record = json.loads((public / 'pressure-study-v1.json').read_text())
    glyphs = np.fromfile(public / record['glyph_file'], dtype='<i2').reshape(record['glyph_shape']) / 32767
    ns = {'s': 'http://www.w3.org/2000/svg'}
    results = []
    for filename in args.files:
        path = Path(filename)
        root = ET.parse(path).getroot()
        metadata = json.loads(root.find('s:metadata', ns).text)
        level = next(item for item in record['levels'] if item['percent'] == metadata['pressure_limit_percent'])
        truth = record['histories'].index(metadata['written_order'])
        case = truth * 8 + metadata['realization'] - 1
        column = 2 if metadata['reader'] == 'nearest' else 3
        chosen = level['points'][case][column]
        if metadata['chosen_order'] != record['histories'][chosen] or metadata['source_report_sha256'] != record['source_report_sha256']:
            raise ValueError('The exported case or provenance does not match')
        if metadata['pressure_factors_display'] != level['pressure_factors'][case]:
            raise ValueError('The exported pressure factors do not match')
        expected = np.stack([glyphs[level['glyph_offset'] + case], glyphs[chosen]])
        actual = np.array([metadata['measured_pitch_deviations_hz'], metadata['chosen_pitch_deviations_hz']])
        if not np.array_equal(actual, expected * record['glyph_scale_hz']):
            raise ValueError('The SVG metadata altered the measured display values')
        paths = root.findall('.//s:path', ns)
        if len(paths) != 8:
            raise ValueError('Expected eight measured rings')
        error = 0.
        for index, node in enumerate(paths):
            ring = index % 4
            values = expected[index // 4, ring]
            angles = np.arange(12) * np.pi / 6
            radii = 40 + ring * 24 + 18 * values
            anchors = np.stack([140 + radii * np.sin(angles), 140 - radii * np.cos(angles)], axis=-1)
            numbers = np.array([float(value) for value in re.findall(r'-?\d+(?:\.\d+)?', node.attrib['d'])])
            if len(numbers) != 74:
                raise ValueError('Unexpected closed cubic path')
            drawn = np.concatenate([numbers[:2][None], numbers[2:].reshape(12, 6)[:-1, 4:6]])
            error = max(error, float(np.abs(drawn - anchors).max()))
        if error > .000501:
            raise ValueError('The drawn anchors differ from the measured values')
        results.append({'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha256(path),
                        'case': metadata['written_order'], 'realization': metadata['realization'],
                        'reader': metadata['reader'], 'chosen': metadata['chosen_order'],
                        'metadata_values_exact': True, 'maximum_anchor_rounding_error_px': error})
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    result = {'verified_utc': datetime.now(timezone.utc).isoformat(), 'exports': results}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--public', default='artwork/analysis/pressure-reading-003/public')
    parser.add_argument('--output', default='research/pressure-exports-001.json')
    parser.add_argument('files', nargs='+')
    main(parser.parse_args())
