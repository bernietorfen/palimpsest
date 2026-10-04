"""Verify the frozen study archives and extract only the small portable proof."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
import zipfile

from studio.preserve import sha256


def safe(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError(f'Unsafe archive member: {name}')
    return path


def main(args):
    edition, proof, output = Path(args.edition), Path(args.proof), Path(args.output)
    if proof.exists() or output.exists():
        raise FileExistsError('Use new verification output paths')
    manifest = json.loads((edition / 'palimpsest-pressure-edition.json').read_text())
    for item in manifest['files']:
        if Path(item['name']).name != item['name']:
            raise ValueError('Expected a flat release asset name')
        path = edition / item['name']
        if path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
            raise ValueError(f"Changed release asset: {item['name']}")
    expected_checksums = {item['name']: item['sha256'] for item in manifest['files']}
    expected_checksums['palimpsest-pressure-edition.json'] = sha256(edition / 'palimpsest-pressure-edition.json')
    saved_checksums = {name: digest for digest, name in
                       (line.split('  ', 1) for line in (edition / 'palimpsest-checksums.sha256').read_text().splitlines())}
    if saved_checksums != expected_checksums:
        raise ValueError('The checksum file differs from the verified release assets')
    actual, embedded, seen = {}, None, set()
    with tarfile.open(edition / 'palimpsest-pressure-record.tar.gz', 'r:gz') as archive:
        for member in archive:
            safe(member.name)
            if not member.isfile() or member.name in seen:
                raise ValueError('Unsupported or duplicate scientific archive member')
            seen.add(member.name)
            with archive.extractfile(member) as source:
                if member.name == 'pressure-record-manifest.json':
                    embedded = json.load(source)
                    continue
                digest, size = hashlib.sha256(), 0
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(block); size += len(block)
            actual[member.name] = {'path': member.name, 'bytes': size, 'sha256': digest.hexdigest()}
    if embedded is None or embedded['source_commit'] != manifest['source_commit']:
        raise ValueError('The scientific archive source identity differs')
    expected = {item['path']: item for item in embedded['files']}
    if actual != expected or len(actual) + 1 != manifest['scientific_archive_files']:
        raise ValueError('The scientific archive contents differ from their manifest')
    proof.mkdir(parents=True)
    with zipfile.ZipFile(edition / 'palimpsest-imperfect-hand.zip') as archive:
        inventory = json.loads(archive.read('portable-manifest.json'))
        names = archive.namelist()
        expected_names = [item['path'] for item in inventory['files']] + ['portable-manifest.json']
        if len(names) != len(set(names)) or set(names) != set(expected_names):
            raise ValueError('The portable archive has unexpected or duplicate files')
        if inventory['source_commit'] != manifest['source_commit']:
            raise ValueError('The portable archive source identity differs')
        for item in inventory['files']:
            safe(item['path'])
            content = archive.read(item['path'])
            if len(content) != item['bytes'] or hashlib.sha256(content).hexdigest() != item['sha256']:
                raise ValueError('The portable archive content differs')
            target = proof / item['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        (proof / 'portable-manifest.json').write_bytes(archive.read('portable-manifest.json'))
    result = {'verified_utc': datetime.now(timezone.utc).isoformat(), 'source_commit': manifest['source_commit'],
              'manifest_sha256': sha256(edition / 'palimpsest-pressure-edition.json'),
              'release_files_verified': len(manifest['files']), 'scientific_files_verified': len(actual),
              'portable_files_verified': len(inventory['files']), 'portable_proof': str(proof),
              'scientific_archive_fully_streamed_and_hashed': True}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--edition', default='artwork/pressure-edition-002')
    parser.add_argument('--proof', default='artwork/pressure-proof-001')
    parser.add_argument('--output', default='research/pressure-edition-verification-001.json')
    main(parser.parse_args())
