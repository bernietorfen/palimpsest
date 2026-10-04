"""Verify every continuation asset, restore its inputs and rebuild the actual book."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from pypdf import PdfReader

from studio.preserve import sha256
from studio.verify_pressure_edition import safe


def page_images(page):
    resources = page['/Resources'].get_object()
    objects = resources.get('/XObject', {})
    if hasattr(objects, 'get_object'):
        objects = objects.get_object()
    result = []
    for obj in objects.values():
        image = obj.get_object()
        if image.get('/Subtype') == '/Image':
            result.append((int(image['/Width']), int(image['/Height']),
                           hashlib.sha256(image.get_data()).hexdigest()))
    return sorted(result)


def main(args):
    edition, proof, output = Path(args.edition), Path(args.proof), Path(args.output)
    if proof.exists() or output.exists():
        raise FileExistsError('Use new verification output paths')
    manifest_path = edition / 'palimpsest-complete-edition.json'
    manifest = json.loads(manifest_path.read_text())
    for item in manifest['files']:
        if Path(item['name']).name != item['name']:
            raise ValueError('Expected a flat release asset name')
        path = edition / item['name']
        if path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
            raise ValueError(f"Changed release asset: {item['name']}")
    expected_checksums = {item['name']: item['sha256'] for item in manifest['files']}
    expected_checksums[manifest_path.name] = sha256(manifest_path)
    saved = {name: digest for digest, name in
             (line.split('  ', 1) for line in (edition / 'palimpsest-checksums.sha256').read_text().splitlines())}
    if saved != expected_checksums:
        raise ValueError('Release checksums differ')
    actual, embedded, seen = {}, None, set()
    archive_path = edition / 'palimpsest-continuation-record.tar.gz'
    with tarfile.open(archive_path, 'r:gz') as archive:
        for member in archive:
            safe(member.name)
            if not member.isfile() or member.name in seen:
                raise ValueError('Unsupported or duplicate record member')
            seen.add(member.name)
            with archive.extractfile(member) as stream:
                if member.name == 'continuation-record-manifest.json':
                    embedded = json.load(stream)
                    continue
                digest, size = hashlib.sha256(), 0
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block); size += len(block)
            actual[member.name] = {'path': member.name, 'bytes': size, 'sha256': digest.hexdigest()}
    if embedded is None or embedded['source_commit'] != manifest['source_commit']:
        raise ValueError('Archive source identity differs')
    if actual != {item['path']: item for item in embedded['files']} or len(actual) + 1 != manifest['scientific_archive_files']:
        raise ValueError('Archive contents differ from the embedded manifest')
    proof.mkdir(parents=True)
    with tarfile.open(archive_path, 'r:gz') as archive:
        for member in archive:
            target = proof / safe(member.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open('xb') as destination:
                shutil.copyfileobj(source, destination, 1024 * 1024)
    shutil.copytree(Path(args.source) / 'studio', proof / 'studio')
    run = subprocess.run([sys.executable, '-m', 'studio.complete_notebook', '--output', 'output/rebuilt.pdf'],
                         cwd=proof, env={**os.environ, 'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2'},
                         text=True, capture_output=True, check=False)
    (proof / 'rebuild.log').write_text(run.stdout + run.stderr)
    if run.returncode:
        raise ValueError(f'Book reconstruction failed; see {proof}/rebuild.log')
    original = PdfReader(edition / 'palimpsest-complete-notebook.pdf')
    rebuilt = PdfReader(proof / 'output/rebuilt.pdf')
    if len(original.pages) != 24 or len(rebuilt.pages) != 24:
        raise ValueError('Unexpected notebook page count')
    pages = []
    for index, (left, right) in enumerate(zip(original.pages, rebuilt.pages)):
        if left.extract_text() != right.extract_text():
            raise ValueError(f'Rebuilt page text differs: {index + 1}')
        if left.get_contents().get_data() != right.get_contents().get_data():
            raise ValueError(f'Rebuilt page drawing commands differ: {index + 1}')
        if page_images(left) != page_images(right):
            raise ValueError(f'Rebuilt embedded image differs: {index + 1}')
        pages.append({'page': index + 1, 'text_equal': True, 'drawing_commands_equal': True,
                      'embedded_images_equal': True, 'images': len(page_images(left))})
    result = {'verified_utc': datetime.now(timezone.utc).isoformat(), 'source_commit': manifest['source_commit'],
        'manifest_sha256': sha256(manifest_path), 'release_files_verified': len(manifest['files']),
        'record_files_verified': len(actual), 'archive_fully_streamed_and_hashed': True,
        'restored_book_rebuilt': True, 'pages': pages,
        'scope': 'Book content and exact embedded images match after reconstruction from the public record. PDF container metadata may differ.'}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'assets': len(manifest['files']), 'record_files': len(actual),
                      'rebuilt_pages': len(pages), 'all_page_content_matches': True}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--edition', default='artwork/complete-edition-001')
    parser.add_argument('--proof', default='artwork/complete-proof-001')
    parser.add_argument('--source', default='artwork/public-source-009')
    parser.add_argument('--output', default='research/complete-edition-verification-001.json')
    main(parser.parse_args())
