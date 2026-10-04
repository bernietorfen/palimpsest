"""Restore and hash every portable-installation file before browser verification."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

from studio.preserve import sha256
from studio.verify_pressure_edition import safe


def main(args):
    edition, proof, report = Path(args.edition), Path(args.proof), Path(args.report)
    if proof.exists() or report.exists():
        raise FileExistsError('Use new proof and report paths')
    manifest = json.loads((edition / 'palimpsest-installation-edition.json').read_text())
    for item in manifest['files']:
        path = edition / item['name']
        if Path(item['name']).name != item['name'] or path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
            raise ValueError('Changed installation asset')
    inventory = json.loads((edition / 'installation-content.json').read_text())
    if inventory['source_commit'] != manifest['source_commit']:
        raise ValueError('Installation source identities differ')
    proof.mkdir(parents=True)
    with zipfile.ZipFile(edition / 'palimpsest-installation.zip') as archive:
        names = archive.namelist()
        expected = [item['path'] for item in inventory['files']] + ['installation-content.json']
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError('Unexpected or duplicate installation entries')
        if archive.read('installation-content.json') != (edition / 'installation-content.json').read_bytes():
            raise ValueError('Embedded installation inventory differs')
        for item in inventory['files']:
            target = proof / safe(item['path'])
            target.parent.mkdir(parents=True, exist_ok=True)
            digest, size = hashlib.sha256(), 0
            with archive.open(item['path']) as source, target.open('xb') as destination:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    size += len(block)
                    if size > item['bytes']:
                        raise ValueError('Oversized installation entry')
                    digest.update(block); destination.write(block)
            if size != item['bytes'] or digest.hexdigest() != item['sha256']:
                raise ValueError('Corrupt installation entry')
        (proof / 'installation-content.json').write_bytes(archive.read('installation-content.json'))
    result = {'verified_utc': datetime.now(timezone.utc).isoformat(), 'source_commit': manifest['source_commit'],
              'files': len(inventory['files']) + 1, 'bytes': manifest['uncompressed_bytes'],
              'archive_sha256': sha256(edition / 'palimpsest-installation.zip'),
              'all_file_hashes_match': True, 'proof': str(proof)}
    report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--edition', default='artwork/installation-edition-001')
    parser.add_argument('--proof', default='artwork/installation-proof-001')
    parser.add_argument('--report', default='research/installation-verification-001.json')
    main(parser.parse_args())
