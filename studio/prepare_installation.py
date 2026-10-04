"""Freeze a portable installation of the film, interactive works and notebook."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

from studio.preserve import sha256


def main(args):
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    complete = Path('artwork/complete-edition-002')
    original_manifest = json.loads((complete / 'palimpsest-complete-edition.json').read_text())
    expected = {item['name']: item for item in original_manifest['files']}
    extras = {'palimpsest-complete-notebook.pdf': complete / 'palimpsest-complete-notebook.pdf',
              'a-mark-at-three-scales-print.pdf': complete / 'a-mark-at-three-scales-print.pdf'}
    for name, path in extras.items():
        if sha256(path) != expected[name]['sha256'] or path.stat().st_size != expected[name]['bytes']:
            raise ValueError('The frozen complete-edition input changed')
    files = {}
    for path in sorted(Path('site').rglob('*')):
        if not path.is_file():
            continue
        if path.is_symlink() or any(part.startswith('.') for part in path.parts):
            raise ValueError('Unexpected installation source path')
        if str(path) in ('site/vercel.json', 'site/assets/generated/edition.json'):
            continue
        files[str(path)] = path
    for name, path in extras.items():
        files['site/assets/generated/' + name] = path
    html = Path('site/index.html').read_text().replace(
        'https://github.com/bernietorfen/palimpsest/releases/download/v1.3.0/palimpsest-complete-notebook.pdf',
        '/assets/generated/palimpsest-complete-notebook.pdf')
    files['site/index.html'] = html.encode()
    credits = Path('site/credits.html').read_text().replace('/assets/generated/palimpsest-notebook.pdf',
        '/assets/generated/palimpsest-complete-notebook.pdf').replace('illustrated notebook', 'complete illustrated notebook')
    files['site/credits.html'] = credits.encode()
    catalog = json.loads(Path('site/edition.json').read_text())
    for entry in catalog['downloads']:
        if entry['title'] == 'The complete notebook':
            entry['url'] = '/assets/generated/palimpsest-complete-notebook.pdf'
        elif entry['title'] == 'A mark, at three scales':
            entry['url'] = '/assets/generated/a-mark-at-three-scales-print.pdf'
        elif entry['title'] == 'The portable instrument':
            entry.update(title='Play the instrument', detail='In this installation', url='/instrument.html')
        elif entry['title'] == 'An imperfect hand':
            entry.update(detail='Interactive study', url='/pressure.html')
        elif entry['url'].startswith('https://'):
            entry['detail'] = 'Online / ' + entry['detail']
    files['site/edition.json'] = (json.dumps(catalog, indent=2) + '\n').encode()
    start = (
        'PALIMPSEST / THE PORTABLE INSTALLATION\nCodex / 3-4 October 2026\n\n'
        'Extract this ZIP into an empty directory on an authorized computer.\n'
        'From the extracted directory, run:\n\n'
        '  python3 -m http.server 8080 --bind 127.0.0.1 --directory site\n\n'
        'Open http://127.0.0.1:8080/ in a modern browser on the same computer.\n'
        'Stop the server with Ctrl+C. It listens only on the local loopback interface.\n'
        'Direct file: opening is not supported because browsers restrict local fetches.\n\n'
        'Included: the complete 1080p film, paired phrase comparison, three interactive\n'
        'sculptures, playable material with synthesized sound, all 120 audible histories,\n'
        'the pressure explorer, fonts, example files, the 24-page complete notebook\n'
        'and the three-grid print PDF. These experiences need no external connection.\n\n'
        'Press Enter the film to begin. In Play, write a phrase, keep it, then ask it\n'
        'again. The retained material changes the answer. Save material to keep a JSON\n'
        'state file; the browser also retains a bounded recovery copy for that tab.\n'
        'Export drawings or sculptures from your own state.\n\n'
        'Catalog links marked Online lead to the 4K master, lossless soundtrack,\n'
        'large prints, scientific records and source. Those optional downloads need\n'
        'an internet connection. External authorship references also require it.\n\n'
        'A modern browser with WebGL2 and Web Audio is required for the interactive\n'
        'instrument. The film, notebook and static text remain separate readable files.\n'
        'Sound playback requires a deliberate click or keypress.\n\n'
        f'Source: https://github.com/bernietorfen/palimpsest/tree/{args.source_commit}\n'
        'Exact files and hashes: installation-content.json, also inside the ZIP.\n'
        'Type license: site/assets/generated/font-license.txt.\n'
    ).encode()
    files['START-HERE.txt'] = start
    records = []
    archive_path = out / 'palimpsest-installation.zip'
    with zipfile.ZipFile(archive_path, 'x') as archive:
        for name, original in sorted(files.items()):
            if isinstance(original, bytes):
                size, digest = len(original), hashlib.sha256(original).hexdigest()
                archive.writestr(name, original, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
            else:
                before = original.stat()
                size, digest = before.st_size, sha256(original)
                compressed = original.suffix in ('.mp4', '.m4a', '.jpg', '.png', '.woff2', '.pdf', '.glb')
                archive.write(original, name, compress_type=zipfile.ZIP_STORED if compressed else zipfile.ZIP_DEFLATED,
                              compresslevel=None if compressed else 6)
                after = original.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ValueError('Installation input changed while archiving')
            records.append({'path': name, 'bytes': size, 'sha256': digest})
        content = {'source_commit': args.source_commit, 'files': records,
            'portable_changes': 'The complete notebook and three-grid print are included locally; catalog entries distinguish local experiences from optional online master downloads. Vercel configuration is omitted.'}
        raw = (json.dumps(content, indent=2) + '\n').encode()
        archive.writestr('installation-content.json', raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    (out / 'installation-content.json').write_bytes(raw)
    (out / 'START-HERE.txt').write_bytes(start)
    items = [{'name': path.name, 'bytes': path.stat().st_size, 'sha256': sha256(path)}
             for path in sorted(out.iterdir()) if path.is_file()]
    manifest = {'title': 'PALIMPSEST / The portable installation', 'created_utc': datetime.now(timezone.utc).isoformat(),
                'source_commit': args.source_commit, 'files': items, 'installation_files': len(records) + 1,
                'uncompressed_bytes': sum(item['bytes'] for item in records),
                'scope': 'Portable viewing and interaction, with optional online links to larger masters and records.'}
    path = out / 'palimpsest-installation-edition.json'
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    lines = [f"{item['sha256']}  {item['name']}" for item in items] + [f'{sha256(path)}  {path.name}']
    (out / 'palimpsest-checksums.sha256').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'files': len(records) + 1, 'archive_bytes': archive_path.stat().st_size,
                      'uncompressed_bytes': manifest['uncompressed_bytes']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='artwork/installation-edition-001')
    parser.add_argument('--source-commit', required=True)
    main(parser.parse_args())
