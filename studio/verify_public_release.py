"""Read public release downloads anonymously and compare the authored inventory.

Bodies are streamed through a bounded buffer and never written to a preview
directory. A byte budget prevents accidentally rereading the large film edition.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


def main(args):
    manifest = Path(args.manifest)
    inventory = json.loads(manifest.read_text())
    items = list(inventory['files'])
    for path in (manifest, manifest.parent / 'palimpsest-checksums.sha256'):
        body = path.read_bytes()
        items.append({'name': path.name, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()})
    if sum(item['bytes'] for item in items) > args.max_bytes:
        raise ValueError('The release exceeds the explicit anonymous verification budget')
    output = Path(args.report)
    if output.exists():
        raise FileExistsError(output)
    results = []
    for item in items:
        if Path(item['name']).name != item['name']:
            raise ValueError('Invalid asset name')
        url = f"https://github.com/{args.repo}/releases/download/{args.tag}/{item['name']}"
        digest, size = hashlib.sha256(), 0
        with urlopen(Request(url, headers={'User-Agent': 'palimpsest-public-verification'}), timeout=120) as response:
            status = response.status
            while chunk := response.read(256 * 1024):
                size += len(chunk)
                if size > item['bytes']:
                    raise ValueError(f"Oversized public download: {item['name']}")
                digest.update(chunk)
        if status != 200 or size != item['bytes'] or digest.hexdigest() != item['sha256']:
            raise ValueError(f"Public download differs from the inventory: {item['name']}")
        results.append({**item, 'status': status, 'url': url})
    report = {'verified_utc': datetime.now(timezone.utc).isoformat(), 'repository': args.repo,
              'tag': args.tag, 'authentication': 'none', 'temporary_media_files': 0, 'assets': results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'assets': len(results), 'bytes': sum(item['bytes'] for item in results),
                      'all_hashes_match': True, 'report': str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--max-bytes', type=int, default=10_000_000)
    main(parser.parse_args())
