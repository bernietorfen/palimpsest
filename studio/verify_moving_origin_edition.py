"""Restore the moving observer's full inputs and independently rebuild its coefficients."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
from studio.preserve import sha256
from studio.verify_choir_download import restore_record
from studio.verify_choir_edition import run_module


def main(args):
    edition,source,proof,output=map(Path,(args.edition,args.source,args.proof,args.output))
    if proof.exists() or output.exists():raise FileExistsError('Use new verification paths')
    path=edition/'palimpsest-moving-observer-edition.json';manifest=json.loads(path.read_text())
    for item in manifest['files']:
        assert Path(item['name']).name==item['name'];asset=edition/item['name'];assert asset.stat().st_size==item['bytes'] and sha256(asset)==item['sha256']
    checks={name:digest for digest,name in (line.split('  ',1) for line in (edition/'palimpsest-checksums.sha256').read_text().splitlines())};assert checks=={**{r['name']:r['sha256'] for r in manifest['files']},path.name:sha256(path)}
    record=json.loads((edition/'moving-observer-record-manifest.json').read_text());assert record['source_commit']==manifest['source_commit']
    restored=restore_record(edition,proof,record,'moving-observer-record.tar.gz','moving-observer-record-manifest.json');assert restored['files']==manifest['scientific_archive_files'];shutil.copytree(source/'studio',proof/'studio')
    run_module('studio.observer_interaction',['--output','artwork/observer-interaction-rebuilt'],proof,'coefficient-rebuild')
    rebuilt=proof/'artwork/observer-interaction-rebuilt/observer-origin-v1.json';assert rebuilt.read_bytes()==(edition/'observer-origin-v1.json').read_bytes()
    run_module('studio.verify_observer_interaction',['--data',str(rebuilt.relative_to(proof)),'--output','research/restored-observer-interaction.json'],proof,'direct-norm-reconstruction')
    verification=json.loads((proof/'research/restored-observer-interaction.json').read_text());assert verification['all_nearest_sets_match']
    report={'verified_utc':datetime.now(timezone.utc).isoformat(),'source_commit':manifest['source_commit'],'all_release_asset_hashes_match':True,'restored_record':restored,'archive_sha256':sha256(edition/'moving-observer-record.tar.gz'),'coefficient_file_byte_identical':True,'data_sha256':sha256(rebuilt),'direct_verification':verification,'scope':'Complete restored input hashes, byte-identical rebuilt interaction coefficients and independent direct-vector distances from the restored original trajectories. Browser behavior and exported SVGs have separate receipts.'}
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--edition',default='artwork/moving-origin-edition-002');p.add_argument('--source',required=True);p.add_argument('--proof',default='artwork/moving-origin-proof-002');p.add_argument('--output',default='research/moving-origin-edition-verification-002.json');main(p.parse_args())
