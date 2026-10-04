"""Restore the observer record, rerun its analyses and rebuild the final artwork."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
from studio.preserve import sha256
from studio.verify_choir_edition import run_module
from studio.verify_choir_download import restore_record


def main(args):
    edition,source,proof,output=map(Path,(args.edition,args.source,args.proof,args.output))
    if proof.exists() or output.exists():raise FileExistsError('Use new proof and report paths')
    manifest_path=edition/'palimpsest-observer-edition.json';manifest=json.loads(manifest_path.read_text())
    for item in manifest['files']:
        assert Path(item['name']).name==item['name'];path=edition/item['name'];assert path.stat().st_size==item['bytes'] and sha256(path)==item['sha256'],path
    expected={r['name']:r['sha256'] for r in manifest['files']};expected[manifest_path.name]=sha256(manifest_path)
    listed={name:digest for digest,name in (line.split('  ',1) for line in (edition/'palimpsest-checksums.sha256').read_text().splitlines())};assert listed==expected
    record=json.loads((edition/'observer-record-manifest.json').read_text());assert record['source_commit']==manifest['source_commit']
    restored=restore_record(edition,proof,record,'observer-scientific-record.tar.gz','observer-record-manifest.json');assert restored['files']==manifest['scientific_archive_files']
    shutil.copytree(source/'studio',proof/'studio')
    analyses=[]
    for study in ('received-histories-002','received-refinement-001'):
        report='research/restored-'+study+'.json';run_module('studio.verify_received_histories',['--study','artifacts/studies/'+study,'--output',report],proof,study+'-verification')
        data=json.loads((proof/report).read_text());assert data['distant_receiver_gate_passed'] and data['field_interventions_exact']
        analyses.append({'study':study,'rates':data['rates'],'cross_rate':data['cross_rate'],'repeated_rate_admission':data.get('repeated_rate_admission')})
    for study in ('observer-offset-001','observer-offset-002'):
        report='research/restored-'+study+'.json';run_module('studio.verify_observer_offset',['--study','artifacts/studies/'+study,'--output',report],proof,study+'-verification')
        data=json.loads((proof/report).read_text());analyses.append({'study':study,'rates':data['rates'],'maximum_matrix_error_hz':data['maximum_matrix_error_hz'],'receivers':data['receivers']})
    original=proof/'artwork/observer-art-002';reference=proof/'artwork/observer-art-002-reference';original.rename(reference)
    run_module('studio.observer_offset_art',[],proof,'observer-art-rebuild')
    names=('the-observer-companion.pdf','the-origin-moves-print.pdf','the-origin-moves-6000x4500.png','the-origin-moves.jpg','six-comparisons.png');files=[]
    for name in names:
        digest=sha256(original/name);assert digest==sha256(reference/name),name
        files.append({'name':name,'bytes':(original/name).stat().st_size,'sha256':digest})
    result={'verified_utc':datetime.now(timezone.utc).isoformat(),'source_commit':manifest['source_commit'],'asset_files':len(manifest['files'])+2,'restored_record':restored,'archive_sha256':sha256(edition/'observer-scientific-record.tar.gz'),'all_file_hashes_match':True,'independent_analyses':analyses,'artwork_rebuilt':files,'all_artwork_byte_identical':True,'proof':str(proof),'scope':'Every release asset and scientific member hashed. Both received-history analyses and both offset diagnostics rerun independently from restored arrays. Three-page companion, vector print, 27-megapixel PNG, preview and evidence PNG rebuilt byte for byte at identical paths. The Matplotlib evidence PDF has ordinary container timestamps and is not asserted byte-identical.'}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--edition',default='artwork/observer-edition-001');p.add_argument('--source',required=True);p.add_argument('--proof',default='artwork/observer-proof-restore-001');p.add_argument('--output',default='research/observer-edition-verification-001.json');main(p.parse_args())
