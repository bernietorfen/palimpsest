"""Restore the second-act scientific record and rebuild its notebook and analysis."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from studio.preserve import sha256
from studio.verify_pressure_edition import safe


def run_module(module,args,proof,name):
    run=subprocess.run([sys.executable,'-m',module,*args],cwd=proof,env={**os.environ,'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2'},capture_output=True,text=True)
    (proof/(name+'.log')).write_text(run.stdout+run.stderr)
    if run.returncode:raise ValueError(f'Restored verification failed: {name}')


def main(args):
    edition,source,proof,output=map(Path,(args.edition,args.source,args.proof,args.output))
    if proof.exists() or output.exists():raise FileExistsError('Use new proof and report paths')
    manifest_path=edition/'palimpsest-choir-edition.json';manifest=json.loads(manifest_path.read_text())
    for item in manifest['files']:
        assert Path(item['name']).name==item['name'];path=edition/item['name'];assert path.stat().st_size==item['bytes'] and sha256(path)==item['sha256'],path
    expected_checksums={r['name']:r['sha256'] for r in manifest['files']};expected_checksums[manifest_path.name]=sha256(manifest_path)
    listed={name:digest for digest,name in (line.split('  ',1) for line in (edition/'palimpsest-checksums.sha256').read_text().splitlines())};assert listed==expected_checksums
    proof.mkdir(parents=True);actual={};embedded=None;seen=set()
    with tarfile.open(edition/'choir-scientific-record.tar.gz','r|gz') as archive:
        for member in archive:
            relative=safe(member.name)
            if not member.isfile() or member.name in seen:raise ValueError('Duplicate or nonregular record entry')
            seen.add(member.name);target=proof/relative;target.parent.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256();size=0
            with archive.extractfile(member) as incoming,target.open('xb') as destination:
                for block in iter(lambda:incoming.read(1024*1024),b''):digest.update(block);size+=len(block);destination.write(block)
            if member.name=='choir-record-manifest.json':embedded=json.loads(target.read_text())
            else:actual[member.name]={'path':member.name,'bytes':size,'sha256':digest.hexdigest()}
    assert embedded and embedded['source_commit']==manifest['source_commit']
    assert actual=={r['path']:r for r in embedded['files']} and len(actual)+1==manifest['scientific_archive_files']
    assert (proof/'choir-record-manifest.json').read_bytes()==(edition/'choir-record-manifest.json').read_bytes()
    shutil.copytree(source/'studio',proof/'studio')
    run_module('studio.choir_notebook',['--output','output/rebuilt-choir.pdf'],proof,'book-rebuild')
    rebuilt=proof/'output/rebuilt-choir.pdf';original=edition/'a-choir-of-absences-notebook.pdf';assert rebuilt.read_bytes()==original.read_bytes()
    run_module('studio.verify_choir_transfer',['--output','research/restored-transfer-verification.json'],proof,'transfer-verification')
    transfer=json.loads((proof/'research/restored-transfer-verification.json').read_text());assert transfer['all_cases_admitted'] and transfer['exact_negative_controls']
    received=None
    if (proof/'artifacts/studies/received-histories-002/manifest.json').exists():
        run_module('studio.verify_received_histories',['--output','research/restored-order-verification.json'],proof,'order-verification');received=json.loads((proof/'research/restored-order-verification.json').read_text())
    result={'verified_utc':datetime.now(timezone.utc).isoformat(),'source_commit':manifest['source_commit'],'asset_files':len(manifest['files'])+2,'restored_scientific_files':len(actual)+1,
        'archive_sha256':sha256(edition/'choir-scientific-record.tar.gz'),'all_file_hashes_match':True,'notebook_rebuild_byte_identical':True,'notebook_sha256':sha256(rebuilt),
        'transfer_analysis_reproduced':True,'order_analysis_reproduced':received is not None,'order_gate_passed':received['distant_receiver_gate_passed'] if received else None,
        'proof':str(proof),'scope':'Every release asset hashed, every scientific member restored and hashed, original notebook rebuilt byte for byte, and independent saved-data analyses rerun on restored records. No perceptual audition claim.'}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--edition',default='artwork/choir-edition-001');p.add_argument('--source',required=True);p.add_argument('--proof',default='artwork/choir-proof-001');p.add_argument('--output',default='research/choir-edition-verification-001.json');main(p.parse_args())
